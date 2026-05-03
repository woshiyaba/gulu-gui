from __future__ import annotations

import asyncio
from typing import Any
from ws.ws_manager import manager


class StreamCollector:
    """流式输出收集器，管理节点生命周期并推送状态事件。

    将"流式推送"与"最终结果收集"分离：
      - push()      → 推送所有 token（含思考过程）到前端
      - push_result / reset_result → 仅追踪 agent 最后一轮 AI 输出

    node_name 非空时获取 stream_writer 并推送 custom 事件（图节点场景）；
    为 None 时仅收集 chunk（独立调用场景）。

    推送的 custom 事件格式：
      - start:      {"node": "xxx", "status": "start"}
      - streaming:  {"node": "xxx", "status": "streaming", "chunk": "..."}
      - end:        {"node": "xxx", "status": "end"}

    若构造时传入 task_id，会一并附加到事件 payload 中，便于前端按任务路由。
    """

    def __init__(
            self,
            user_id: str | None = None,
            node_name: str | None = None,
            task_id: str | None = None,
    ):
        self._node_name = node_name
        self._user_id = user_id
        self._task_id = task_id
        self._chunks: list[str] = []
        self._result: str | None = None
        self._manager = manager

    def _payload(self, **extra: Any) -> dict[str, Any]:
        data: dict[str, Any] = {"node": self._node_name, **extra}
        if self._task_id is not None:
            data["task_id"] = self._task_id
        return data

    async def start(self):
        """推送节点开始事件，应在流式输出前调用。"""
        if self._manager and self._user_id:
            await self._manager.send_json(user_id=self._user_id, data=self._payload(status="start"))

    async def push(self, content: str):
        if not content:
            return
        self._chunks.append(content)
        if self._manager and self._user_id:
            await self._manager.send_json(
                user_id=self._user_id,
                data=self._payload(status="streaming", chunk=content),
            )

    async def finish(self):
        """推送节点结束事件，应在流式输出完成后调用。"""
        if self._manager and self._user_id:
            await self._manager.send_json(user_id=self._user_id, data=self._payload(status="end"))

    async def push_error(self, message: str):
        """推送错误事件，供失败兜底使用。"""
        if self._manager and self._user_id:
            await self._manager.send_json(
                user_id=self._user_id,
                data=self._payload(status="error", message=message),
            )

    def set_result(self, content: str):
        """记录 updates 中提取的最终 AI 输出，每次覆盖写入以保留最新一轮。"""
        self._result = content

    @property
    def result(self) -> str:
        """优先返回 updates 提取的最终结果，兜底返回流式 token 拼接。"""
        if self._result is not None:
            return self._result
        return "".join(self._chunks)


def _extract_final_content(chunk) -> str | None:
    """从 updates 事件的 data 中提取最终 AIMessage.content。

    遍历 data 各节点的 messages 列表，找最后一条满足条件的 AI 消息：
      - type == "ai"
      - content 非空
      - 无 tool_calls（说明是最终输出而非中间调用）
    """
    candidate: str | None = None
    for node_name, data in chunk["data"].items():
        if node_name == "model":
            candidate = data["messages"][-1].content
    return candidate


_STREAM_DONE = object()


async def stream_agent_collect(
        agent: Any,
        content: str,
        thread_id: str,
        node_name: str | None = None,
        user_id: str | None = None,
        task_id: str | None = None,
) -> str:
    """流式调用 agent 并收集完整结果（同步迭代版）。

    `agent.stream(...)` 是同步生成器，并且 agent 内部的工具（如 call_api）也是同步 HTTP，
    若直接在事件循环里 `for chunk in agent.stream(...)`，事件循环会被占住，导致 agent
    自调本服务的 FastAPI 接口时超时。这里把同步迭代放到工作线程，通过 asyncio.Queue
    把 chunk 喂回主协程，再推 WS / 收集结果，事件循环始终保持空闲。
    """
    sc = StreamCollector(user_id=user_id, node_name=node_name, task_id=task_id)
    await sc.start()

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def producer() -> None:
        try:
            for chunk in agent.stream(
                    {"messages": [{"role": "user", "content": content}]},
                    config={"configurable": {"thread_id": thread_id}},
                    stream_mode=["messages", "updates"],
                    subgraphs=True,
                    version="v2",
            ):
                asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
        except BaseException as exc:
            asyncio.run_coroutine_threadsafe(queue.put(exc), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(_STREAM_DONE), loop)

    producer_task = asyncio.create_task(asyncio.to_thread(producer))

    try:
        while True:
            chunk = await queue.get()
            if chunk is _STREAM_DONE:
                break
            if isinstance(chunk, BaseException):
                raise chunk
            if chunk["type"] == "messages":
                token, _metadata = chunk["data"]
                await sc.push(token.content)
            elif chunk["type"] == "updates":
                final = _extract_final_content(chunk)
                if final:
                    sc.set_result(final)
        await producer_task
    finally:
        await sc.finish()
    return sc.result


async def astream_agent_collect(
        agent: Any,
        content: str,
        thread_id: str,
        node_name: str | None = None,
        user_id: str | None = None,
        task_id: str | None = None,
) -> str:
    """流式调用 agent 并收集完整结果（异步版）。"""
    sc = StreamCollector(user_id=user_id, node_name=node_name, task_id=task_id)
    await sc.start()
    try:
        async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": content}]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode=["messages", "updates"],
                subgraphs=True,
                version="v2",
        ):
            if chunk["type"] == "messages":
                token, _metadata = chunk["data"]
                await sc.push(token.content)
            elif chunk["type"] == "updates":
                final = _extract_final_content(chunk)
                if final:
                    sc.set_result(final)
    finally:
        await sc.finish()
    return sc.result


async def agent_collect(
        agent: Any,
        content: str,
        thread_id: str,
        node_name: str | None = None,
        user_id: str | None = None,
        task_id: str | None = None,
) -> str:
    """先 invoke 一次再走异步流式收集（备用调用模式）。"""
    agent.invoke(
        {"messages": [{"role": "user", "content": content}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    sc = StreamCollector(user_id=user_id, node_name=node_name, task_id=task_id)
    await sc.start()
    try:
        async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": content}]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode=["messages", "updates"],
                subgraphs=True,
                version="v2",
        ):
            if chunk["type"] == "messages":
                token, _metadata = chunk["data"]
                await sc.push(token.content)
            elif chunk["type"] == "updates":
                final = _extract_final_content(chunk)
                if final:
                    sc.set_result(final)
    finally:
        await sc.finish()
    return sc.result
