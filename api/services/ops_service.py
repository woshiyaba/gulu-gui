import asyncio
import base64
import hashlib
import hmac
import html
import json
import os
import re
import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from api.repositories import ops_repository, pokemon_filter_repository
from common.utils import lkgc

OPS_TOKEN_SECRET = os.getenv("OPS_TOKEN_SECRET", "ops-dev-secret")
OPS_TOKEN_TTL_SECONDS = int(os.getenv("OPS_TOKEN_TTL_SECONDS", "43200"))
OPS_INIT_USERNAME = os.getenv("OPS_INIT_USERNAME", "admin")
OPS_INIT_PASSWORD = os.getenv("OPS_INIT_PASSWORD", "admin123456")
OPS_INIT_NICKNAME = os.getenv("OPS_INIT_NICKNAME", "默认管理员")

_ALLOWED_FRIEND_IMAGE_SUFFIX = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
_MAX_FRIEND_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_SKILL_ICON_SUFFIX = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
_MAX_SKILL_ICON_BYTES = 2 * 1024 * 1024


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{_b64encode(salt)}.{_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_b64, digest_b64 = password_hash.split(".", 1)
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def create_access_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + OPS_TOKEN_TTL_SECONDS,
    }
    payload_raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    payload_b64 = _b64encode(payload_raw)
    sig = hmac.new(OPS_TOKEN_SECRET.encode(), payload_b64.encode(), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64encode(sig)}"


def decode_access_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected = hmac.new(OPS_TOKEN_SECRET.encode(), payload_b64.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(sig_b64)):
            raise ValueError("invalid signature")
        payload = json.loads(_b64decode(payload_b64).decode())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录态无效") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录态已过期")
    return payload


async def ensure_ops_bootstrap() -> None:
    await ops_repository.ensure_ops_tables()
    if await ops_repository.count_ops_users() == 0:
        await ops_repository.create_ops_user(
            username=OPS_INIT_USERNAME,
            password_hash=hash_password(OPS_INIT_PASSWORD),
            nickname=OPS_INIT_NICKNAME,
            role="admin",
        )


def serialize_ops_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "nickname": user.get("nickname", ""),
        "role": user["role"],
    }


async def login(username: str, password: str) -> dict:
    user = await ops_repository.get_user_by_username(username.strip())
    if not user or not user.get("is_active") or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": serialize_ops_user(user),
    }


