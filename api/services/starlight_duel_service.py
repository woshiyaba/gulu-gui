from fastapi import HTTPException, status

from api.repositories import starlight_duel_repository, ops_repository
from api.services.ops_service import ensure_role


async def get_latest_episode() -> dict | None:
    return await starlight_duel_repository.get_latest_active_episode()


async def get_episode_by_number(episode_number: int) -> dict:
    episode = await starlight_duel_repository.get_episode_by_number(episode_number)
    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    return episode


async def list_episodes_for_ops(
    user: dict,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await starlight_duel_repository.list_episodes_paginated(page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_episode_detail_for_ops(user: dict, episode_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    episode = await starlight_duel_repository.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    return episode


async def create_episode_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    if not payload.get("episode_number"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="期数不能为空")
    item = await starlight_duel_repository.create_episode(payload)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="starlight_duel_episode",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=item,
    )
    return item


async def update_episode_for_ops(user: dict, episode_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await starlight_duel_repository.get_episode_by_id(episode_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    item = await starlight_duel_repository.update_episode(episode_id, payload)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="starlight_duel_episode",
        resource_id=str(episode_id),
        action="update",
        before_json=before,
        after_json=item,
    )
    return item


async def delete_episode_for_ops(user: dict, episode_id: int) -> None:
    ensure_role(user, {"admin"})
    before = await starlight_duel_repository.get_episode_by_id(episode_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    deleted = await starlight_duel_repository.delete_episode(episode_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该期星光对决不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="starlight_duel_episode",
        resource_id=str(episode_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def search_pokemon_for_ops(user: dict, keyword: str) -> dict:
    ensure_role(user, {"editor", "admin"})
    items = await starlight_duel_repository.search_pokemon(keyword.strip())
    return {"items": items}


async def search_skills_for_ops(user: dict, keyword: str) -> dict:
    ensure_role(user, {"editor", "admin"})
    items = await starlight_duel_repository.search_skills(keyword.strip())
    return {"items": items}
