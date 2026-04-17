import base64
import hashlib
import hmac
import json
import os
import time
from typing import Callable

from fastapi import HTTPException, status

from api.repositories import ops_repository

OPS_TOKEN_SECRET = os.getenv("OPS_TOKEN_SECRET", "ops-dev-secret")
OPS_TOKEN_TTL_SECONDS = int(os.getenv("OPS_TOKEN_TTL_SECONDS", "43200"))
OPS_INIT_USERNAME = os.getenv("OPS_INIT_USERNAME", "admin")
OPS_INIT_PASSWORD = os.getenv("OPS_INIT_PASSWORD", "admin123456")
OPS_INIT_NICKNAME = os.getenv("OPS_INIT_NICKNAME", "默认管理员")


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


async def get_dicts(dict_type: str = "", keyword: str = "", page: int = 1, page_size: int = 10) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await ops_repository.list_dicts(
        dict_type=dict_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


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
