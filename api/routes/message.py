"""用户私聊消息接口（REST 兜底）。

实时发送走 WebSocket（/ws/{user_id}），这里提供 REST 发送 / 拉历史 / 标记已读，
便于小程序调用与离线落库。发送统一走 message_service.send_message。
"""

from fastapi import APIRouter, Query

from api.repositories import message_repository
from api.schemas.message import MessageReadRequest, MessageSendRequest, UserMessage
from api.services import message_service

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=UserMessage)
async def send_message(payload: MessageSendRequest):
    """发送一条私聊消息：落库，接收方在线则实时 ws 下发。"""
    return await message_service.send_message(
        from_user_id=payload.from_user_id,
        to_user_id=payload.to_user_id,
        content=payload.content,
    )


@router.get("/inbox", response_model=list[UserMessage])
async def get_inbox(
    user_id: int = Query(..., description="接收方用户 id"),
    limit: int = Query(50, ge=1, le=200, description="最多返回条数"),
):
    """拉取某用户收到的消息 / 通知（按时间倒序）。"""
    return await message_repository.list_inbox(user_id, limit)


@router.get("/unread-count")
async def get_unread_count(user_id: int = Query(..., description="接收方用户 id")):
    """某用户未读消息数（用于红点提醒）。"""
    return {"count": await message_repository.count_unread(user_id)}


@router.get("/conversation", response_model=list[UserMessage])
async def get_conversation(
    user_a: int = Query(..., description="用户 A id"),
    user_b: int = Query(..., description="用户 B id"),
    limit: int = Query(50, ge=1, le=200, description="最多返回条数"),
):
    """拉取 user_a 与 user_b 之间的历史消息（按时间正序）。"""
    return await message_repository.list_conversation(user_a, user_b, limit)


@router.post("/read")
async def mark_read(payload: MessageReadRequest):
    """标记某用户收到的若干消息为已读。"""
    await message_repository.mark_read(payload.to_user_id, payload.ids)
    return {"ok": True}
