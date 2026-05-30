"""WebSocket 路由 —— 客户端连接入口"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws.ws_manager import manager
from ws.handlers.qq_agent_handler import handle_qq_message
from ws.handlers.pet_chat_handler import PET_CHAT_NODE, PetChatSession

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


@router.websocket("/ws/pet-chat/{user_id}/{pet_id}")
async def pet_chat_endpoint(websocket: WebSocket, user_id: str, pet_id: str):
    """宠物对话 WebSocket：每个"用户 × 宠物"一条连接。

    建立连接时合并宠物人设 + 用户补充创建专属 agent；之后每条文本消息
    都交给该 agent 流式回复，token 通过 ws 推回。
    """
    session = PetChatSession(user_id, pet_id)
    await manager.connect(user_id=session.key, websocket=websocket)
    try:
        if not await session.prepare():
            await manager.send_json(
                session.key,
                {"node": PET_CHAT_NODE, "status": "error", "message": "这只宠物还不能聊天哦～"},
            )
            return
        while True:
            message = await websocket.receive_text()
            await session.handle_message(message)
    except WebSocketDisconnect:
        pass
    finally:
        await session.persist()
        manager.disconnect(session.key, websocket)
