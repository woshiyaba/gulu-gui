"""AI PK 任务服务 —— 提交任务 / 后台流式跑 / 查询结果"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from api.repositories import ai_pk_repository
from ws.ws_manager import manager

logger = logging.getLogger(__name__)


async def ensure_ai_pk_tables() -> None:
    await ai_pk_repository.ensure_ai_pk_tables()


async def submit_battle_task(user_id: str, team_a: dict, team_b: dict) -> str:
    """创建一条 PK 任务，立刻返回 task_id 并在后台启动流式分析。"""
    task_id = uuid4().hex
    await ai_pk_repository.create_task(task_id, user_id, team_a, team_b)
    asyncio.create_task(_run_battle_task(task_id, user_id, team_a, team_b))
    return task_id


async def _run_battle_task(task_id: str, user_id: str, team_a: dict, team_b: dict) -> None:
    """后台任务：调用 stream_analyze_battle 流式跑分析，结束后落库。"""
    from agents.sub.pk_subagent import stream_analyze_battle

    try:
        await ai_pk_repository.mark_running(task_id)
        result, raw = await stream_analyze_battle(
            team_a, team_b, user_id=user_id, task_id=task_id,
        )
        await ai_pk_repository.complete_task(task_id, result, raw=raw)
        # DB 已落库，再向前端推一个 "done" 事件，把结构化结果直接带过去，
        # 前端不必再发 HTTP 拉取，且彻底避开 "stream end → DB 还没写完" 的竞态。
        try:
            await manager.send_json(
                user_id=user_id,
                data={
                    "task_id": task_id,
                    "node": "pk",
                    "status": "done",
                    "result": result,
                },
            )
        except Exception:
            logger.exception("[ai-pk] 任务 %s 推送 done 事件失败", task_id)
    except Exception as exc:
        logger.exception("[ai-pk] 任务 %s 执行失败", task_id)
        try:
            await ai_pk_repository.fail_task(task_id, str(exc))
        except Exception:
            logger.exception("[ai-pk] 任务 %s 标记失败时再次出错", task_id)
        try:
            await manager.send_json(
                user_id=user_id,
                data={
                    "task_id": task_id,
                    "node": "pk",
                    "status": "error",
                    "message": str(exc),
                },
            )
        except Exception:
            logger.exception("[ai-pk] 任务 %s 推送 error 事件失败", task_id)


async def get_task(task_id: str) -> dict | None:
    return await ai_pk_repository.get_task(task_id)
