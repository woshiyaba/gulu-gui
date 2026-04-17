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
