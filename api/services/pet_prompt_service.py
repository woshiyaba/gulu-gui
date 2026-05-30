"""宠物对话 prompt 后台业务逻辑。

每只宠物（精灵）绑定一段独立人设 prompt，可控制是否启用对话（enabled）。
后台维护需 editor/admin，删除需 admin，所有写操作记审计日志。
"""

from datetime import date, datetime

from fastapi import HTTPException, status

from api.repositories import ops_repository, pet_prompt_repository
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
    """清洗入参：pet_id 转 int，prompt 去首尾空白，enabled 转 bool。"""
    pet_id = payload.get("pet_id")
    if not pet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择宠物")
    return {
        "pet_id": int(pet_id),
        "prompt": (payload.get("prompt") or "").strip(),
        "enabled": bool(payload.get("enabled", False)),
    }


async def list_for_ops(user: dict, keyword: str = "", page: int = 1, page_size: int = 10) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await pet_prompt_repository.list_paginated(keyword.strip(), page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_for_ops(user: dict, item_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await pet_prompt_repository.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物 prompt 不存在")
    return item


async def create_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    data = _normalize(payload)

    if not await pet_prompt_repository.get_pet(data["pet_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物不存在")
    if await pet_prompt_repository.get_by_pet_id(data["pet_id"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该宠物已配置 prompt，请勿重复添加")

    item = await pet_prompt_repository.create(data)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pet_prompt",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=_for_audit(item),
    )
    return item


async def update_for_ops(user: dict, item_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await pet_prompt_repository.get_by_id(item_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物 prompt 不存在")

    data = _normalize(payload)
    if data["pet_id"] != before["pet_id"]:
        if not await pet_prompt_repository.get_pet(data["pet_id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物不存在")
        existing = await pet_prompt_repository.get_by_pet_id(data["pet_id"])
        if existing and existing["id"] != item_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该宠物已配置 prompt，请勿重复添加")

    item = await pet_prompt_repository.update(item_id, data)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pet_prompt",
        resource_id=str(item_id),
        action="update",
        before_json=_for_audit(before),
        after_json=_for_audit(item),
    )
    return item


async def delete_for_ops(user: dict, item_id: int) -> None:
    ensure_role(user, {"admin"})
    before = await pet_prompt_repository.get_by_id(item_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物 prompt 不存在")
    deleted = await pet_prompt_repository.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="宠物 prompt 不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pet_prompt",
        resource_id=str(item_id),
        action="delete",
        before_json=_for_audit(before),
        after_json=None,
    )
