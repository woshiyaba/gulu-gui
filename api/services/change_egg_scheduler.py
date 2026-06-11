"""换蛋广场定时匹配调度器（APScheduler）。

在 api/main.py 的 lifespan 内 start_scheduler() / stop_scheduler()。
周期性调用 change_egg_service.run_match_all_open 做全量扫描匹配。
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.services.change_egg_service import run_match_all_open

logger = logging.getLogger(__name__)

# 匹配扫描间隔（分钟），可用环境变量覆盖
MATCH_INTERVAL_MINUTES = int(os.getenv("CHANGE_EGG_MATCH_INTERVAL_MINUTES", "2"))

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    """启动调度器并注册换蛋匹配任务。"""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_match_all_open,
        "interval",
        minutes=MATCH_INTERVAL_MINUTES,
        id="change_egg_match",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("[change_egg] 定时匹配调度器已启动，间隔 %d 分钟", MATCH_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    """停止调度器。"""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("[change_egg] 定时匹配调度器已停止")
