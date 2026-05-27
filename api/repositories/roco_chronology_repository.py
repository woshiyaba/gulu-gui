"""洛克纪年（大事记）数据访问。

事件存于 roco_chronology 表（建表见 sql/roco_chronology.sql，本模块不负责建表）。
images 列为 JSONB 字符串数组，读出时由 psycopg 自动解析为 Python list。
"""

import json

from db.connection import get_pool

# 前台 / 后台公用的字段列表
_DETAIL_COLUMNS = "id, event_date, title, content, images, sort_order, is_active, created_at, updated_at"


# ── 前台展示 ────────────────────────────────────────────


async def list_published() -> list[dict]:
    """前台时间轴列表：仅启用项，返回时间 + 标题 + id + 封面图，按时间倒序。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, event_date, title,
                       COALESCE(images->>0, '') AS cover_image
                FROM roco_chronology
                WHERE is_active = TRUE
                ORDER BY event_date DESC, sort_order DESC, id DESC
                """
            )
            return await cur.fetchall()


async def get_published_detail(item_id: int) -> dict | None:
    """前台详情：仅启用项，返回图文等完整信息。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, event_date, title, content, images
                FROM roco_chronology
                WHERE id = %s AND is_active = TRUE
                """,
                (item_id,),
            )
            return await cur.fetchone()


# ── 后台维护 ────────────────────────────────────────────


async def list_paginated(keyword: str = "", page: int = 1, page_size: int = 10) -> tuple[int, list[dict]]:
    pool = await get_pool()
    offset = (page - 1) * page_size
    where = ""
    params: list = []
    if keyword:
        where = "WHERE title ILIKE %s"
        params.append(f"%{keyword}%")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS cnt FROM roco_chronology {where}", params)
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT {_DETAIL_COLUMNS}
                FROM roco_chronology
                {where}
                ORDER BY event_date DESC, sort_order DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            items = await cur.fetchall()
            return total, items


async def get_by_id(item_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {_DETAIL_COLUMNS} FROM roco_chronology WHERE id = %s",
                (item_id,),
            )
            return await cur.fetchone()


async def create(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO roco_chronology (event_date, title, content, images, sort_order, is_active)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                RETURNING {_DETAIL_COLUMNS}
                """,
                (
                    payload["event_date"],
                    payload["title"],
                    payload["content"],
                    json.dumps(payload["images"], ensure_ascii=False),
                    payload["sort_order"],
                    payload["is_active"],
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update(item_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                UPDATE roco_chronology
                SET event_date = %s, title = %s, content = %s, images = %s::jsonb,
                    sort_order = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING {_DETAIL_COLUMNS}
                """,
                (
                    payload["event_date"],
                    payload["title"],
                    payload["content"],
                    json.dumps(payload["images"], ensure_ascii=False),
                    payload["sort_order"],
                    payload["is_active"],
                    item_id,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete(item_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM roco_chronology WHERE id = %s", (item_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted
