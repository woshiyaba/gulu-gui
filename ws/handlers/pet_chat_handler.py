"""宠物对话 WebSocket handler。

每一个"用户 × 宠物"维持一条独立的聊天 WebSocket。建立连接时：
  1. 查询宠物人设 + 用户个性化补充，合并成 system prompt 并创建专属 agent；
  2. 从库里加载历史对话，回放给前端展示，并写入 agent 上下文（保持记忆连续）。
之后每条消息都通过该 agent 流式回复；连接断开时把本次会话新增的消息落库。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.chat_agent import create_pet_chat_agent
from api.services.pet_chat_service import (
    build_pet_system_prompt,
    load_pet_history,
    save_pet_history,
)
from common.utils.writer import stream_agent_collect
from ws.ws_manager import manager

logger = logging.getLogger(__name__)

# 推送给前端的节点名，前端按此路由宠物对话事件
PET_CHAT_NODE = "pet-chat"

# 加载历史并写入 agent 上下文的最大条数，避免上下文过长
HISTORY_LIMIT = 50


def session_key(user_id: str, pet_id: str) -> str:
    """同一条宠物对话连接的注册键，保证多只宠物的流式推送互不串台。"""
    return f"{PET_CHAT_NODE}:{user_id}:{pet_id}"


def build_thread_id(user_id: str, pet_id: str) -> str:
    """会话的 thread_id，按"宠物 × 用户"固定，保证同一会话上下文连续。"""
    return f"thread-{pet_id}-{user_id}"


def extract_user_text(message: str) -> str:
    """从前端消息里取出用户文本，兼容纯文本与 {"content": "..."} JSON。"""
    message = (message or "").strip()
    if not message:
        return ""
    try:
        data = json.loads(message)
    except (json.JSONDecodeError, ValueError):
        return message
    if isinstance(data, dict):
        for key in ("content", "message", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    return message


class PetChatSession:
    """封装一条宠物对话的生命周期：人设构建、历史加载、消息处理、落库。"""

    def __init__(self, user_id: str, pet_id: str):
        self.user_id = user_id
        self.pet_id = pet_id
        self.key = session_key(user_id, pet_id)
        self.thread_id = build_thread_id(user_id, pet_id)
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self._agent: Any | None = None
        # 本次会话新增的消息，断开时落库；不含已加载的历史，避免重复入库
        self._pending: list[dict[str, str]] = []

    async def prepare(self) -> bool:
        """构建 system prompt 创建 agent，并加载历史对话。宠物没人设时返回 False。"""
        system_prompt = await build_pet_system_prompt(self.user_id, self.pet_id)
        if not system_prompt:
            return False
        self._agent = create_pet_chat_agent(system_prompt, name=f"pet-{self.pet_id}")
        await self._load_history()
        return True

    async def _load_history(self) -> None:
        """加载历史消息：回放给前端，并写入 agent 上下文。"""
        history = await load_pet_history(self.user_id, self.pet_id, limit=HISTORY_LIMIT)
        # 先把历史回放给前端展示
        await manager.send_json(
            self.key,
            {"node": PET_CHAT_NODE, "status": "history", "messages": history},
        )
        if not history:
            return
        # 把历史写入 agent 的 checkpointer，让后续对话带上下文
        seed = [{"role": m["role"], "content": m["content"]} for m in history]
        self._agent.update_state(self.config, {"messages": seed})

    async def handle_message(self, raw_message: str) -> None:
        """处理一条用户消息：流式调用 agent 并把回复推回前端，同时缓存待落库消息。"""
        if self._agent is None:
            return
        text = extract_user_text(raw_message)
        if not text:
            return

        try:
            reply = await stream_agent_collect(
                self._agent,
                text,
                thread_id=self.thread_id,
                node_name=PET_CHAT_NODE,
                user_id=self.key,
            )
        except Exception:
            logger.exception("[pet-chat] 宠物 %s 对话处理失败", self.pet_id)
            await manager.send_json(
                self.key,
                {"node": PET_CHAT_NODE, "status": "error", "message": "宠物有点累了，待会儿再聊吧～"},
            )
            return

        self._pending.append({"role": "user", "content": text})
        if reply:
            self._pending.append({"role": "assistant", "content": reply})

    async def persist(self) -> None:
        """连接断开时把本次会话新增的消息落库。"""
        if not self._pending:
            return
        try:
            await save_pet_history(self.user_id, self.pet_id, self._pending)
        except Exception:
            logger.exception("[pet-chat] 宠物 %s 历史落库失败", self.pet_id)
        finally:
            self._pending.clear()
