"""用户反馈数据访问。

反馈存于 user_feedback 表，按时间倒序供后台查看，可按状态过滤。
建表语句见 sql/user_feedback.sql（不随应用自动执行，需手动建表）。
"""

from db.connection import get_pool

_COLUMNS = "id, user_id, content, contact, feedback_type, status, created_at, updated_at"


async def create_feedback(
    user_id: int | None,
    content: str,
    contact: str | None,
    feedback_type: str | None,
) -> dict:
    """新增一条反馈，返回完整记录。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO user_feedback (user_id, content, contact, feedback_type)
                VALUES (%s, %s, %s, %s)
                RETURNING {_COLUMNS}
                """,
                (user_id, content, contact, feedback_type),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def list_feedback(status: str | None, limit: int, offset: int) -> tuple[int, list[dict]]:
    """分页查询反馈，按时间倒序；可按状态过滤。返回 (总数, 当前页记录)。"""
    where = ""
    params: list = []
    if status:
        where = "WHERE status = %s"
        params.append(status)

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS total FROM user_feedback {where}", params)
            total = (await cur.fetchone())["total"]

            await cur.execute(
                f"""
                SELECT {_COLUMNS}
                FROM user_feedback
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            rows = await cur.fetchall()
    return total, rows


async def update_status(feedback_id: int, status: str) -> dict | None:
    """更新处理状态，返回更新后的记录；不存在时返回 None。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                UPDATE user_feedback
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING {_COLUMNS}
                """,
                (status, feedback_id),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row
