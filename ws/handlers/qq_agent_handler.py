"""QQ 群消息 → Agent 处理 → 回复消息的 handler。

当群消息 @BOT_QQ 时，提取文本内容交给 main_agent 处理，
然后构造 send_group_msg 格式通过 ws send_json 发回。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from ws.ws_manager import manager

logger = logging.getLogger(__name__)

BOT_QQ = "3766543953"

# 懒加载 agent，避免模块导入时就初始化（耗时且占内存）
_agent = None
_agent_lock = asyncio.Lock()


async def _get_agent():
    global _agent
    if _agent is None:
        async with _agent_lock:
            if _agent is None:
                from agents.main_agent import create_main_agent
                _agent = create_main_agent()
    return _agent


def _is_at_bot(message_data: dict) -> bool:
    """判断消息中是否 @了 BOT_QQ。"""
    messages: list[dict] = message_data.get("message", [])
    return any(
        seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == BOT_QQ
        for seg in messages
    )


def _extract_text(message_data: dict) -> str:
    """从消息段中提取纯文本内容（去除 at 段）。"""
    messages: list[dict] = message_data.get("message", [])
    parts = []
    for seg in messages:
        if seg.get("type") == "text":
            parts.append(seg["data"].get("text", ""))
    return "".join(parts).strip()


def _extract_reply(result: dict) -> str:
    """从 agent 返回结果中提取最后一条 AI 回复文本。"""
    logger.info("[_extract_reply] 收到 %s 的提问", result)

    messages = result.get("messages", [])
    if not messages:
        return ""
    return messages[-1].content or ""


def _build_reply(group_id: int, text: str) -> dict[str, Any]:
    """构造 send_group_msg 的 JSON 格式。"""
    return {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": text,
        },
    }


async def handle_qq_message(data: dict) -> None:
    """处理一条 QQ 消息。如果是群消息且 @BOT，则调用 agent 并回复。

    Args:
        data: 从 WebSocket 收到的完整 QQ 消息 JSON。
    """
    # 只处理群消息
    if data.get("post_type") != "message" or data.get("message_type") != "group":
        return

    if not _is_at_bot(data):
        return

    user_text = _extract_text(data)
    if not user_text:
        return

    group_id = data.get("group_id")
    sender = data.get("sender", {})
    nickname = sender.get("card") or sender.get("nickname", "")
    logger.info("[qq-agent] 收到 %s 的提问: %s (群 %s)", nickname, user_text, group_id)

    try:
        agent = await _get_agent()
        thread_id = uuid4().hex
        config = {"configurable": {"thread_id": thread_id}}

        # agent.invoke 是同步阻塞调用，放到线程池中避免阻塞事件循环
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [{"role": "user", "content": user_text}]},
            config,
        )

        reply_text = _extract_reply(result)
        if not reply_text:
            reply_text = "抱歉，我暂时无法回答这个问题。"
    except Exception:
        logger.exception("[qq-agent] agent 调用失败")
        reply_text = "处理消息时出错了，请稍后再试。"

    reply_msg = _build_reply(group_id, reply_text)
    await manager.send_json("napcat-qq", reply_msg)
    logger.info("[qq-agent] 已回复群 %s: %s", group_id, reply_text[:50])