async def update_profile(user: dict, payload: dict) -> dict:
    nickname = (payload.get("nickname") or "").strip()
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""

    if not nickname:
        nickname = user.get("nickname", "") or user["username"]

    password_hash = None
    if new_password:
        if len(new_password) < 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少 6 位")
        if not current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="修改密码时必须填写当前密码")
        if not verify_password(current_password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
        password_hash = hash_password(new_password)

    before = serialize_ops_user(user)
    updated_user = await ops_repository.update_ops_user_profile(
        user_id=user["id"],
        nickname=nickname,
        password_hash=password_hash,
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    after = serialize_ops_user(updated_user)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="ops_user",
        resource_id=str(user["id"]),
        action="update",
        before_json=before,
        after_json=after,
    )
    return after


async def get_current_user_from_token(token: str) -> dict:
    payload = decode_access_token(token)
    user = await ops_repository.get_user_by_id(int(payload["sub"]))
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    return user


def ensure_role(user: dict, allowed_roles: set[str]) -> None:
    if user["role"] not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有操作权限")


async def get_dicts(
        dict_type: str = "",
        code: str = "",
        label: str = "",
        page: int | None = 1,
        page_size: int | None = 10,
) -> dict:
    # 仅按 dict_type 拉下拉时，允许不传分页，直接返回该类型全量字典。
    if page is None and page_size is None:
        items = await ops_repository.list_dicts_all(dict_type=dict_type, code=code, label=label)
        total = len(items)
        return {"total": total, "page": 1, "page_size": total if total > 0 else 1, "items": items}

    safe_page = max(page or 1, 1)
    safe_page_size = max(1, min(page_size or 10, 100))
    total, items = await ops_repository.list_dicts(
        dict_type=dict_type,
        code=code,
        label=label,
        page=safe_page,
        page_size=safe_page_size,
    )
    return {"total": total, "page": safe_page, "page_size": safe_page_size, "items": items}


async def create_dict(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    item = await ops_repository.create_dict_item(payload)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="sys_dict",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=item,
    )
    return item


async def update_dict(user: dict, dict_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_dict_by_id(dict_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典项不存在")
    item = await ops_repository.update_dict_item(dict_id, payload)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="sys_dict",
        resource_id=str(dict_id),
        action="update",
        before_json=before,
        after_json=item,
    )
    return item


async def delete_dict(user: dict, dict_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_dict_by_id(dict_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典项不存在")
    deleted = await ops_repository.delete_dict_item(dict_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典项不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="sys_dict",
        resource_id=str(dict_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def list_users(user: dict) -> dict:
    ensure_role(user, {"admin"})
    rows = await ops_repository.list_ops_users()
    return {"items": [serialize_ops_user(row) for row in rows]}


async def create_user(user: dict, payload: dict) -> dict:
    ensure_role(user, {"admin"})
    username = (payload.get("username") or "").strip()
    nickname = (payload.get("nickname") or "").strip()
    password = payload.get("password") or ""
    role = (payload.get("role") or "editor").strip()

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号不能为空")
    if len(username) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号至少 3 位")
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位")
    if role not in {"admin", "editor"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色无效")

    exists = await ops_repository.get_user_by_username(username)
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号已存在")

    if not nickname:
        nickname = username

    created = await ops_repository.create_ops_user_with_return(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname,
        role=role,
    )

    result = serialize_ops_user(created)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="ops_user",
        resource_id=str(result["id"]),
        action="create",
        before_json=None,
        after_json=result,
    )
    return result


async def update_user(user: dict, target_user_id: int, payload: dict) -> dict:
    ensure_role(user, {"admin"})
    target = await ops_repository.get_user_by_id(target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    nickname = (payload.get("nickname") or "").strip() or target["nickname"] or target["username"]
    role = (payload.get("role") or target["role"]).strip()
    password = payload.get("password") or ""

    if role not in {"admin", "editor"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色无效")
    if target_user_id == user["id"] and role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能把自己降级为 editor")

    password_hash = None
    if password:
        if len(password) < 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 位")
        password_hash = hash_password(password)

    before = serialize_ops_user(target)
    updated = await ops_repository.update_ops_user_by_admin(
        user_id=target_user_id,
        nickname=nickname,
        role=role,
        password_hash=password_hash,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    after = serialize_ops_user(updated)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="ops_user",
        resource_id=str(target_user_id),
        action="update",
        before_json=before,
        after_json=after,
    )
    return after


async def delete_user(user: dict, target_user_id: int) -> None:
    ensure_role(user, {"admin"})
    if target_user_id == user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录账号")

    before = await ops_repository.get_user_by_id(target_user_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    deleted = await ops_repository.delete_ops_user(target_user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="ops_user",
        resource_id=str(target_user_id),
        action="delete",
        before_json=serialize_ops_user(before),
        after_json=None,
    )


async def list_audit_logs_for_ops(
        user: dict,
        username: str = "",
        resource_type: str = "",
        resource_id: str = "",
        action: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_audit_logs_for_ops(
        username=username.strip(),
        resource_type=resource_type.strip(),
        resource_id=resource_id.strip(),
        action=action.strip(),
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def _normalize_pokemon_payload(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["no"] = (payload.get("no") or "").strip()
    normalized["name"] = (payload.get("name") or "").strip()
    normalized["egg_groups"] = [x.strip() for x in (payload.get("egg_groups") or []) if str(x).strip()]
    normalized["skills"] = payload.get("skills") or []
    if not normalized["no"] or not normalized["name"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="编号和名称不能为空")
    if not normalized.get("trait_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="特性不能为空")
    return normalized


async def list_pokemon_for_ops(
        user: dict,
        keyword: str = "",
        no: str = "",
        name: str = "",
        attr_id: int | None = None,
        egg_group: str = "",
        type_code: str = "",
        form_code: str = "",
        trait_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, rows = await ops_repository.list_pokemon_for_ops(
        keyword=keyword.strip(),
        no=no.strip(),
        name=name.strip(),
        attr_id=attr_id,
        egg_group=egg_group.strip(),
        type_code=type_code.strip(),
        form_code=form_code.strip(),
        trait_id=trait_id,
        page=page,
        page_size=page_size,
    )
    items: list[dict] = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "no": row["no"],
                "name": row["name"],
                "type_name": row.get("type_name", ""),
                "form_name": row.get("form_name", ""),
                "trait_name": row.get("trait_name", ""),
                "attributes": [x for x in (row.get("attr_names") or "").split(",") if x],
                "egg_groups": [x for x in (row.get("egg_group_names") or "").split(",") if x],
            }
        )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_pokemon_detail_for_ops(user: dict, pokemon_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    detail = await ops_repository.get_pokemon_detail_for_ops(pokemon_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")
    return detail


async def create_pokemon_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_pokemon_payload(payload)
    created = await ops_repository.save_pokemon_for_ops(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_pokemon_for_ops(user: dict, pokemon_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_pokemon_detail_for_ops(pokemon_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")
    normalized = _normalize_pokemon_payload(payload)
    updated = await ops_repository.save_pokemon_for_ops(normalized, pokemon_id=pokemon_id)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon",
        resource_id=str(pokemon_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_pokemon_for_ops(user: dict, pokemon_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_pokemon_detail_for_ops(pokemon_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")
    deleted = await ops_repository.delete_pokemon_for_ops(pokemon_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon",
        resource_id=str(pokemon_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def get_pokemon_options_for_ops(user: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    result = await ops_repository.list_pokemon_options_for_ops()
    rows = await ops_repository.list_dicts_all(dict_type="pokemon_skill_source")
    result["skill_sources"] = [str(r.get("code") or "").strip() for r in rows if str(r.get("code") or "").strip()]
    return result


def _normalize_lkgc_response(raw: object) -> object:
    if isinstance(raw, dict) and "data" in raw:
        data = raw.get("data")
        if isinstance(data, dict) and "data" in data:
            return data.get("data")
        return data
    return raw


def _strip_lkgc_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "")
    return html.unescape(text).strip()


def _lkgc_form_names(item: dict) -> list[str]:
    values: list[str] = []
    for key in ("from", "form_name"):
        value = str(item.get(key) or "").strip()
        if value:
            values.append(value)
    return values


def _lkgc_name_candidates(item: dict) -> set[str]:
    name = str(item.get("name") or "").strip()
    candidates = {name} if name else set()
    for form_name in _lkgc_form_names(item):
        candidates.add(f"{name}（{form_name}）")
        candidates.add(f"{name}({form_name})")
    return candidates


def _find_lkgc_pet_for_pokemon(pokemon: dict, max_pages: int = 120, page_size: int = 100) -> dict | None:
    pokemon_name = str(pokemon.get("name") or "").strip()
    best_by_name: dict | None = None

    for page in range(1, max_pages + 1):
        raw = lkgc.fetch_pet_list(page=page, page_size=page_size)
        data = _normalize_lkgc_response(raw)
        if isinstance(data, dict):
            records = data.get("list") or data.get("data") or data.get("items") or []
        elif isinstance(data, list):
            records = data
        else:
            records = []
        if not records:
            break

        for item in records:
            if not isinstance(item, dict):
                continue
            if pokemon_name in _lkgc_name_candidates(item):
                best_by_name = item

    return best_by_name


def _fetch_lkgc_detail_for_pokemon(pokemon: dict) -> tuple[dict | None, dict | None]:
    pet = _find_lkgc_pet_for_pokemon(pokemon)
    if not pet:
        return None, None
    pet_id = str(pet.get("real_pet_id") or pet.get("pet_id") or "").strip()
    if not pet_id:
        return pet, None

    raw = lkgc.get_pet_info(pet_id)
    data = _normalize_lkgc_response(raw)
    if isinstance(data, list):
        detail = data[0] if data else None
    elif isinstance(data, dict):
        detail = data
    else:
        detail = None
    return pet, detail if isinstance(detail, dict) else None


def _infer_lkgc_skill_type(item: dict) -> str:
    category_id = item.get("category_id")
    damage_id = item.get("damage_id")
    if category_id == 1 and damage_id == 1:
        return "物攻"
    if category_id == 1 and damage_id == 2:
        return "魔攻"
    if category_id == 2 and damage_id == -1:
        return "防御"
    if category_id == 3 and damage_id == -1:
        return "状态"
    return ""


async def _resolve_lkgc_trait(detail: dict) -> int | None:
    """从 getPetInfo 的 feature_list 中 upsert 特性，返回 trait_id。"""
    feature_list = detail.get("feature_list") or []
    if not isinstance(feature_list, list) or not feature_list:
        return None
    ft = feature_list[0]
    name = str(ft.get("name") or "").strip()
    desc = str(ft.get("desc") or "").strip()
    if not name:
        return None
    return await ops_repository.upsert_trait(name, desc)


def _upload_lkgc_skill_icon(icon_url: str, warnings: list[str], skill_name: str) -> str:
    icon_url = (icon_url or "").strip()
    if not icon_url:
        return ""
    try:
        from oss.oss import get_client
        cos = get_client()
        return cos.upload_from_url(icon_url, prefix="skill/icon")
    except Exception as exc:
        warnings.append(f"技能 {skill_name} 图标上传失败：{exc}")
        return ""


def _upload_lkgc_pokemon_image(image_url: str, warnings: list[str], pokemon_name: str) -> str:
    """下载 lkgc 精灵图片并上传到 COS，返回 COS 地址。失败时返回空字符串。"""
    image_url = (image_url or "").strip()
    if not image_url:
        return ""
    try:
        from oss.oss import get_client
        cos = get_client()
        return cos.upload_from_url(image_url, prefix="pokemon/lkgc")
    except Exception as exc:
        warnings.append(f"精灵 {pokemon_name} 图片上传失败：{exc}")
        return ""


async def sync_pokemon_lkgc_skills_for_ops(user: dict, pokemon_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    pokemon = await ops_repository.get_pokemon_lkgc_sync_identity(pokemon_id)
    if not pokemon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")

    pet, detail = await asyncio.to_thread(_fetch_lkgc_detail_for_pokemon, pokemon)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未在洛克观测列表中匹配到该精灵")
    if not detail:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="洛克观测宠物详情为空")

    if not isinstance(detail.get("skill_list") or {}, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="洛克观测 skill_list 格式异常")

    warnings: list[str] = []
    result = await _sync_lkgc_pokemon_skills(pokemon_id, detail, warnings)
    response = {
        "pokemon_id": pokemon_id,
        "pokemon_name": pokemon.get("name") or "",
        "lkgc_pet_id": str((detail or {}).get("real_pet_id") or pet.get("real_pet_id") or ""),
        "lkgc_name": str((detail or {}).get("name") or pet.get("name") or ""),
        "request_total": result["request_total"],
        "matched_skill_count": result["matched_skill_count"],
        "inserted_skill_count": result["inserted_skill_count"],
        "inserted_relation_count": result["inserted_relation_count"],
        "updated_relation_count": result["updated_relation_count"],
        "skipped_count": result["skipped_count"],
        "warnings": warnings,
        "items": result["items"],
    }
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon",
        resource_id=str(pokemon_id),
        action="sync_lkgc_skills",
        before_json=None,
        after_json=response,
    )
    return response


async def _sync_lkgc_pokemon_skills(pokemon_id: int, detail: dict, warnings: list[str]) -> dict:
    """把 lkgc detail.skill_list 同步为该精灵的技能/关系。warnings 直接追加，不抛异常。"""
    source_map = [
        ("base", "原生技能"),
        ("bloodline", "血脉技能"),
        ("stone", "技能石技能"),
    ]
    skill_list = detail.get("skill_list") or {}
    if not isinstance(skill_list, dict):
        warnings.append("洛克广场 skill_list 格式异常，已跳过技能同步")
        skill_list = {}

    raw_skill_items: list[dict] = []
    for source_key, source_type in source_map:
        entries = skill_list.get(source_key) or []
        if not isinstance(entries, list):
            warnings.append(f"skill_list.{source_key} 不是数组，已跳过")
            continue
        for sort_order, item in enumerate(entries, start=1):
            if not isinstance(item, dict):
                warnings.append(f"skill_list.{source_key}[{sort_order}] 不是对象，已跳过")
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                warnings.append(f"skill_list.{source_key}[{sort_order}] 缺少技能名称，已跳过")
                continue
            raw_skill_items.append({
                "raw": item,
                "name": name,
                "source_type": source_type,
                "sort_order": sort_order,
            })

    existing_skill_names = await ops_repository.list_existing_skill_names([item["name"] for item in raw_skill_items])
    attribute_id_map = await ops_repository.list_lkgc_attribute_id_map()
    planned: list[dict] = []
    for raw_item in raw_skill_items:
        item = raw_item["raw"]
        icon = ""
        if raw_item["name"] not in existing_skill_names:
            icon = await asyncio.to_thread(
                _upload_lkgc_skill_icon,
                str(item.get("icon_url") or "").strip(),
                warnings,
                raw_item["name"],
            )

        # type_id（lkgc 属性 id）→ attribute.id
        attr_id: int | None = None
        raw_type_id = item.get("type_id")
        if isinstance(raw_type_id, (int, float)) and int(raw_type_id) > 0:
            lkgc_type_id = int(raw_type_id)
            attr_id = attribute_id_map.get(lkgc_type_id)
            if attr_id is None:
                warnings.append(
                    f"技能 {raw_item['name']}: type_id={lkgc_type_id} 未在 attribute.lkgc_id 中找到"
                )

        planned.append({
            "name": raw_item["name"],
            "source_type": raw_item["source_type"],
            "sort_order": raw_item["sort_order"],
            "power": int(item.get("power") or 0),
            "consume": int(item.get("take_energy") or 0),
            "skill_desc": _strip_lkgc_html(str(item.get("desc") or "")),
            "icon": icon,
            "type": _infer_lkgc_skill_type(item),
            "attr_id": attr_id,
        })

    result = await ops_repository.sync_pokemon_lkgc_skill_links(pokemon_id, planned)
    warnings.extend(result.get("warnings") or [])
    result["request_total"] = len(planned)
    return result


async def sync_pokemon_from_lkgc_for_ops(user: dict) -> dict:
    """遍历 lkgc getList 全量数据，按 name 匹配本库 pokemon，未命中则新增。"""
    # ensure_role(user, {"editor", "admin"})

    all_pets = await asyncio.to_thread(lkgc.fetch_all_pets, max_pages=120, page_size=100)
    if not all_pets:
        return {
            "total_checked": 0,
            "total_inserted": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "warnings": [],
            "items": [],
        }

    egg_group_map = await ops_repository.list_all_lkgc_egg_groups()
    attribute_id_map = await ops_repository.list_lkgc_attribute_id_map()
    warnings: list[str] = []
    items: list[dict] = []
    inserted = 0
    skipped = 0
    errors = 0

    # Build candidate names for all pets at once
    pet_info_list: list[tuple[dict, set[str]]] = []
    all_candidates: list[str] = []
    for pet in all_pets:
        candidates = _lkgc_name_candidates(pet)
        if not candidates:
            continue
        pet_info_list.append((pet, candidates))
        all_candidates.extend(candidates)

    existing_names = await ops_repository.check_pokemon_names_exist(all_candidates)

    for pet, candidates in pet_info_list:
        name = str(pet.get("name") or "").strip()
        match = existing_names & candidates

        if match:
            skipped += 1
            items.append({
                "name": next(iter(match)),
                "lkgc_name": name,
                "status": "skipped",
                "message": "已存在",
                "pokemon_id": None,
            })
            continue

        # New pokemon — fetch detail
        pet_id = str(pet.get("real_pet_id") or pet.get("pet_id") or "").strip()
        if not pet_id:
            errors += 1
            items.append({
                "name": name,
                "lkgc_name": name,
                "status": "error",
                "message": "缺少 real_pet_id",
                "pokemon_id": None,
            })
            continue

        raw = await asyncio.to_thread(lkgc.get_pet_info, pet_id)
        detail = _normalize_lkgc_response(raw)
        if isinstance(detail, list):
            detail = detail[0] if detail else None
        if not isinstance(detail, dict):
            errors += 1
            warnings.append(f"{name}: getPetInfo 返回为空，已跳过")
            items.append({
                "name": name,
                "lkgc_name": name,
                "status": "error",
                "message": "getPetInfo 返回为空",
                "pokemon_id": None,
            })
            continue

        try:
            payload = _build_lkgc_pokemon_payload(pet, detail, egg_group_map, attribute_id_map, warnings)
            # 处理特性（trait）
            trait_id = await _resolve_lkgc_trait(detail)
            if trait_id:
                payload["trait_id"] = trait_id
            if not payload:
                errors += 1
                items.append({
                    "name": name,
                    "lkgc_name": name,
                    "status": "error",
                    "message": "构建 payload 失败",
                    "pokemon_id": None,
                })
                continue

            # 下载精灵图片到 COS，替换临时外链
            cos_url = await asyncio.to_thread(_upload_lkgc_pokemon_image, payload.get("image", ""), warnings, name)
            if cos_url:
                payload["image"] = payload["detail_url"] = payload["image_lc"] = cos_url

            # yise 图片（如果有）
            yise_url = payload.get("image_yise", "") or ""
            if yise_url:
                cos_yise = await asyncio.to_thread(_upload_lkgc_pokemon_image, yise_url, warnings, f"{name}(异色)")
                if cos_yise:
                    payload["image_yise"] = cos_yise

            pokemon_id = await ops_repository.insert_pokemon_from_lkgc(payload)
            inserted += 1

            # 同步该精灵对应技能（复用 _sync_lkgc_pokemon_skills，warnings 直接合并）
            skill_summary: dict | None = None
            try:
                print(f"[lkgc-skill-sync] 开始同步精灵技能 pokemon_id={pokemon_id} name={payload['name']}")
                skill_result = await _sync_lkgc_pokemon_skills(pokemon_id, detail, warnings)
                skill_summary = {
                    "request_total": skill_result["request_total"],
                    "matched_skill_count": skill_result["matched_skill_count"],
                    "inserted_skill_count": skill_result["inserted_skill_count"],
                    "inserted_relation_count": skill_result["inserted_relation_count"],
                    "updated_relation_count": skill_result["updated_relation_count"],
                    "skipped_count": skill_result["skipped_count"],
                }
                print(
                    f"[lkgc-skill-sync] 精灵技能同步完成 pokemon_id={pokemon_id} name={payload['name']} "
                    f"request_total={skill_summary['request_total']} "
                    f"matched={skill_summary['matched_skill_count']} "
                    f"inserted_skill={skill_summary['inserted_skill_count']} "
                    f"inserted_relation={skill_summary['inserted_relation_count']} "
                    f"updated_relation={skill_summary['updated_relation_count']} "
                    f"skipped={skill_summary['skipped_count']}"
                )
            except Exception as skill_exc:
                warnings.append(f"{name}: 技能同步失败 - {skill_exc}")
                print(f"[lkgc-skill-sync] 精灵技能同步失败 pokemon_id={pokemon_id} name={payload['name']} err={skill_exc}")

            items.append({
                "name": payload["name"],
                "lkgc_name": name,
                "status": "inserted",
                "message": "已新增",
                "pokemon_id": pokemon_id,
                "skills": skill_summary,
            })
        except Exception as exc:
            errors += 1
            warnings.append(f"{name}: 写入失败 - {exc}")
            items.append({
                "name": name,
                "lkgc_name": name,
                "status": "error",
                "message": str(exc),
                "pokemon_id": None,
            })

    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon",
        resource_id="batch",
        action="sync_lkgc",
        before_json=None,
        after_json={"total_checked": len(all_pets), "total_inserted": inserted, "total_errors": errors},
    )

    return {
        "total_checked": len(all_pets),
        "total_inserted": inserted,
        "total_skipped": skipped,
        "total_errors": errors,
        "warnings": warnings,
        "items": items,
    }


def _build_lkgc_pokemon_payload(
        pet: dict, detail: dict, egg_group_map: dict[int, str],
        attribute_id_map: dict[int, int], warnings: list[str]
) -> dict | None:
    """将 lkgc 的 getList + getPetInfo 数据组装为 pokemon 行 payload。"""
    name = str(pet.get("name") or "").strip()
    if not name:
        return None

    # evolution stage → type / type_name
    stage = pet.get("evolution_stage")
    stage_map = {
        0: ("final", "最终形态"),
        1: ("stage1", "Ⅰ阶"),
        2: ("stage2", "Ⅱ阶"),
        3: ("final", "最终形态"),
    }
    pokemon_type, type_name = stage_map.get(stage, ("", ""))

    # stats
    hp = int(pet.get("sm") or 0)
    atk = int(pet.get("wg") or 0)
    matk = int(pet.get("mg") or 0)
    def_val = int(pet.get("wf") or 0)
    mdef = int(pet.get("mf") or 0)
    spd = int(pet.get("sd") or 0)
    total_race = hp + atk + matk + def_val + mdef + spd

    # egg groups
    egg_type_ids: list[int] = pet.get("egg_type_list") or []
    egg_group_names = [egg_group_map.get(eid, f"未知({eid})") for eid in egg_type_ids if eid in egg_group_map]
    for eid in egg_type_ids:
        if eid not in egg_group_map:
            warnings.append(f"{name}: egg_type_list 中的 {eid} 未在 lkgc_egg_group 中找到")

    # trait（由调用方通过 _resolve_lkgc_trait 异步处理）
    trait_id = 1

    # type_list → attribute ids（通过 attribute.lkgc_id 反查 attribute.id）
    type_list = detail.get("type_list") or pet.get("type_list") or []
    attribute_ids: list[int] = []
    for t in type_list:
        if not isinstance(t, (int, float)):
            continue
        lkgc_type_id = int(t)
        attr_id = attribute_id_map.get(lkgc_type_id)
        if attr_id is None:
            warnings.append(f"{name}: type_list 中的 lkgc_id={lkgc_type_id} 未在 attribute.lkgc_id 中找到")
            continue
        attribute_ids.append(attr_id)

    # name_en from icon_name
    icon_name = str(pet.get("icon_name") or detail.get("icon_name") or "").strip()
    name_en = icon_name.removeprefix("JL_") if icon_name else ""

    # main image
    main_url = str(pet.get("main_url") or "").strip()
    form = str(pet.get("form") or "").strip() or "original"
    form_name = str(pet.get("form_name") or "").strip() or "原始形态"

    return {
        "no": "",
        "name": name,
        "image": main_url,
        "type": pokemon_type,
        "type_name": type_name,
        "form": form,
        "form_name": form_name,
        "egg_group": ",".join(egg_group_names),
        "egg_groups": egg_group_names,
        "trait_id": trait_id,
        "detail_url": main_url,
        "image_lc": main_url,
        "image_yise": str(pet.get("yise_url") or detail.get("yise_url") or "").strip(),
        "chain_id": None,
        "hp": hp,
        "atk": atk,
        "matk": matk,
        "def_val": def_val,
        "mdef": mdef,
        "spd": spd,
        "total_race": total_race,
        "obtain_method": str(pet.get("position") or "").strip(),
        "name_en": name_en,
        "source_id": pet.get("base_id") or pet.get("source_id") or detail.get("base_id"),
        "attribute_ids": attribute_ids,
    }


async def get_pokemon_evolution_chain_for_ops(user: dict, pokemon_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    result = await ops_repository.get_pokemon_evolution_chain_for_ops(pokemon_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")
    return result


async def update_pokemon_evolution_chain_for_ops(user: dict, pokemon_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_pokemon_evolution_chain_for_ops(pokemon_id)
    if before is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")

    steps = payload.get("steps") or []
    normalized_steps: list[dict] = []
    for idx, step in enumerate(steps, start=1):
        pokemon_name = (step.get("pokemon_name") or "").strip()
        if not pokemon_name:
            continue
        normalized_steps.append(
            {
                "sort_order": max(1, int(step.get("sort_order") or idx)),
                "pokemon_name": pokemon_name,
                "evolution_condition": (step.get("evolution_condition") or "").strip(),
                "pre_evolution_condition": (step.get("pre_evolution_condition") or "").strip(),
            }
        )
    if not normalized_steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="进化链至少保留一条有效步骤")

    after = await ops_repository.save_pokemon_evolution_chain_for_ops(pokemon_id, normalized_steps)
    if after is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵不存在")

    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="evolution_chain",
        resource_id=str(after.get("chain_id") or ""),
        action="update",
        before_json=before,
        after_json=after,
    )
    return after


async def search_pokemon_evolution_chain_for_ops(user: dict, keyword: str) -> dict:
    ensure_role(user, {"editor", "admin"})
    result = await ops_repository.search_evolution_chain_for_ops(keyword)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到匹配的进化链")
    return result


def _friend_upload_stem(raw_stem: str) -> str:
    stem = re.sub(r"[^0-9A-Za-z._-]", "_", raw_stem).strip("._-")
    return stem[:120] if stem else ""


def _friend_upload_filename(original: str) -> str:
    path = Path(original)
    suf = path.suffix.lower()
    if suf not in _ALLOWED_FRIEND_IMAGE_SUFFIX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 webp、png、jpg、jpeg、gif",
        )
    stem = _friend_upload_stem(path.stem)
    if not stem:
        stem = uuid4().hex
    return f"{stem}{suf}"


def _friend_unique_dest(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suf = Path(filename).stem, Path(filename).suffix
    for i in range(2, 1000):
        alt = directory / f"{stem}_{i}{suf}"
        if not alt.exists():
            return alt
    return directory / f"{uuid4().hex}{suf}"


async def _save_image_upload(
        upload: UploadFile,
        *,
        upload_dir: str,
        base_url: str,
        allowed_suffix: set[str],
        max_bytes: int,
        suffix_hint: str,
) -> dict:
    if not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择文件")
    path = Path(upload.filename)
    suf = path.suffix.lower()
    if suf not in allowed_suffix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持 {suffix_hint}",
        )
    stem = _friend_upload_stem(path.stem) or uuid4().hex
    filename = f"{stem}{suf}"
    root = Path(upload_dir).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法创建上传目录: {exc}",
        ) from exc
    dest = _friend_unique_dest(root, filename)
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件不能超过 {max_bytes // (1024 * 1024)}MB",
        )
    try:
        dest.write_bytes(content)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"写入文件失败: {exc}",
        ) from exc
    return {"filename": dest.name, "preview_url": f"{base_url}{dest.name}"}


async def save_yise_image_upload(user: dict, upload: UploadFile) -> dict:
    """将异色立绘保存到 YISE_IMAGE_UPLOAD_DIR，返回写入库用的 image_yise 与预览 URL。"""
    ensure_role(user, {"editor", "admin"})
    from config import YISE_IMAGE_BASE_URL, YISE_IMAGE_UPLOAD_DIR

    result = await _save_image_upload(
        upload,
        upload_dir=YISE_IMAGE_UPLOAD_DIR,
        base_url=YISE_IMAGE_BASE_URL,
        allowed_suffix=_ALLOWED_FRIEND_IMAGE_SUFFIX,
        max_bytes=_MAX_FRIEND_IMAGE_BYTES,
        suffix_hint="webp、png、jpg、jpeg、gif",
    )
    image_yise = f"/yise/friends/{result['filename']}"
    return {"image_yise": image_yise, "preview_url": result["preview_url"]}


async def save_friend_image_upload(user: dict, upload: UploadFile) -> dict:
    """将朋友图保存到 FRIEND_IMAGE_UPLOAD_DIR，返回写入库用的 image_lc 与预览 URL。"""
    ensure_role(user, {"editor", "admin"})
    from config import FRIEND_IMAGE_BASE_URL, FRIEND_IMAGE_UPLOAD_DIR

    if not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择文件")

    filename = _friend_upload_filename(upload.filename)
    root = Path(FRIEND_IMAGE_UPLOAD_DIR).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法创建上传目录: {exc}",
        ) from exc

    dest = _friend_unique_dest(root, filename)
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    if len(content) > _MAX_FRIEND_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片不能超过 5MB")

    try:
        dest.write_bytes(content)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"写入文件失败: {exc}",
        ) from exc

    image_lc = dest.name
    preview_url = f"{FRIEND_IMAGE_BASE_URL}{image_lc}"
    return {"image_lc": image_lc, "preview_url": preview_url}


async def save_resonance_magic_icon_upload(user: dict, upload: UploadFile) -> dict:
    """将共鸣魔法图标保存到 RESONANCE_MAGIC_ICON_UPLOAD_DIR，返回写入库用的 icon 与预览 URL。"""
    ensure_role(user, {"editor", "admin"})
    from config import RESONANCE_MAGIC_ICON_BASE_URL, RESONANCE_MAGIC_ICON_UPLOAD_DIR

    result = await _save_image_upload(
        upload,
        upload_dir=RESONANCE_MAGIC_ICON_UPLOAD_DIR,
        base_url=RESONANCE_MAGIC_ICON_BASE_URL,
        allowed_suffix=_ALLOWED_FRIEND_IMAGE_SUFFIX,
        max_bytes=2 * 1024 * 1024,
        suffix_hint="webp、png、jpg、jpeg、gif",
    )
    icon = f"/resonance-magic/{result['filename']}"
    return {"icon": icon, "preview_url": result["preview_url"]}


def _normalize_skill_payload(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="技能名称不能为空")
    if len(name) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="技能名称过长")
    try:
        power = int(payload.get("power") or 0)
        consume = int(payload.get("consume") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="威力/消耗必须为整数") from exc
    if power < 0 or power > 9999:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="威力必须在 0-9999 之间")
    if consume < 0 or consume > 9999:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消耗必须在 0-9999 之间")
    return {
        "name": name,
        "attr": (payload.get("attr") or "").strip(),
        "type": (payload.get("type") or "").strip(),
        "power": power,
        "consume": consume,
        "skill_desc": (payload.get("skill_desc") or "").strip(),
        "icon": (payload.get("icon") or "").strip(),
    }


async def list_skills_for_ops(
        user: dict,
        keyword: str = "",
        attr: str = "",
        type_: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_skills_for_ops(
        keyword=keyword.strip(),
        attr=attr.strip(),
        type_=type_.strip(),
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_skill_detail_for_ops(user: dict, skill_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    detail = await ops_repository.get_skill_for_ops(skill_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    return detail


async def create_skill_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_skill_payload(payload)
    exists = await ops_repository.get_skill_by_name(normalized["name"])
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="技能名称已存在")
    created = await ops_repository.create_skill_for_ops(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_skill_for_ops(user: dict, skill_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_skill_for_ops(skill_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    normalized = _normalize_skill_payload(payload)
    if normalized["name"] != before["name"]:
        exists = await ops_repository.get_skill_by_name(normalized["name"])
        if exists and int(exists["id"]) != skill_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="技能名称已存在")
    updated = await ops_repository.update_skill_for_ops(skill_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill",
        resource_id=str(skill_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_skill_for_ops(user: dict, skill_id: int, force: bool = False) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_skill_for_ops(skill_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    total, _ = await ops_repository.list_skill_usages_for_ops(skill_id)
    if total > 0:
        if not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"该技能已被 {total} 只精灵使用，不能直接删除",
            )
        ensure_role(user, {"admin"})
    deleted = await ops_repository.delete_skill_for_ops(skill_id, force=force)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill",
        resource_id=str(skill_id),
        action="delete" if not force else "force_delete",
        before_json=before,
        after_json=None,
    )


async def list_skill_usages_for_ops(user: dict, skill_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_skill_for_ops(skill_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    total, items = await ops_repository.list_skill_usages_for_ops(skill_id)
    return {"total": total, "items": items}


async def get_skill_options_for_ops(user: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    return await ops_repository.list_skill_options_for_ops()


_MAX_OBTAIN_METHOD_LEN = 255


def _normalize_obtain_method(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="获取方式不能为空")
    if len(text) > _MAX_OBTAIN_METHOD_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取方式不能超过 {_MAX_OBTAIN_METHOD_LEN} 字",
        )
    return text


async def list_skill_stones_for_ops(
        user: dict,
        keyword: str = "",
        attr: str = "",
        type_: str = "",
        obtain_keyword: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_skill_stones_for_ops(
        keyword=keyword.strip(),
        attr=attr.strip(),
        type_=type_.strip(),
        obtain_keyword=obtain_keyword.strip(),
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_skill_stone_detail_for_ops(user: dict, stone_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    detail = await ops_repository.get_skill_stone_for_ops(stone_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能石不存在")
    return detail


async def create_skill_stone_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    try:
        skill_id = int(payload.get("skill_id") or 0)
    except (TypeError, ValueError):
        skill_id = 0
    if skill_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择技能")
    obtain_method = _normalize_obtain_method(payload.get("obtain_method"))

    skill = await ops_repository.get_skill_for_ops(skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="技能不存在")
    exists = await ops_repository.get_skill_stone_by_skill_id(skill_id)
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该技能已存在技能石")

    created = await ops_repository.create_skill_stone_for_ops(skill_id, obtain_method)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill_stone",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_skill_stone_for_ops(user: dict, stone_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_skill_stone_for_ops(stone_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能石不存在")
    obtain_method = _normalize_obtain_method(payload.get("obtain_method"))
    updated = await ops_repository.update_skill_stone_for_ops(stone_id, obtain_method)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能石不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill_stone",
        resource_id=str(stone_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_skill_stone_for_ops(user: dict, stone_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_skill_stone_for_ops(stone_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能石不存在")
    deleted = await ops_repository.delete_skill_stone_for_ops(stone_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能石不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="skill_stone",
        resource_id=str(stone_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def list_available_skills_for_stone(user: dict, keyword: str = "", limit: int = 30) -> dict:
    ensure_role(user, {"editor", "admin"})
    safe_limit = max(1, min(limit, 100))
    items = await ops_repository.list_available_skills_for_stone(
        keyword=keyword.strip(), limit=safe_limit
    )
    return {"items": items}


def _normalize_resonance_magic_payload(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共鸣魔法名称不能为空")
    if len(name) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共鸣魔法名称过长")
    try:
        max_usage_count = int(payload.get("max_usage_count") or 1)
        sort_order = int(payload.get("sort_order") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="使用次数和排序必须为整数")
    if max_usage_count < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="最大可使用次数至少为1")
    return {
        "name": name,
        "description": (payload.get("description") or "").strip(),
        "max_usage_count": max_usage_count,
        "icon": (payload.get("icon") or "").strip(),
        "sort_order": sort_order,
    }


async def list_resonance_magics_for_ops(
        user: dict,
        keyword: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_resonance_magics_for_ops(
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_resonance_magic_for_ops(user: dict, magic_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    detail = await ops_repository.get_resonance_magic_for_ops(magic_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="共鸣魔法不存在")
    return detail


async def create_resonance_magic_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_resonance_magic_payload(payload)
    exists = await ops_repository.get_resonance_magic_by_name(normalized["name"])
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共鸣魔法名称已存在")
    created = await ops_repository.create_resonance_magic_for_ops(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="resonance_magic",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_resonance_magic_for_ops(user: dict, magic_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_resonance_magic_for_ops(magic_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="共鸣魔法不存在")
    normalized = _normalize_resonance_magic_payload(payload)
    if normalized["name"] != before["name"]:
        exists = await ops_repository.get_resonance_magic_by_name(normalized["name"])
        if exists and int(exists["id"]) != magic_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共鸣魔法名称已存在")
    updated = await ops_repository.update_resonance_magic_for_ops(magic_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="共鸣魔法不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="resonance_magic",
        resource_id=str(magic_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_resonance_magic_for_ops(user: dict, magic_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_resonance_magic_for_ops(magic_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="共鸣魔法不存在")
    deleted = await ops_repository.delete_resonance_magic_for_ops(magic_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="共鸣魔法不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="resonance_magic",
        resource_id=str(magic_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def save_skill_icon_upload(user: dict, upload: UploadFile) -> dict:
    ensure_role(user, {"editor", "admin"})
    from config import SKILL_ICON_BASE_URL, SKILL_ICON_UPLOAD_DIR

    result = await _save_image_upload(
        upload,
        upload_dir=SKILL_ICON_UPLOAD_DIR,
        base_url=SKILL_ICON_BASE_URL,
        allowed_suffix=_ALLOWED_SKILL_ICON_SUFFIX,
        max_bytes=_MAX_SKILL_ICON_BYTES,
        suffix_hint="webp、png、jpg、jpeg、gif",
    )
    return {"icon": result["filename"], "preview_url": result["preview_url"]}


# ---------- 名词解释（pokemon_mark）维护 ----------


def _normalize_pokemon_mark_payload(payload: dict) -> dict:
    key = (payload.get("key") or "").strip()
    zh_name = (payload.get("zh_name") or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="key 不能为空")
    if not zh_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="中文名不能为空")
    return {
        "key": key,
        "zh_name": zh_name,
        "zh_description": (payload.get("zh_description") or "").strip(),
        "sort_order": int(payload.get("sort_order") or 0),
        "image": (payload.get("image") or "").strip(),
    }


async def list_pokemon_marks_for_ops(
        user: dict,
        keyword: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    safe_page = max(page or 1, 1)
    safe_page_size = max(1, min(page_size or 10, 100))
    total, items = await ops_repository.list_pokemon_marks_for_ops(
        keyword=keyword,
        page=safe_page,
        page_size=safe_page_size,
    )
    return {"total": total, "page": safe_page, "page_size": safe_page_size, "items": items}


async def create_pokemon_mark_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_pokemon_mark_payload(payload)
    if await ops_repository.get_pokemon_mark_by_key(normalized["key"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识 key 已存在")
    if await ops_repository.get_pokemon_mark_by_sort_order(normalized["sort_order"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="排序值已被其他词条占用")
    created = await ops_repository.create_pokemon_mark(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_pokemon_mark_for_ops(user: dict, mark_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_pokemon_mark_by_id(mark_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    normalized = _normalize_pokemon_mark_payload(payload)
    if normalized["key"] != before["key"]:
        exists = await ops_repository.get_pokemon_mark_by_key(normalized["key"])
        if exists and int(exists["id"]) != mark_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识 key 已存在")
    if normalized["sort_order"] != before["sort_order"]:
        exists = await ops_repository.get_pokemon_mark_by_sort_order(normalized["sort_order"])
        if exists and int(exists["id"]) != mark_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="排序值已被其他词条占用")
    updated = await ops_repository.update_pokemon_mark(mark_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(mark_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_pokemon_mark_for_ops(user: dict, mark_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_pokemon_mark_by_id(mark_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    deleted = await ops_repository.delete_pokemon_mark(mark_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(mark_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


# ---------- 印记维护（pokemon_mark 复用同一张表） ----------


def _normalize_mark_payload(payload: dict) -> dict:
    key = (payload.get("key") or "").strip()
    zh_name = (payload.get("zh_name") or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识不能为空")
    if not zh_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="中文名不能为空")
    if len(key) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识不能超过 50 字符")
    if len(zh_name) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="中文名不能超过 50 字符")
    return {
        "key": key,
        "zh_name": zh_name,
        "zh_description": (payload.get("zh_description") or "").strip(),
        "image": (payload.get("image") or "").strip(),
        "sort_order": int(payload.get("sort_order") or 0),
    }


async def list_marks_for_ops(
        user: dict,
        keyword: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_marks_for_ops(
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def create_mark_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_mark_payload(payload)
    exists = await ops_repository.get_mark_by_key(normalized["key"])
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识已存在")
    created = await ops_repository.create_mark_for_ops(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_mark_for_ops(user: dict, mark_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_mark_for_ops(mark_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="印记不存在")
    normalized = _normalize_mark_payload(payload)
    if normalized["key"] != before["key"]:
        exists = await ops_repository.get_mark_by_key(normalized["key"])
        if exists and int(exists["id"]) != mark_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文标识已存在")
    updated = await ops_repository.update_mark_for_ops(mark_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="印记不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(mark_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_mark_for_ops(user: dict, mark_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_mark_for_ops(mark_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="印记不存在")
    deleted = await ops_repository.delete_mark_for_ops(mark_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="印记不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_mark",
        resource_id=str(mark_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


# ---------- 图鉴筛选项（pokemon_filter_option）维护 ----------


_ALLOWED_FILTER_TYPES = {"shiny", "sort"}
_ALLOWED_FILTER_ORDER_BY = {
    "",
    "no",
    "total_stats",
    "hp",
    "atk",
    "matk",
    "def_val",
    "mdef",
    "spd",
}
_ALLOWED_FILTER_ORDER_DIR = {"", "asc", "desc"}


def _normalize_filter_option_payload(payload: dict) -> dict:
    code = (payload.get("code") or "").strip()
    label = (payload.get("label") or "").strip()
    filter_type = (payload.get("filter_type") or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code 不能为空")
    if len(code) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code 不能超过 50 字符")
    if not label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="label 不能为空")
    if len(label) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="label 不能超过 100 字符")
    if filter_type not in _ALLOWED_FILTER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"filter_type 必须是 {sorted(_ALLOWED_FILTER_TYPES)} 之一",
        )

    order_by = (payload.get("order_by") or "").strip()
    order_dir = (payload.get("order_dir") or "").strip().lower()
    if order_by not in _ALLOWED_FILTER_ORDER_BY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"order_by 必须是 {sorted(_ALLOWED_FILTER_ORDER_BY)} 之一",
        )
    if order_dir not in _ALLOWED_FILTER_ORDER_DIR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_dir 必须为 asc / desc 或空",
        )
    if filter_type == "sort":
        if not order_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="排序类筛选必须指定 order_by",
            )
        if not order_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="排序类筛选必须指定 order_dir",
            )

    return {
        "code": code,
        "label": label,
        "filter_type": filter_type,
        "order_by": order_by,
        "order_dir": order_dir,
        "sort_order": int(payload.get("sort_order") or 0),
        "is_active": bool(payload.get("is_active", True)),
    }


async def list_pokemon_filter_options_for_ops(
        user: dict,
        keyword: str = "",
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    safe_page = max(page or 1, 1)
    safe_page_size = max(1, min(page_size or 10, 100))
    total, items = await pokemon_filter_repository.list_filter_options_for_ops(
        keyword=keyword,
        page=safe_page,
        page_size=safe_page_size,
    )
    return {"total": total, "page": safe_page, "page_size": safe_page_size, "items": items}


async def create_pokemon_filter_option_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = _normalize_filter_option_payload(payload)
    if await pokemon_filter_repository.get_filter_option_by_code(normalized["code"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code 已存在")
    created = await pokemon_filter_repository.create_filter_option(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_filter_option",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_pokemon_filter_option_for_ops(user: dict, option_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await pokemon_filter_repository.get_filter_option_by_id(option_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="筛选项不存在")
    normalized = _normalize_filter_option_payload(payload)
    if normalized["code"] != before["code"]:
        exists = await pokemon_filter_repository.get_filter_option_by_code(normalized["code"])
        if exists and int(exists["id"]) != option_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code 已存在")
    updated = await pokemon_filter_repository.update_filter_option(option_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="筛选项不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_filter_option",
        resource_id=str(option_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_pokemon_filter_option_for_ops(user: dict, option_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await pokemon_filter_repository.get_filter_option_by_id(option_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="筛选项不存在")
    deleted = await pokemon_filter_repository.delete_filter_option(option_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="筛选项不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_filter_option",
        resource_id=str(option_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


# ---------- 孵化宠物（egg_hatch_pet）维护 ----------


def _normalize_egg_hatch_pet_payload(payload: dict) -> dict:
    def _non_negative_int(value, label: str) -> int:
        try:
            num = int(value or 0)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}必须是整数")
        if num < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}不能为负数")
        return num

    weight_low = _non_negative_int(payload.get("weight_low"), "体重下限")
    weight_high = _non_negative_int(payload.get("weight_high"), "体重上限")
    height_low = _non_negative_int(payload.get("height_low"), "身高下限")
    height_high = _non_negative_int(payload.get("height_high"), "身高上限")
    if weight_high < weight_low:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="体重上限不能小于下限")
    if height_high < height_low:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="身高上限不能小于下限")
    return {
        "is_leader_form": bool(payload.get("is_leader_form")),
        "hatch_data": _non_negative_int(payload.get("hatch_data"), "孵化时间"),
        "weight_low": weight_low,
        "weight_high": weight_high,
        "height_low": height_low,
        "height_high": height_high,
        "big_size_length_min": _non_negative_int(payload.get("big_size_length_min"), "大体型身长下限"),
        "big_size_weight_min": _non_negative_int(payload.get("big_size_weight_min"), "大体型体重下限"),
        "small_size_length_max": _non_negative_int(payload.get("small_size_length_max"), "小体型身长上限"),
        "small_size_weight_max": _non_negative_int(payload.get("small_size_weight_max"), "小体型体重上限"),
    }


async def list_egg_hatch_pets_for_ops(
        user: dict,
        keyword: str = "",
        is_leader_form: bool | None = None,
        page: int = 1,
        page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    safe_page = max(page or 1, 1)
    safe_page_size = max(1, min(page_size or 10, 100))
    total, items = await ops_repository.list_egg_hatch_pets_for_ops(
        keyword=keyword.strip(),
        is_leader_form=is_leader_form,
        page=safe_page,
        page_size=safe_page_size,
    )
    return {"total": total, "page": safe_page, "page_size": safe_page_size, "items": items}


async def get_egg_hatch_pet_detail_for_ops(user: dict, pet_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    detail = await ops_repository.get_egg_hatch_pet_for_ops(pet_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="孵化宠物配置不存在")
    return detail


async def create_egg_hatch_pet_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    try:
        pokemon_id = int(payload.get("pokemon_id") or 0)
    except (TypeError, ValueError):
        pokemon_id = 0
    if pokemon_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择宠物")
    if not await ops_repository.get_pokemon_detail_for_ops(pokemon_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="宠物不存在")
    if await ops_repository.get_egg_hatch_pet_by_pokemon_id(pokemon_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该宠物已配置孵化数据")
    normalized = _normalize_egg_hatch_pet_payload(payload)
    normalized["pokemon_id"] = pokemon_id
    created = await ops_repository.create_egg_hatch_pet_for_ops(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="egg_hatch_pet",
        resource_id=str(created["id"]),
        action="create",
        before_json=None,
        after_json=created,
    )
    return created


async def update_egg_hatch_pet_for_ops(user: dict, pet_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_egg_hatch_pet_for_ops(pet_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="孵化宠物配置不存在")
    normalized = _normalize_egg_hatch_pet_payload(payload)
    updated = await ops_repository.update_egg_hatch_pet_for_ops(pet_id, normalized)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="孵化宠物配置不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="egg_hatch_pet",
        resource_id=str(pet_id),
        action="update",
        before_json=before,
        after_json=updated,
    )
    return updated


async def delete_egg_hatch_pet_for_ops(user: dict, pet_id: int) -> None:
    ensure_role(user, {"editor", "admin"})
    before = await ops_repository.get_egg_hatch_pet_for_ops(pet_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="孵化宠物配置不存在")
    deleted = await ops_repository.delete_egg_hatch_pet_for_ops(pet_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="孵化宠物配置不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="egg_hatch_pet",
        resource_id=str(pet_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def list_available_pokemon_for_egg_hatch(user: dict, keyword: str = "", limit: int = 30) -> dict:
    ensure_role(user, {"editor", "admin"})
    safe_limit = max(1, min(limit or 30, 100))
    items = await ops_repository.list_available_pokemon_for_egg_hatch(
        keyword=keyword.strip(),
        limit=safe_limit,
    )
    return {"items": items}
