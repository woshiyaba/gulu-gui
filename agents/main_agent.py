"""
main_agent — 任务规划 Agent。

架构：Skill 定义 API 规范 + 通用 call_api 工具执行。
- Skills（SKILL.md）自动加载为上下文，描述可用的 API 端点和参数
- Agent 读取 skill 文档，理解接口规范，通过 call_api 工具发起调用
- 扩展新功能只需添加 SKILL.md，无需改代码
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.tools import tool

from common.utils.llm_utils import (
    DEFAULT_SKILLS_DIR,
    PROJECT_ROOT,
    ReadOnlyFilesystemBackend,
    create_app_deep_agent,
)

# ---------------------------------------------------------------------------
# 通用 API 调用工具
# ---------------------------------------------------------------------------

_API_BASE_URL = os.getenv("POKEMON_API_BASE_URL", "http://localhost:8000")

try:
    import httpx
    _HTTP_LIB = "httpx"
except ImportError:
    import urllib.request as _urllib_request
    _HTTP_LIB = "urllib"


def _http_request(method: str, url: str, params: dict | None, body: dict | None) -> Any:
    """底层 HTTP 请求，支持 httpx / urllib 两种后端。"""
    if _HTTP_LIB == "httpx":
        with httpx.Client(timeout=15) as client:
            resp = client.request(method, url, params=params, json=body)
            resp.raise_for_status()
            return resp.json()
    else:
        from urllib.parse import urlencode
        if params:
            parts = []
            for k, v in params.items():
                if v is None:
                    continue
                if isinstance(v, list):
                    for item in v:
                        parts.append((k, str(item)))
                elif str(v) != "":
                    parts.append((k, str(v)))
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
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是洛克王国精灵图鉴助手，一个智能任务规划器。

你的职责：
1. 理解用户的问题或请求。
2. 阅读已加载的 Skill 文档，了解可用的 API 端点和参数格式。
3. 通过 call_api 工具调用对应的接口获取数据。
4. 将查询结果整理为用户友好的回答。

## 工作方式

你拥有一个 **call_api** 工具，可以发起 HTTP 请求。
Skill 文档中详细描述了每个 API 端点的路径、参数和返回格式。
请严格按照 Skill 文档中的接口规范来构造 call_api 的参数。

示例：查询精灵详情
→ call_api(method="GET", path="/api/pokemon/皮卡丘")

示例：搜索火系技能
→ call_api(method="GET", path="/api/skills", params={"attr": "火"})

## 规则

- **必须** 通过 call_api 工具获取数据，不要编造数据。
- **禁止** 编写脚本、创建文件或通过 shell 执行命令。
- 一个问题可能需要多次调用 call_api（如比较两只精灵需要分别查询）。
- 如果 API 返回错误，向用户解释原因。
- 回答使用中文，保持简洁友好。
- 回答尽量简洁 回复内容保持在0~100字之间
"""

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


def create_main_agent():
    """创建并返回 main_agent 实例。"""
    backend = ReadOnlyFilesystemBackend(root_dir=PROJECT_ROOT, virtual_mode=True)
    return create_app_deep_agent(
        system_prompt=SYSTEM_PROMPT,
        skills_dir=DEFAULT_SKILLS_DIR,
        backend=backend,
        tools=[call_api],
        name="main-agent",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _extract_reply(result: dict) -> str:
    """从 agent 返回结果中提取最后一条 AI 回复文本。"""
    for msg in reversed(result.get("messages", [])):
        if msg.type != "ai" or not msg.content:
            continue
        content = msg.content
        if isinstance(content, list):
            return "".join(
                block["text"]
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        return content
    return ""


def run_interactive():
    """启动交互式命令行对话。"""
    agent = create_main_agent()
    thread_id = uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 50)
    print("洛克王国精灵图鉴助手 (输入 exit 退出)")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("再见！")
            break

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
        reply = _extract_reply(result)
        if reply:
            print(f"\n助手: {reply}")


if __name__ == "__main__":
    run_interactive()
