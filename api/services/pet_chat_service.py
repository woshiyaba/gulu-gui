"""宠物对话服务 —— 查询宠物人设 + 用户补充，合并出 system prompt"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from agents.chat_agent import compose_pet_system_prompt
from api.repositories import ops_repository, pet_chat_repository
from api.services import personality_service

logger = logging.getLogger(__name__)

# pet_prompt_extra 字典里被特殊处理的 code
EXTRA_DICT_TYPE = "pet_prompt_extra"
NICKNAME_CODE = "nickname"      # 写入 pet_prompt_extra.nickname 列
CHARACTER_CODE = "character"    # 性格，下拉项，选项来自 personalities，存性格 name


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


# ── 用户自定义宠物信息（pet_prompt_extra）────────────────────


async def get_pet_prompt_extra_form(user_id: object, pet_id: object) -> dict:
    """返回用户可编辑的字段定义 + 当前已保存的值。

    字段定义来自 sys_dict（dict_type=pet_prompt_extra）；性格（code=character）
    是下拉项，选项为全部性格名称；昵称（code=nickname）的当前值取自
    pet_prompt_extra.nickname 列，其余字段取自 attributes（key 为中文 label）。
    """
    pet_id_int = _to_int(pet_id)
    user_id_int = _to_int(user_id)
    if pet_id_int is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少宠物 id")

    rows = await ops_repository.list_dicts_all(dict_type=EXTRA_DICT_TYPE)

    extra_row = None
    if user_id_int is not None:
        extra_row = await pet_chat_repository.get_pet_extra(user_id_int, pet_id_int)
    nickname = (extra_row.get("nickname") if extra_row else "") or ""
    attributes = (extra_row.get("attributes") if extra_row else None) or {}
    if not isinstance(attributes, dict):
        attributes = {}

    has_character = any(r.get("code") == CHARACTER_CODE for r in rows)
    character_options: list[str] = []
    if has_character:
        personalities = await personality_service.list_personalities_public()
        character_options = [p["name"] for p in personalities if p and p.get("name")]

    fields: list[dict] = []
    for r in rows:
        code = r.get("code") or ""
        label = r.get("label") or ""
        is_character = code == CHARACTER_CODE
        if code == NICKNAME_CODE:
            value = nickname
        else:
            value = attributes.get(label, "")
        fields.append({
            "code": code,
            "label": label,
            "type": "select" if is_character else "text",
            "options": character_options if is_character else [],
            "value": value or "",
        })

    return {"pet_id": pet_id_int, "fields": fields}


async def save_pet_prompt_extra(
    user_id: object,
    pet_id: object,
    values: dict[str, str],
) -> dict:
    """保存用户填写的 DIY 属性。

    values 为 {code: value}；code=nickname 写入 nickname 列，其余按字典 label
    作为 key 写入 attributes（JSONB）。
    """
    user_id_int = _to_int(user_id)
    pet_id_int = _to_int(pet_id)
    if user_id_int is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少用户 id")
    if pet_id_int is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少宠物 id")

    values = values or {}
    rows = await ops_repository.list_dicts_all(dict_type=EXTRA_DICT_TYPE)
    code_to_label = {r.get("code"): (r.get("label") or "") for r in rows}

    nickname = (values.get(NICKNAME_CODE) or "").strip()
    attributes: dict[str, str] = {}
    for code, raw in values.items():
        if code == NICKNAME_CODE or code not in code_to_label:
            continue
        text = (raw or "").strip()
        if not text:
            continue
        attributes[code_to_label[code]] = text

    row = await pet_chat_repository.upsert_pet_extra(
        user_id_int, pet_id_int, nickname, attributes,
    )
    return {
        "pet_id": pet_id_int,
        "nickname": row.get("nickname") or "",
        "attributes": row.get("attributes") or {},
    }
