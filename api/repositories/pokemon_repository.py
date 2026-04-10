from db.connection import get_pool


def _build_filters(name: str = "", attr: str = "") -> tuple[str, list]:
    """构建列表查询的 WHERE 条件与参数。"""
    conditions: list[str] = []
    params: list = []

    if name:
        conditions.append("p.name LIKE %s")
        params.append(f"%{name}%")

    if attr:
        conditions.append(
            "EXISTS (SELECT 1 FROM pokemon_attribute pa2 "
            "WHERE pa2.pokemon_name = p.name AND pa2.attr_name = %s)"
        )
        params.append(attr)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


async def list_attributes() -> list[dict]:
    """查询所有不重复的属性。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT attr_name, attr_image FROM pokemon_attribute ORDER BY attr_name"
            )
            return await cur.fetchall()


async def count_pokemon(name: str = "", attr: str = "") -> int:
    """查询符合条件的精灵总数。"""
    where_clause, params = _build_filters(name=name, attr=attr)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS cnt FROM pokemon p {where_clause}",
                params,
            )
            row = await cur.fetchone() or {}
            return row.get("cnt", 0)


async def list_pokemon(
    name: str = "",
    attr: str = "",
    page: int = 1,
    page_size: int = 30,
) -> list[dict]:
    """分页查询精灵基础信息与属性。"""
    where_clause, params = _build_filters(name=name, attr=attr)
    offset = (page - 1) * page_size

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT
                    p.no, p.name, p.image, p.type, p.type_name, p.form, p.form_name,
                    GROUP_CONCAT(pa.attr_name ORDER BY pa.id SEPARATOR ',') AS attr_names,
                    GROUP_CONCAT(pa.attr_image ORDER BY pa.id SEPARATOR '|||') AS attr_images
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_name = p.name
                {where_clause}
                GROUP BY p.id, p.no, p.name, p.image, p.type, p.type_name, p.form, p.form_name
                ORDER BY p.no, p.id
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            return await cur.fetchall()


async def list_pokemon_by_body_metrics(height_cm: int, weight_g: int) -> list[dict]:
    """按身高和体重区间匹配可命中的宠物名称，跳过首领形态。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT pokemon_name
                FROM egg_hatch_pet
                WHERE is_leader_form = 0
                  AND height_low <= %s
                  AND height_high >= %s
                  AND weight_low <= %s
                  AND weight_high >= %s
                ORDER BY pokemon_name
                """,
                (height_cm, height_cm, weight_g, weight_g),
            )
            return await cur.fetchall()


async def get_pokemon_base(name: str) -> dict | None:
    """查询单只精灵的基础信息与属性。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT p.no, p.name, p.image, p.type, p.type_name, p.form, p.form_name,
                       GROUP_CONCAT(pa.attr_name ORDER BY pa.id SEPARATOR ',') AS attr_names,
                       GROUP_CONCAT(pa.attr_image ORDER BY pa.id SEPARATOR '|||') AS attr_images
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_name = p.name
                WHERE p.name = %s
                GROUP BY p.id, p.no, p.name, p.image, p.type, p.type_name, p.form, p.form_name
                """,
                (name,),
            )
            return await cur.fetchone()


async def get_pokemon_detail(name: str) -> dict:
    """查询单只精灵的详情行。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM pokemon_detail WHERE pokemon_name = %s", (name,))
            return await cur.fetchone() or {}


async def get_pokemon_skills(name: str) -> list[dict]:
    """查询单只精灵的技能列表。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT s.name, s.attr, s.power, s.type, s.consume, s.skill_desc, s.icon
                FROM pokemon_skill ps
                JOIN skill s ON s.name = ps.skill_name
                WHERE ps.pokemon_name = %s
                ORDER BY ps.sort_order
                """,
                (name,),
            )
            return await cur.fetchall()
