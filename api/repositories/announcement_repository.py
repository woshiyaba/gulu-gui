"""公告相关数据访问。

- 公告正文存于 site_announcement 表（单条配置行）。
- 点赞数存于 sys_dict（dict_type=announcement, code=like_count，label 为计数）。
"""

from db.connection import get_pool

ANNOUNCEMENT_DICT_TYPE = "announcement"
ANNOUNCEMENT_LIKE_CODE = "like_count"


ANNOUNCEMENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS site_announcement (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def _parse_like_label(label: str | None) -> int:
    raw = (label or "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


async def ensure_announcement_table() -> None:
    """初始化 site_announcement 表，并保证存在唯一的配置行（id=1）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(ANNOUNCEMENT_TABLE_SQL)
            await cur.execute("SELECT COUNT(*) AS cnt FROM site_announcement")
            row = await cur.fetchone() or {}
            if int(row.get("cnt", 0)) == 0:
                await cur.execute(
                    "INSERT INTO site_announcement (title, content, is_active) VALUES ('', '', FALSE)"
                )
        await conn.commit()


async def get_announcement() -> dict | None:
    """读取唯一一条公告配置。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, title, content, is_active, updated_at
                FROM site_announcement
                ORDER BY id
                LIMIT 1
                """
            )
            return await cur.fetchone()


async def get_active_announcement() -> dict | None:
    """读取启用且有内容的公告，供前台展示；否则返回 None。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT title, content, updated_at
                FROM site_announcement
                WHERE is_active = TRUE
                  AND (title <> '' OR content <> '')
                ORDER BY id
                LIMIT 1
                """
            )
            return await cur.fetchone()


async def update_announcement(payload: dict) -> dict | None:
    """更新唯一一条公告配置，自动刷新 updated_at。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE site_announcement
                SET title = %s, content = %s, is_active = %s, updated_at = NOW()
                WHERE id = (SELECT id FROM site_announcement ORDER BY id LIMIT 1)
                RETURNING id, title, content, is_active, updated_at
                """,
                (
                    payload["title"],
                    payload["content"],
                    payload["is_active"],
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def ensure_announcement_like_dict() -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sys_dict (dict_type, code, label, extra, sort_order)
                VALUES (%s, %s, '0', '', 0)
                ON CONFLICT (dict_type, code) DO NOTHING
                """,
                (ANNOUNCEMENT_DICT_TYPE, ANNOUNCEMENT_LIKE_CODE),
            )
        await conn.commit()


async def get_announcement_like_count() -> int:
    await ensure_announcement_like_dict()
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT label
                FROM sys_dict
                WHERE dict_type = %s AND code = %s
                """,
                (ANNOUNCEMENT_DICT_TYPE, ANNOUNCEMENT_LIKE_CODE),
            )
            row = await cur.fetchone()
            if not row:
                return 0
            return _parse_like_label(row.get("label"))


async def increment_announcement_like_count() -> int:
    await ensure_announcement_like_dict()
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE sys_dict
                SET label = (
                    COALESCE(NULLIF(TRIM(label), ''), '0')::bigint + 1
                )::varchar
                WHERE dict_type = %s AND code = %s
                RETURNING label
                """,
                (ANNOUNCEMENT_DICT_TYPE, ANNOUNCEMENT_LIKE_CODE),
            )
            row = await cur.fetchone()
        await conn.commit()
    if not row:
        return 0
    return _parse_like_label(row.get("label"))
