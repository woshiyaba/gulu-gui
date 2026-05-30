"""宠物对话仓储 —— pet_prompt / pet_prompt_extra 读写

建表语句见 sql/pet_chat.sql（由人工手动执行），本模块只负责查询与写入。
"""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_pool


async def get_pet_prompt(pet_id: int) -> dict[str, Any] | None:
    """查询某只宠物的基础人设 prompt（仅返回已启用的）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT pet_id, prompt, enabled
                FROM pet_prompt
                WHERE pet_id = %s AND enabled = TRUE
                """,
                (pet_id,),
            )
            return await cur.fetchone()


async def get_pet_enabled(pet_id: int) -> bool:
    """查询某只宠物是否开启对话；无记录视为未开启。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT enabled FROM pet_prompt WHERE pet_id = %s",
                (pet_id,),
            )
            row = await cur.fetchone()
    return bool(row and row["enabled"])


async def get_pet_avatar(pet_id: int) -> str | None:
    """从 pokemon 表按 id 查宠物头像（image）；无记录返回 None。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT avatar FROM pokemon WHERE id = %s",
                (pet_id,),
            )
            row = await cur.fetchone()
    if not row:
        return None
    return row.get("avatar") or ""


async def get_pet_extra(user_id: int, pet_id: int) -> dict[str, Any] | None:
    """查询某用户对某只宠物的个性化补充。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, pet_id, nickname, attributes
                FROM pet_prompt_extra
                WHERE user_id = %s AND pet_id = %s
                """,
                (user_id, pet_id),
            )
            return await cur.fetchone()


async def list_pet_messages(
    user_id: int,
    pet_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """按时间正序返回某会话最近 limit 条历史消息。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT role, content, created_at
                FROM (
                    SELECT role, content, created_at, id
                    FROM pet_chat_message
                    WHERE user_id = %s AND pet_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                ) AS recent
                ORDER BY id ASC
                """,
                (user_id, pet_id, limit),
            )
            return await cur.fetchall()


async def save_pet_messages(
    user_id: int,
    pet_id: int,
    messages: list[dict[str, str]],
) -> int:
    """批量落库一段对话消息，返回写入条数。messages 为 [{role, content}, ...]。"""
    rows = [
        (user_id, pet_id, m["role"], m["content"])
        for m in messages
        if m.get("content")
    ]
    if not rows:
        return 0

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO pet_chat_message (user_id, pet_id, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                rows,
            )
        await conn.commit()
    return len(rows)


async def upsert_pet_extra(
    user_id: int,
    pet_id: int,
    nickname: str = "",
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """新增 / 更新用户对某只宠物的个性化补充，返回最新记录。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pet_prompt_extra (user_id, pet_id, nickname, attributes)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (user_id, pet_id) DO UPDATE
                SET nickname = EXCLUDED.nickname,
                    attributes = EXCLUDED.attributes,
                    updated_at = NOW()
                RETURNING user_id, pet_id, nickname, attributes
                """,
                (
                    user_id,
                    pet_id,
                    nickname or "",
                    json.dumps(attributes or {}, ensure_ascii=False),
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row
