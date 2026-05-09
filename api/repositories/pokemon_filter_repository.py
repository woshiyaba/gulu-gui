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
