from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageSendRequest(BaseModel):
    """发送一条私聊消息。"""

    from_user_id: int = Field(..., description="发送方用户 id")
    to_user_id: int = Field(..., description="接收方用户 id")
    content: str = Field(..., min_length=1, description="消息内容")


class MessageReadRequest(BaseModel):
    """标记某用户收到的若干消息为已读。"""

    to_user_id: int = Field(..., description="接收方用户 id")
    ids: list[int] = Field(default_factory=list, description="要标记已读的消息 id 列表")


class UserMessage(BaseModel):
    """一条用户消息。"""

    id: int
    from_user_id: int
    to_user_id: int
    msg_type: str = "chat"
    content: str = ""
    payload: dict[str, Any] | None = None
    is_delivered: bool = False
    delivered_at: datetime | None = None
    is_read: bool = False
    created_at: datetime | None = None
