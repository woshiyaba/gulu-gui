"""洛克纪年（大事记）业务逻辑。

前台只读启用中的事件；后台维护需 editor/admin，删除需 admin，所有写操作记审计日志。
"""

from datetime import date, datetime

from fastapi import HTTPException, status

from api.repositories import ops_repository, roco_chronology_repository
from api.services.ops_service import ensure_role


def _for_audit(item: dict | None) -> dict | None:
    """审计日志走 json.dumps，需把 date/datetime 转成字符串。"""
    if not item:
        return item
    return {
        key: (value.isoformat() if isinstance(value, (date, datetime)) else value)
        for key, value in item.items()
    }


def _normalize(payload: dict) -> dict:
    """清洗入参：去掉空图片、首尾空白。"""
    images = [str(url).strip() for url in (payload.get("images") or []) if str(url).strip()]
    return {
        "event_date": payload["event_date"],
        "title": (payload.get("title") or "").strip(),
        "content": payload.get("content") or "",
        "images": images,
        "sort_order": int(payload.get("sort_order") or 0),
        "is_active": bool(payload.get("is_active", True)),
    }


# ── 前台展示 ────────────────────────────────────────────


async def list_published() -> list[dict]:
    return await roco_chronology_repository.list_published()


async def get_published_detail(item_id: int) -> dict:
    item = await roco_chronology_repository.get_published_detail(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事迹不存在")
    return item


# ── 后台维护 ────────────────────────────────────────────


async def list_for_ops(user: dict, keyword: str = "", page: int = 1, page_size: int = 10) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await roco_chronology_repository.list_paginated(keyword.strip(), page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_for_ops(user: dict, item_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await roco_chronology_repository.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事迹不存在")
    return item


async def create_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await roco_chronology_repository.create(_normalize(payload))
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="roco_chronology",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=_for_audit(item),
    )
    return item


async def update_for_ops(user: dict, item_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await roco_chronology_repository.get_by_id(item_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事迹不存在")
    item = await roco_chronology_repository.update(item_id, _normalize(payload))
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="roco_chronology",
        resource_id=str(item_id),
        action="update",
        before_json=_for_audit(before),
        after_json=_for_audit(item),
    )
    return item


async def delete_for_ops(user: dict, item_id: int) -> None:
    ensure_role(user, {"admin"})
    before = await roco_chronology_repository.get_by_id(item_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事迹不存在")
    deleted = await roco_chronology_repository.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事迹不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="roco_chronology",
        resource_id=str(item_id),
        action="delete",
        before_json=_for_audit(before),
        after_json=None,
    )
