"""换蛋广场接口。

用户上传"拥有 / 需求"的蛋组挂单，提交后立即异步触发一次匹配；
另有 APScheduler 定时全量扫描。命中后通过通用消息入口给双方下发通知。
面向 C 端，user_id 直接走请求体 / Query（沿用 album 约定，不挂鉴权）。
"""

import asyncio

from fastapi import APIRouter, HTTPException, Query

from api.schemas.change_egg import (
    ChangeEggCloseRequest,
    ChangeEggCreateRequest,
    ChangeEggListing,
    ChangeEggTag,
)
from api.services import change_egg_service

router = APIRouter(prefix="/api/change-eggs", tags=["change-eggs"])


@router.post("", response_model=ChangeEggListing)
async def create_listing(payload: ChangeEggCreateRequest):
    """新增换蛋挂单，落库后立即异步触发一次匹配，接口即时返回挂单。"""
    listing = await change_egg_service.create_listing(
        user_id=payload.user_id,
        game_id=payload.game_id,
        own_pokemon_id=payload.own_pokemon_id,
        own_tag=payload.own_tag,
        want_pokemon_id=payload.want_pokemon_id,
        want_tag=payload.want_tag,
    )
    # 立即异步触发一次匹配，不阻塞响应
    asyncio.create_task(change_egg_service.run_match_for_listing(listing["id"]))
    return listing


@router.get("", response_model=list[ChangeEggListing])
async def list_my_listings(
    user_id: int = Query(..., description="平台用户 id"),
    status: str | None = Query(None, description="按状态过滤：open / matched / closed"),
):
    """查询某用户自己的挂单。"""
    return await change_egg_service.list_user_listings(user_id, status)


@router.get("/square", response_model=list[ChangeEggListing])
async def list_square(
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    pokemon_id: int | None = Query(None, description="按拥有的精灵 id 过滤"),
    tag: str | None = Query(None, description="按拥有蛋组 tag 过滤"),
):
    """广场分页浏览所有 open 挂单。"""
    return await change_egg_service.list_square(limit, offset, pokemon_id, tag)


@router.get("/tags", response_model=list[ChangeEggTag])
async def list_tags():
    """返回可选的换蛋蛋组 tag（后台在 /api/ops/dicts 维护）。"""
    return await change_egg_service.list_tags()


@router.post("/{listing_id}/close", response_model=ChangeEggListing)
async def close_listing(listing_id: int, payload: ChangeEggCloseRequest):
    """用户主动关闭自己正在匹配（open）的挂单：status open → closed。"""
    listing = await change_egg_service.close_listing(listing_id, payload.user_id)
    if not listing:
        raise HTTPException(status_code=404, detail="挂单不存在、无权限或不在匹配中")
    return listing


@router.delete("/{listing_id}")
async def delete_listing(
    listing_id: int,
    user_id: int = Query(..., description="平台用户 id（校验归属）"),
):
    """彻底删除自己的挂单（任意状态）。"""
    ok = await change_egg_service.delete_listing(listing_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="挂单不存在或无权限")
    return {"ok": True}
