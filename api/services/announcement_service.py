from datetime import datetime

from api.repositories import announcement_repository, ops_repository
from api.services.ops_service import ensure_role


def _for_audit(item: dict | None) -> dict | None:
    """审计日志走 json.dumps，需把 datetime 转成字符串。"""
    if not item:
        return item
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in item.items()
    }


async def get_active_announcement() -> dict | None:
    """供前台调用：返回启用中的公告，未启用/为空时返回 None。"""
    return await announcement_repository.get_active_announcement()


async def get_announcement_for_ops(user: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await announcement_repository.get_announcement()
    if not item:
        # 理论上 bootstrap 已建好配置行，这里兜底再建一次。
        await announcement_repository.ensure_announcement_table()
        item = await announcement_repository.get_announcement()
    return item


async def update_announcement_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await announcement_repository.get_announcement()
    normalized = {
        "title": (payload.get("title") or "").strip(),
        "content": payload.get("content") or "",
        "is_active": bool(payload.get("is_active")),
    }
    item = await announcement_repository.update_announcement(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="announcement",
        resource_id=str(item["id"]) if item else "1",
        action="update",
        before_json=_for_audit(before),
        after_json=_for_audit(item),
    )
    return item


async def get_about_texts() -> list[str]:
    """供前台"关于"卡片调用：返回 sys_dict 中 dict_type=about 的话语列表。"""
    return await announcement_repository.get_about_texts()


async def get_announcement_like_count() -> int:
    return await announcement_repository.get_announcement_like_count()


async def like_announcement() -> int:
    return await announcement_repository.increment_announcement_like_count()
