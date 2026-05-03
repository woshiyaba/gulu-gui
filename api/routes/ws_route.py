"""WebSocket 路由 —— 客户端连接入口"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws.ws_manager import manager
from ws.handlers.qq_agent_handler import handle_qq_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket=websocket)
    try:
        while True:
            message = await websocket.receive_text()
            logger.info("[ws] 收到消息: %s", message[:200])
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue
            await handle_qq_message(data)
    except WebSocketDisconnect:
        manager.disconnect("napcat-qq", websocket)


@router.websocket("/ws/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: str):
    """前端用户 WebSocket：以 user_id 为键注册连接，接收后端流式事件。

    前端目前只读不写；保持 receive 循环以维护连接，收到的内容暂时忽略。
    """
    await manager.connect(user_id=user_id, websocket=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
