"""用户私聊 WebSocket 消息处理。

前端在 /ws/{user_id} 上发送形如 {"type":"chat","to":<id>,"content":".."} 的帧，
转交统一入口 message_service.send_message 落库 + 实时下发给接收方。
其它类型的帧暂时忽略。
"""

from __future__ import annotations

import json
import logging

from api.services import message_service

logger = logging.getLogger(__name__)


async def handle_user_ws_message(user_id: str, raw: str) -> None:
    """处理一条来自 /ws/{user_id} 的文本帧。"""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(data, dict):
        return

    if data.get("type") != "chat":
        return

    to = data.get("to")
    content = (data.get("content") or "").strip()
    if to is None or not content:
        return

    try:
        from_user_id = int(user_id)
        to_user_id = int(to)
    except (TypeError, ValueError):
        return

    await message_service.send_message(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        content=content,
    )
