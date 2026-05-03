"""AI PK 任务仓储 —— PostgreSQL 持久化"""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_pool


AI_PK_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS ai_pk_task (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(128) NOT NULL,
    team_a JSONB NOT NULL,
    team_b JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    result JSONB,
    raw TEXT,
    error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_pk_task_user ON ai_pk_task(user_id, created_at DESC);
"""


async def ensure_ai_pk_tables() -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(AI_PK_TABLES_SQL)
        await conn.commit()


async def create_task(task_id: str, user_id: str, team_a: dict, team_b: dict) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ai_pk_task (task_id, user_id, team_a, team_b, status)
                VALUES (%s, %s, %s::jsonb, %s::jsonb, 'pending')
                """,
                (
                    task_id,
                    user_id,
                    json.dumps(team_a, ensure_ascii=False),
                    json.dumps(team_b, ensure_ascii=False),
                ),
            )
        await conn.commit()


async def mark_running(task_id: str) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE ai_pk_task SET status='running', updated_at=NOW() WHERE task_id=%s",
                (task_id,),
            )
        await conn.commit()


async def complete_task(task_id: str, result: dict, raw: str | None = None) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE ai_pk_task
                SET status='completed',
                    result=%s::jsonb,
                    raw=%s,
                    updated_at=NOW()
                WHERE task_id=%s
                """,
                (json.dumps(result, ensure_ascii=False), raw, task_id),
            )
        await conn.commit()


async def fail_task(task_id: str, error: str) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE ai_pk_task
                SET status='failed',
                    error=%s,
                    updated_at=NOW()
                WHERE task_id=%s
                """,
                (error, task_id),
            )
        await conn.commit()


async def get_task(task_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT task_id, user_id, team_a, team_b, status, result, raw, error,
                       created_at, updated_at
                FROM ai_pk_task
                WHERE task_id=%s
                """,
                (task_id,),
            )
            return await cur.fetchone()
