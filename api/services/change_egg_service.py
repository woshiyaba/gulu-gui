"""换蛋广场业务逻辑 —— 挂单 CRUD + 双向匹配编排。

匹配条件：A.拥有 == B.需求 且 A.需求 == B.拥有，pokemon_id 与 tag 同时相等。
- 用户提交挂单后由路由层 asyncio.create_task 立即触发一次 run_match_for_listing；
- 定时任务（APScheduler）周期性调用 run_match_all_open 全量扫描；
- 命中后写 change_egg_match 去重，并通过 message_service 给双方各下发一条通知。
"""

from __future__ import annotations

import logging
from typing import Any

from api.repositories import change_egg_repository
from api.services import message_service

logger = logging.getLogger(__name__)

# 系统通知发送方 id
SYSTEM_USER_ID = 0


async def create_listing(
    user_id: int,
    game_id: str,
    own_pokemon_id: int,
    own_tag: str,
    want_pokemon_id: int,
    want_tag: str,
) -> dict[str, Any]:
    return await change_egg_repository.create_listing(
        user_id=user_id,
        game_id=game_id,
        own_pokemon_id=own_pokemon_id,
        own_tag=own_tag,
        want_pokemon_id=want_pokemon_id,
        want_tag=want_tag,
    )


async def list_user_listings(user_id: int, status: str | None = None) -> list[dict[str, Any]]:
    return await change_egg_repository.list_user_listings(user_id, status)


async def list_square(
    limit: int = 20,
    offset: int = 0,
    pokemon_id: int | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    return await change_egg_repository.list_open_listings(limit, offset, pokemon_id, tag)


async def close_listing(listing_id: int, user_id: int) -> dict[str, Any] | None:
    return await change_egg_repository.close_listing(listing_id, user_id)


async def delete_listing(listing_id: int, user_id: int) -> bool:
    return await change_egg_repository.delete_listing(listing_id, user_id)


async def list_tags() -> list[dict[str, Any]]:
    return await change_egg_repository.list_egg_tags()


def _build_notify(listing: dict[str, Any], partner: dict[str, Any]) -> dict[str, Any]:
    """构造给 listing.user 的换蛋匹配通知（content + payload）。"""
    content = (
        f"找到换蛋对象啦！对方拥有你需求的蛋组，"
        f"对方游戏 id：{partner.get('game_id', '')}"
    )
    payload = {
        "kind": "egg_match",
        "my_listing_id": listing["id"],
        "partner_user_id": partner["user_id"],
        "partner_game_id": partner.get("game_id", ""),
        "partner_listing_id": partner["id"],
        "partner_own_pokemon_id": partner["own_pokemon_id"],
        "partner_own_tag": partner["own_tag"],
        "partner_want_pokemon_id": partner["want_pokemon_id"],
        "partner_want_tag": partner["want_tag"],
    }
    return {"content": content, "payload": payload}


async def _notify_pair(listing: dict[str, Any], partner: dict[str, Any]) -> None:
    """给命中的双方各下发一条换蛋匹配通知。"""
    for target, other in ((listing, partner), (partner, listing)):
        notify = _build_notify(target, other)
        await message_service.send_message(
            from_user_id=SYSTEM_USER_ID,
            to_user_id=target["user_id"],
            content=notify["content"],
            msg_type="egg_match_notify",
            payload=notify["payload"],
        )


async def run_match_for_listing(listing_id: int) -> int:
    """对单条挂单跑一次匹配，返回新命中的对数。

    对每个候选：record_match 去重（已存在则跳过通知）→ 双方置 matched → 通知双方。
    """
    listing = await change_egg_repository.get_listing(listing_id)
    if not listing or listing.get("status") != "open":
        return 0

    matched = 0
    candidates = await change_egg_repository.find_reciprocal_matches(listing)
    for partner in candidates:
        is_new = await change_egg_repository.record_match(
            listing_a_id=listing["id"],
            listing_b_id=partner["id"],
            user_a_id=listing["user_id"],
            user_b_id=partner["user_id"],
        )
        if not is_new:
            continue
        await change_egg_repository.mark_listings_matched([listing["id"], partner["id"]])
        try:
            await _notify_pair(listing, partner)
        except Exception:
            logger.warning("[change_egg] 下发匹配通知失败 a=%s b=%s", listing["id"], partner["id"], exc_info=True)
        matched += 1
        # 当前挂单已匹配，不再继续配对其它候选
        break

    return matched


async def run_match_all_open() -> int:
    """全量扫描所有 open 挂单逐个匹配（定时任务调用），返回新命中的对数。

    依赖 change_egg_match 唯一约束去重，重复命中不会重复通知。
    """
    listings = await change_egg_repository.list_all_open_listings()
    total = 0
    for listing in listings:
        try:
            total += await run_match_for_listing(listing["id"])
        except Exception:
            logger.warning("[change_egg] 扫描匹配出错 listing_id=%s", listing.get("id"), exc_info=True)
    if total:
        logger.info("[change_egg] 定时匹配新命中 %d 对", total)
    return total
