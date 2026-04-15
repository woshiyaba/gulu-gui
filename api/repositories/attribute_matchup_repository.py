from db.connection import get_pool


async def list_attr_axis_order() -> list[str]:
    """按 sort_order 返回表头属性名列表。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name AS attr_name FROM attribute ORDER BY sort_order ASC",
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
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            placeholders = ", ".join(["%s"] * len(defenders))
            await cur.execute(
                f"""
                SELECT da.name AS defender_attr, aa.name AS attacker_attr, am.multiplier
                FROM attribute_matchup am
                JOIN attribute da ON da.id = am.defender_attr_id
                JOIN attribute aa ON aa.id = am.attacker_attr_id
                WHERE da.name IN ({placeholders})
                """,
                defenders,
            )
            return await cur.fetchall()


async def list_matchups_for_attackers(attackers: list[str]) -> list[dict]:
    """
    查询若干进攻属性在矩阵中的全部行（attacker × defender）。
    用于计算精灵进攻侧克制关系。
    """
    if not attackers:
        return []

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            placeholders = ", ".join(["%s"] * len(attackers))
            await cur.execute(
                f"""
                SELECT da.name AS defender_attr, aa.name AS attacker_attr, am.multiplier
                FROM attribute_matchup am
                JOIN attribute da ON da.id = am.defender_attr_id
                JOIN attribute aa ON aa.id = am.attacker_attr_id
                WHERE aa.name IN ({placeholders})
                """,
                attackers,
            )
            return await cur.fetchall()
