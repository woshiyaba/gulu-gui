from fastapi import HTTPException, status

from api.repositories import banner_repository, ops_repository
from api.services.ops_service import ensure_role


async def list_active_banners() -> list[dict]:
    return await banner_repository.list_active_banners()


async def list_banners_for_ops(
    user: dict,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await banner_repository.list_banners_paginated(page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def create_banner_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await banner_repository.create_banner(payload)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="banner",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=item,
    )
    return item


async def update_banner_for_ops(user: dict, banner_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await banner_repository.get_banner_by_id(banner_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner不存在")
    item = await banner_repository.update_banner(banner_id, payload)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="banner",
        resource_id=str(banner_id),
        action="update",
        before_json=before,
        after_json=item,
    )
    return item


async def delete_banner_for_ops(user: dict, banner_id: int) -> None:
    ensure_role(user, {"admin"})
    before = await banner_repository.get_banner_by_id(banner_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner不存在")
    deleted = await banner_repository.delete_banner(banner_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="banner",
        resource_id=str(banner_id),
        action="delete",
        before_json=before,
        after_json=None,
    )
