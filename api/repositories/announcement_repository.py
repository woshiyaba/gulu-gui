"""公告相关数据：点赞数存于 sys_dict（dict_type=announcement, code=like_count，label 为计数）。"""

from db.connection import get_pool

ANNOUNCEMENT_DICT_TYPE = "announcement"
ANNOUNCEMENT_LIKE_CODE = "like_count"


def _parse_like_label(label: str | None) -> int:
    raw = (label or "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


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
