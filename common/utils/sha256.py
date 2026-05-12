"""通用 HMAC-SHA256 签名工具，用于 CloudBase 函数调用授权。"""

import hashlib
import hmac
import json
import time
from typing import Any, Iterable, Mapping, Optional


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hmac_sha256(secret: str, data: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def canonical_body(body: Any) -> str:
    """将 body 序列化为参与签名的规范字符串。"""
    if isinstance(body, (bytes, bytearray)):
        return body.decode("utf-8")
    if isinstance(body, str):
        return body
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def current_timestamp_ms() -> str:
    return str(int(time.time() * 1000))


def generate_authorization(
    method: str,
    path: str,
    query: str,
    body: Any,
    headers: Mapping[str, str],
    access_key: str,
    secret_key: str,
    signed_headers: Optional[Iterable[str]] = None,
    timestamp: Optional[str] = None,
) -> str:
    """生成 `HMAC-SHA256` Authorization 头。

    :param signed_headers: 参与签名的 header key 列表，默认包含 CloudBase 调用所需字段。
    """
    if timestamp is None:
        timestamp = current_timestamp_ms()

    default_signed = [
        "x-client-timestamp",
        "x-from-app-id",
        "x-from-env-id",
        "x-from-function-name",
        "x-from-instance-id",
        "x-to-env-id",
        "x-to-function-name",
    ]
    keys = sorted(signed_headers) if signed_headers else sorted(default_signed)

    canonical_headers = "".join(
        f"{k.lower()}:{headers[k]}\n" for k in keys
    )

    body_hash = sha256_hex(canonical_body(body))

    canonical_request = (
        f"{method.upper()}\n"
        f"{path}\n"
        f"{query}\n"
        f"{canonical_headers}\n"
        f"{';'.join(keys)}\n"
        f"{body_hash}\n"
    )

    string_to_sign = (
        "HMAC-SHA256\n"
        f"{timestamp}\n"
        f"{sha256_hex(canonical_request)}\n"
    )

    signature = hmac_sha256(secret_key, string_to_sign)

    return (
        f"HMAC-SHA256 "
        f"Credential={access_key}, "
        f"SignedHeaders={';'.join(keys)}, "
        f"Signature={signature}"
    )
