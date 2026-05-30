"""宠物对话服务 —— 查询宠物人设 + 用户补充，合并出 system prompt"""

from __future__ import annotations

import logging

from agents.chat_agent import compose_pet_system_prompt
from api.repositories import pet_chat_repository

logger = logging.getLogger(__name__)


def _to_int(value: object) -> int | None:
    """把路径参数等转成 int，非数字返回 None。"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _extra_to_dict(extra_row: dict | None) -> dict[str, str]:
    """把 pet_prompt_extra 记录整理成扁平键值对：昵称 + attributes。"""
    if not extra_row:
        return {}

    merged: dict[str, str] = {}
    nickname = (extra_row.get("nickname") or "").strip()
    if nickname:
        merged["昵称"] = nickname

    attributes = extra_row.get("attributes")
    if isinstance(attributes, dict):
        merged.update(attributes)
    return merged


async def build_pet_system_prompt(user_id: object, pet_id: object) -> str | None:
    """查询宠物人设 + 用户个性化补充，合并为一个 system prompt。

    宠物没有配置（或未启用）人设时返回 None，调用方据此拒绝建立对话。
    """
    pet_id_int = _to_int(pet_id)
    if pet_id_int is None:
        return None

    prompt_row = await pet_chat_repository.get_pet_prompt(pet_id_int)
    if not prompt_row or not (prompt_row.get("prompt") or "").strip():
        logger.info("[pet-chat] 宠物 %s 未配置人设 prompt", pet_id)
        return None

    extra: dict[str, str] = {}
    user_id_int = _to_int(user_id)
    if user_id_int is not None:
        extra_row = await pet_chat_repository.get_pet_extra(user_id_int, pet_id_int)
        extra = _extra_to_dict(extra_row)

    return compose_pet_system_prompt(prompt_row["prompt"], extra)


async def is_pet_chat_enabled(pet_id: object) -> bool:
    """根据宠物 id 返回是否开启对话（pet_prompt.enabled）。"""
    pet_id_int = _to_int(pet_id)
    if pet_id_int is None:
        return False
    return await pet_chat_repository.get_pet_enabled(pet_id_int)


async def get_pet_avatar(pet_id: object) -> str | None:
    """从 pokemon 表查宠物头像；pet_id 非数字或宠物不存在时返回 None。"""
    pet_id_int = _to_int(pet_id)
    if pet_id_int is None:
        return None
    return await pet_chat_repository.get_pet_avatar(pet_id_int)


async def load_pet_history(
    user_id: object,
    pet_id: object,
    limit: int = 50,
) -> list[dict]:
    """加载某会话最近的历史消息，按时间正序返回。

    返回 [{"role": "user"|"assistant", "content": str, "created_at": iso}, ...]
    user_id / pet_id 非数字时返回空列表。
    """
    user_id_int = _to_int(user_id)
    pet_id_int = _to_int(pet_id)
    if user_id_int is None or pet_id_int is None:
        return []

    rows = await pet_chat_repository.list_pet_messages(user_id_int, pet_id_int, limit)
    history: list[dict] = []
    for row in rows:
        created_at = row.get("created_at")
        history.append({
            "role": row["role"],
            "content": row["content"],
            "created_at": created_at.isoformat() if created_at else None,
        })
    return history


async def save_pet_history(
    user_id: object,
    pet_id: object,
    messages: list[dict],
) -> int:
    """落库一段对话消息（[{role, content}, ...]），返回写入条数。"""
    user_id_int = _to_int(user_id)
    pet_id_int = _to_int(pet_id)
    if user_id_int is None or pet_id_int is None or not messages:
        return 0
    return await pet_chat_repository.save_pet_messages(user_id_int, pet_id_int, messages)
