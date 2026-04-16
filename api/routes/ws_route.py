"""WebSocket 路由 —— 客户端连接入口"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket=websocket)
    try:
        while True:
            message = await websocket.receive_text()
            print(f"[ws] 收到消息: {message}")
            # logger.info("[ws] 收到消息: %s", message)
    except WebSocketDisconnect:
        manager.disconnect("napcat-qq", websocket)
