from db.connection import get_pool


POKEMON_FILTER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pokemon_filter_option (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    filter_type VARCHAR(20) NOT NULL,
    order_by VARCHAR(20) NOT NULL DEFAULT '',
    order_dir VARCHAR(10) NOT NULL DEFAULT '',
    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


# (code, label, filter_type, order_by, order_dir, sort_order)
_DEFAULT_FILTER_OPTIONS: list[tuple[str, str, str, str, str, int]] = [
    ("yise", "异色精灵", "shiny", "", "", 10),
    ("total_desc", "总种族值降序", "sort", "total_stats", "desc", 20),
    ("total_asc", "总种族值升序", "sort", "total_stats", "asc", 21),
    ("hp_desc", "体力降序", "sort", "hp", "desc", 30),
    ("hp_asc", "体力升序", "sort", "hp", "asc", 31),
    ("atk_desc", "攻击降序", "sort", "atk", "desc", 40),
    ("atk_asc", "攻击升序", "sort", "atk", "asc", 41),
    ("matk_desc", "魔攻降序", "sort", "matk", "desc", 50),
    ("matk_asc", "魔攻升序", "sort", "matk", "asc", 51),
    ("def_desc", "防御降序", "sort", "def_val", "desc", 60),
    ("def_asc", "防御升序", "sort", "def_val", "asc", 61),
    ("mdef_desc", "魔抗降序", "sort", "mdef", "desc", 70),
    ("mdef_asc", "魔抗升序", "sort", "mdef", "asc", 71),
    ("spd_desc", "速度降序", "sort", "spd", "desc", 80),
    ("spd_asc", "速度升序", "sort", "spd", "asc", 81),
]


async def ensure_pokemon_filter_table() -> None:
    """初始化 pokemon_filter_option 表，并在表为空时灌入默认筛选项。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(POKEMON_FILTER_TABLE_SQL)
            await cur.execute("SELECT COUNT(*) AS cnt FROM pokemon_filter_option")
            row = await cur.fetchone() or {}
            if int(row.get("cnt", 0)) == 0:
                for option in _DEFAULT_FILTER_OPTIONS:
                    await cur.execute(
                        """
                        INSERT INTO pokemon_filter_option
                            (code, label, filter_type, order_by, order_dir, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (code) DO NOTHING
                        """,
                        option,
                    )
        await conn.commit()


async def list_active_filter_options() -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, code, label, filter_type, order_by, order_dir, sort_order
                FROM pokemon_filter_option
                WHERE is_active = TRUE
                ORDER BY sort_order, id
                """
            )
            return await cur.fetchall()


async def get_filter_options_by_codes(codes: list[str]) -> list[dict]:
    if not codes:
        return []
    pool = await get_pool()
    placeholders = ", ".join(["%s"] * len(codes))
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id, code, label, filter_type, order_by, order_dir, sort_order
                FROM pokemon_filter_option
                WHERE is_active = TRUE AND code IN ({placeholders})
                ORDER BY sort_order, id
                """,
                codes,
            )
            return await cur.fetchall()


_OPS_SELECT_COLUMNS = (
    "id, code, label, filter_type, order_by, order_dir, sort_order, is_active"
)


async def list_filter_options_for_ops(
    keyword: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list = []
    kw = keyword.strip()
    if kw:
        conditions.append("(code ILIKE %s OR label ILIKE %s)")
        params.extend([f"%{kw}%", f"%{kw}%"])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS cnt FROM pokemon_filter_option {where_clause}",
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT {_OPS_SELECT_COLUMNS}
                FROM pokemon_filter_option
                {where_clause}
                ORDER BY sort_order, id
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            return total, await cur.fetchall()


async def get_filter_option_by_id(option_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {_OPS_SELECT_COLUMNS} FROM pokemon_filter_option WHERE id = %s",
                (option_id,),
            )
            return await cur.fetchone()


async def get_filter_option_by_code(code: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {_OPS_SELECT_COLUMNS} FROM pokemon_filter_option WHERE code = %s",
                (code,),
            )
            return await cur.fetchone()


async def create_filter_option(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO pokemon_filter_option
                    (code, label, filter_type, order_by, order_dir, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING {_OPS_SELECT_COLUMNS}
                """,
                (
                    payload["code"],
                    payload["label"],
                    payload["filter_type"],
                    payload.get("order_by", ""),
                    payload.get("order_dir", ""),
                    payload.get("sort_order", 0),
                    payload.get("is_active", True),
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update_filter_option(option_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                UPDATE pokemon_filter_option
                SET code = %s,
                    label = %s,
                    filter_type = %s,
                    order_by = %s,
                    order_dir = %s,
                    sort_order = %s,
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING {_OPS_SELECT_COLUMNS}
                """,
                (
                    payload["code"],
                    payload["label"],
                    payload["filter_type"],
                    payload.get("order_by", ""),
                    payload.get("order_dir", ""),
                    payload.get("sort_order", 0),
                    payload.get("is_active", True),
                    option_id,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_filter_option(option_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM pokemon_filter_option WHERE id = %s",
                (option_id,),
            )
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted
