from db.connection import get_pool

STAT_COLS = (
    "hp_mod_pct",
    "phy_atk_mod_pct",
    "mag_atk_mod_pct",
    "phy_def_mod_pct",
    "mag_def_mod_pct",
    "spd_mod_pct",
)
STAT_KEY_TO_COL = {
    "hp": "hp_mod_pct",
    "phy_atk": "phy_atk_mod_pct",
    "mag_atk": "mag_atk_mod_pct",
    "phy_def": "phy_def_mod_pct",
    "mag_def": "mag_def_mod_pct",
    "spd": "spd_mod_pct",
}
SELECT_COLS = "id, name, " + ", ".join(STAT_COLS)


def _col(stat_key: str) -> str | None:
    return STAT_KEY_TO_COL.get(stat_key)


async def list_personalities(
    keyword: str = "",
    buff_stat: str = "",
    nerf_stat: str = "",
    page: int = 1,
    page_size: int = 100,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    conditions: list[str] = []
    params: list = []

    kw = (keyword or "").strip()
    if kw:
        conditions.append("name ILIKE %s")
        like = f"%{kw}%"
        params.append(like)

    buff_col = _col(buff_stat)
    if buff_col:
        conditions.append(f"{buff_col} = 0.10")
    nerf_col = _col(nerf_stat)
    if nerf_col:
        conditions.append(f"{nerf_col} = -0.10")

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS cnt FROM personality {where_sql}", params)
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT {SELECT_COLS}
                FROM personality
                {where_sql}
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            items = await cur.fetchall()
            return total, items


async def get_personality_by_id(pid: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {SELECT_COLS} FROM personality WHERE id = %s",
                (pid,),
            )
            return await cur.fetchone()


async def id_exists(pid: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM personality WHERE id = %s", (pid,))
            return (await cur.fetchone()) is not None


async def next_available_id() -> int:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM personality")
            row = await cur.fetchone() or {}
            return int(row.get("max_id", 0)) + 1


async def create_personality(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO personality (id, name, {", ".join(STAT_COLS)})
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {SELECT_COLS}
                """,
                (
                    payload["id"],
                    payload["name"],
                    payload["hp_mod_pct"],
                    payload["phy_atk_mod_pct"],
                    payload["mag_atk_mod_pct"],
                    payload["phy_def_mod_pct"],
                    payload["mag_def_mod_pct"],
                    payload["spd_mod_pct"],
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update_personality(pid: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                UPDATE personality
                SET name = %s,
                    hp_mod_pct = %s, phy_atk_mod_pct = %s, mag_atk_mod_pct = %s,
                    phy_def_mod_pct = %s, mag_def_mod_pct = %s, spd_mod_pct = %s
                WHERE id = %s
                RETURNING {SELECT_COLS}
                """,
                (
                    payload["name"],
                    payload["hp_mod_pct"],
                    payload["phy_atk_mod_pct"],
                    payload["mag_atk_mod_pct"],
                    payload["phy_def_mod_pct"],
                    payload["mag_def_mod_pct"],
                    payload["spd_mod_pct"],
                    pid,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_personality(pid: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM personality WHERE id = %s", (pid,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def bulk_upsert_personalities(rows: list[dict]) -> int:
    """全量重建：TRUNCATE 后批量插入。"""
    if not rows:
        return 0
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM personality")
            values = [
                (
                    r["id"], r["name"],
                    r["hp_mod_pct"], r["phy_atk_mod_pct"], r["mag_atk_mod_pct"],
                    r["phy_def_mod_pct"], r["mag_def_mod_pct"], r["spd_mod_pct"],
                )
                for r in rows
            ]
            await cur.executemany(
                f"""
                INSERT INTO personality (id, name, {", ".join(STAT_COLS)})
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                values,
            )
        await conn.commit()
        return len(rows)
