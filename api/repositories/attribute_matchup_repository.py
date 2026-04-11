from db.connection import get_pool


async def list_attr_axis_order() -> list[str]:
    """按 sort_order 返回表头属性名列表。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT attr_name FROM attribute_axis ORDER BY sort_order ASC",
            )
            rows = await cur.fetchall()
            return [r["attr_name"] for r in rows]


async def list_matchups_for_defenders(defenders: list[str]) -> list[dict]:
    """
    查询若干防守属性在单方矩阵中的全部行（defender × attacker）。
    defenders 建议已去重且顺序稳定。
    """
    if not defenders:
        return []

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            placeholders = ", ".join(["%s"] * len(defenders))
            await cur.execute(
                f"""
                SELECT defender_attr, attacker_attr, multiplier
                FROM attribute_matchup
                WHERE defender_attr IN ({placeholders})
                """,
                defenders,
            )
            return await cur.fetchall()
