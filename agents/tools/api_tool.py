"""通用 API 调用工具。

抽出原本散在 main_agent.py 的 HTTP 工具，方便多个 agent / subagent 复用。
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from langchain_core.tools import tool

_API_BASE_URL = os.getenv("POKEMON_API_BASE_URL", "http://localhost:8000")

try:
    import httpx

    _HTTP_LIB = "httpx"
except ImportError:
    import urllib.request as _urllib_request

    _HTTP_LIB = "urllib"


def _http_request(method: str, url: str, params: dict | None, body: dict | None) -> Any:
    """底层 HTTP 请求，httpx 优先，未装时退化到 urllib。"""
    if _HTTP_LIB == "httpx":
        with httpx.Client(timeout=15) as client:
            resp = client.request(method, url, params=params, json=body)
            resp.raise_for_status()
            return resp.json()

    from urllib.parse import urlencode

    if params:
        parts: list[tuple[str, str]] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, list):
                parts.extend((key, str(item)) for item in value)
            elif str(value) != "":
                parts.append((key, str(value)))
        if parts:
            url = f"{url}?{urlencode(parts)}"

    req = _urllib_request.Request(url, method=method.upper())
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    with _urllib_request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


@tool
def call_api(
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
) -> str:
    """通用 API 调用工具。根据 Skill 文档中描述的接口规范发起 HTTP 请求。

    Args:
        method: HTTP 方法，如 GET、POST、PUT、DELETE。
        path: API 路径，如 /api/pokemon/皮卡丘。不要包含域名。
        params: URL 查询参数（用于 GET 请求的筛选/分页等）。
        body: 请求体（用于 POST/PUT 请求）。

    Returns:
        API 返回的 JSON 数据（字符串格式）。
    """
    url = f"{_API_BASE_URL.rstrip('/')}{path}"
    try:
        result = _http_request(method.upper(), url, params, body)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
