"""用户消息仓储 —— user_message 读写（私聊 / 通用通知）。

建表语句见 sql/change_egg.sql，本模块在 ensure_message_tables() 内
用 CREATE TABLE IF NOT EXISTS 自动建表，并负责查询与写入。
"""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_pool


USER_MESSAGE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_message (
    id           BIGSERIAL    PRIMARY KEY,
    from_user_id BIGINT       NOT NULL,
    to_user_id   BIGINT       NOT NULL,
    msg_type     VARCHAR(20)  NOT NULL DEFAULT 'chat',
    content      TEXT         NOT NULL DEFAULT '',
    payload      JSONB,
    is_delivered BOOLEAN      NOT NULL DEFAULT FALSE,
    delivered_at TIMESTAMP,
    is_read      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_um_pending ON user_message (to_user_id, is_delivered);
CREATE INDEX IF NOT EXISTS idx_um_conv    ON user_message (from_user_id, to_user_id, id);
"""

_RETURN_COLS = (
    "id, from_user_id, to_user_id, msg_type, content, payload, "
    "is_delivered, delivered_at, is_read, created_at"
)


async def ensure_message_tables() -> None:
    """确保 user_message 表存在。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(USER_MESSAGE_TABLE_SQL)
        await conn.commit()


async def insert_message(
    from_user_id: int,
    to_user_id: int,
    content: str,
    msg_type: str = "chat",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """落库一条消息，返回完整记录。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO user_message (from_user_id, to_user_id, msg_type, content, payload)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING {_RETURN_COLS}
                """,
                (
                    from_user_id,
                    to_user_id,
                    msg_type,
                    content,
                    json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row


async def list_undelivered(to_user_id: int) -> list[dict[str, Any]]:
    """按时间正序返回某用户所有未投递消息。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT {_RETURN_COLS}
                FROM user_message
                WHERE to_user_id = %s AND is_delivered = FALSE
                ORDER BY id ASC
                """,
                (to_user_id,),
            )
            return await cur.fetchall()


async def mark_delivered(ids: list[int]) -> None:
    """批量标记消息为已投递。"""
    if not ids:
        return
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_message
                SET is_delivered = TRUE, delivered_at = NOW()
                WHERE id = ANY(%s)
                """,
                (ids,),
            )
        await conn.commit()


async def list_conversation(
    user_a: int,
    user_b: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """按时间正序返回 user_a 与 user_b 之间最近 limit 条消息（双向）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT {_RETURN_COLS}
                FROM (
                    SELECT {_RETURN_COLS}
                    FROM user_message
                    WHERE (from_user_id = %s AND to_user_id = %s)
                       OR (from_user_id = %s AND to_user_id = %s)
                    ORDER BY id DESC
                    LIMIT %s
                ) AS recent
                ORDER BY id ASC
                """,
                (user_a, user_b, user_b, user_a, limit),
            )
            return await cur.fetchall()


async def list_inbox(to_user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """按时间倒序返回某用户收到的最近 limit 条消息（含通知）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT {_RETURN_COLS}
                FROM user_message
                WHERE to_user_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (to_user_id, limit),
            )
            return await cur.fetchall()


async def count_unread(to_user_id: int) -> int:
    """统计某用户未读消息数。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS cnt FROM user_message WHERE to_user_id = %s AND is_read = FALSE",
                (to_user_id,),
            )
            row = await cur.fetchone() or {}
    return int(row.get("cnt", 0))


async def mark_read(to_user_id: int, ids: list[int]) -> None:
    """把某用户收到的指定消息标记为已读。"""
    if not ids:
        return
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE user_message
                SET is_read = TRUE
                WHERE to_user_id = %s AND id = ANY(%s)
                """,
                (to_user_id, ids),
            )
        await conn.commit()
