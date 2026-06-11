"""用户消息业务逻辑 —— 私聊 / 通用通知的统一下发入口。

设计：所有"给某用户下发一条消息/通知"都走 send_message()。
- 先落库；
- 接收方在线（ws 已连接）则通过 WebSocket 实时下发并标记已投递；
- 接收方离线则保留未投递，等其上线时 flush_undelivered() 补发。

换蛋匹配命中通知直接复用 send_message(msg_type='egg_match_notify')。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from api.repositories import message_repository
from ws.ws_manager import manager

logger = logging.getLogger(__name__)

# ws 事件统一节点名，前端按 node 路由
MESSAGE_NODE = "message"


def _to_ws_event(msg: dict[str, Any]) -> dict[str, Any]:
    """把一条消息记录转成下发给前端的 ws 事件结构。"""
    created_at = msg.get("created_at")
    return {
        "node": MESSAGE_NODE,
        "type": msg.get("msg_type", "chat"),
        "id": msg.get("id"),
        "from_user_id": msg.get("from_user_id"),
        "to_user_id": msg.get("to_user_id"),
        "content": msg.get("content", ""),
        "payload": msg.get("payload"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }


def _is_online(user_id: int) -> bool:
    """接收方是否在线：/ws/{user_id} 以 str(user_id) 为键注册连接。"""
    conns = manager.active_connections.get(str(user_id))
    return bool(conns)


async def send_message(
    from_user_id: int,
    to_user_id: int,
    content: str,
    msg_type: str = "chat",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """统一下发入口：落库 → 在线则实时 ws 推送并标记已投递 → 返回消息记录。"""
    msg = await message_repository.insert_message(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        content=content,
        msg_type=msg_type,
        payload=payload,
    )
    if _is_online(to_user_id):
        await manager.send_json(str(to_user_id), _to_ws_event(msg))
        await message_repository.mark_delivered([msg["id"]])
        msg["is_delivered"] = True
    return msg


async def flush_undelivered(user_id: int) -> int:
    """用户上线时调用：把其所有未投递消息逐条 ws 下发并标记已投递，返回补发条数。"""
    pending = await message_repository.list_undelivered(user_id)
    if not pending:
        return 0
    delivered_ids: list[int] = []
    for msg in pending:
        try:
            await manager.send_json(str(user_id), _to_ws_event(msg))
            delivered_ids.append(msg["id"])
        except Exception:
            logger.warning("[message] 补发失败 user_id=%s id=%s", user_id, msg.get("id"), exc_info=True)
    await message_repository.mark_delivered(delivered_ids)
    return len(delivered_ids)
