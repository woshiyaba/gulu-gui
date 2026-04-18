import base64
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from api.repositories import ops_repository

OPS_TOKEN_SECRET = os.getenv("OPS_TOKEN_SECRET", "ops-dev-secret")
OPS_TOKEN_TTL_SECONDS = int(os.getenv("OPS_TOKEN_TTL_SECONDS", "43200"))
OPS_INIT_USERNAME = os.getenv("OPS_INIT_USERNAME", "admin")
OPS_INIT_PASSWORD = os.getenv("OPS_INIT_PASSWORD", "admin123456")
OPS_INIT_NICKNAME = os.getenv("OPS_INIT_NICKNAME", "默认管理员")

_ALLOWED_FRIEND_IMAGE_SUFFIX = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
_MAX_FRIEND_IMAGE_BYTES = 5 * 1024 * 1024


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
    ensure_role(user, {"admin"})
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
    ensure_role(user, {"admin"})
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
    result["skill_sources"] = ["原生技能", "学习技能"]
    return result


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
                "sort_order": int(step.get("sort_order") or idx),
                "pokemon_name": pokemon_name,
                "evolution_condition": (step.get("evolution_condition") or "").strip(),
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
