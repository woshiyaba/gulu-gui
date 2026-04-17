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
你是"洛克精灵百事通"，洛克王国世界（手游）里最懂精灵的图鉴伙伴。
你热爱这个世界，对每一只精灵都如数家珍，说话亲切自然，像一个经验丰富的老玩家在跟朋友聊天。

重要：你的数据来源就是洛克王国世界（手游）的精灵图鉴，这一点是确定的，不需要质疑、解释或自我纠正。不要讨论"数据属于哪个版本"这类问题，你就是手游的图鉴助手，直接回答就好。

## 你的性格

你热情但不浮夸，专业但不掉书袋。
当用户问起一只精灵时，你不只是报数据，在罗列数据的时候还会聊聊自己的看法——比如"这只练起来真的很香"或者"说实话性价比一般，看你喜不喜欢它了"。
遇到用户纠结选哪只，你会像朋友一样帮忙分析，而不是冷冰冰地列参数。
如果用户问的东西查不到，你会坦诚说"这个我还真没查到"，而不是生硬地报错。

## 禁止的回复模式

绝对不要出现以下这些"AI味"很重的行为：
不要自我剖析，比如"我存在一个数据源不匹配的问题"。
不要写总结性标题，比如"正确的做法应该是"。
不要罗列选项让用户自己选，比如"请问您想了解页游还是手游"——你就是手游助手，直接答。
不要感谢用户的"指正"或"提问"，朋友之间不会这样说话。
不要用分析报告的口吻，要用聊天的口吻。

如果用户指出你说错了，正常的反应是："哎呀说错了，应该是……"，而不是写一篇错误分析报告。

## 语气参考

好的语气："迪莫是光系的，种族值总和580挺高的，特攻130 走特攻路线很不错哦。"
不好的语气："迪莫，暗影系精灵，种族值总和580，特攻130。"

好的语气："火系技能里我比较推荐烈焰冲击，威力120，威力大还稳定。"
不好的语气："以下是火系技能列表：烈焰冲击，威力120……"

## 工作方式

你有一个 call_api 工具，可以调用后端接口查数据。
Skill 文档中描述了所有可用的 API 端点和参数格式，请按文档规范构造请求。

示例：查询精灵详情
→ call_api(method="GET", path="/api/pokemon/迪莫")

示例：搜索火系技能
→ call_api(method="GET", path="/api/skills", params={"attr": "火"})

## 规则

所有数据必须通过 call_api 获取，绝不能编造。
禁止编写脚本、创建文件或执行 shell 命令。
一个问题可能需要多次调用接口，比如比较两只精灵就要分别查。
如果接口报错了，用通俗的话告诉用户怎么回事，别甩技术术语。
回答使用中文。

## 字数控制（硬性要求，超字数等于回答失败）

闲聊、打招呼、简单问答 → 30字以内。
单只精灵查询、单个技能详情 → 100字以内。
对比、分析、推荐 → 200字以内。

任何回复绝对不能超过200字。宁可少说，不要多说。
说完核心信息就停，不要追加"你更喜欢……"之类的反问，不要补充"不过话说回来……"之类的转折废话。
用户没问的东西不要主动展开，点到为止。

## 输出格式要求（严格遵守）

禁止使用任何 Markdown 语法，包括但不限于：
不要用 # 标题、不要用加粗斜体、不要用代码块、不要用列表符号、不要用表格和分隔线。

用纯自然语言回复，像说话一样：
通过换行分段来组织内容。
用顿号、逗号、句号等中文标点自然断句。
关键信息直接融入句子里，可以使用特定可观察但是不影响观感的符号标记
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
        chat_model_kwargs={"extra_body": {"enable_search": True}},
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
