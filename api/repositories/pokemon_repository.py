import re

from db.connection import get_pool

_PAREN_SUFFIX_PATTERN = re.compile(r"（[^）]*）")


def _strip_variant_suffix(name: str) -> str:
    """去掉名称中的括号后缀，用于聚合同一只宠物的不同命名。"""
    return _PAREN_SUFFIX_PATTERN.sub("", name).strip()


def _is_original_form(row: dict) -> bool:
    """判断是否为原始形态。"""
    return row.get("form") == "original" or row.get("form_name") == "原始形态"


def _is_regional_form(row: dict) -> bool:
    """判断是否为地区形态。"""
    return row.get("form") == "regional" or row.get("form_name") == "地区形态"


def _dedupe_body_metric_rows(rows: list[dict]) -> list[dict]:
    """
    先排除地区形态，再按去括号后的名字去重。
    同一组里优先保留第一个原始形态；若没有原始形态，则退回第一个非地区形态。
    """
    grouped_rows: dict[str, list[dict]] = {}

    for row in rows:
        base_name = _strip_variant_suffix(row["pokemon_name"])
        grouped_rows.setdefault(base_name, []).append(row)

    deduped_rows: list[dict] = []
    for grouped in grouped_rows.values():
        non_regional_rows = [row for row in grouped if not _is_regional_form(row)]
        if not non_regional_rows:
            continue

        chosen_row = next(
            (row for row in non_regional_rows if _is_original_form(row)),
            non_regional_rows[0],
        )
        deduped_rows.append({
            "pokemon_name": chosen_row["pokemon_name"],
            "image": chosen_row.get("image", ""),
        })

    return deduped_rows


def _build_filters(
    name: str = "",
    attrs: list[str] | None = None,
    egg_groups: list[str] | None = None,
) -> tuple[str, list]:
    """构建列表查询的 WHERE 条件与参数。"""
    conditions: list[str] = []
    params: list = []
    attrs = attrs or []
    egg_groups = egg_groups or []

    if name:
        conditions.append("p.name LIKE %s")
        params.append(f"%{name}%")

    if attrs:
        attr_placeholders = ", ".join(["%s"] * len(attrs))
        # 属性多选按交集处理：必须同时拥有所选全部属性（适配双属性精灵检索）
        conditions.append(
            "EXISTS ("
            "SELECT 1 FROM pokemon_attribute pa2 "
            "JOIN attribute a2 ON a2.id = pa2.attr_id "
            "WHERE pa2.pokemon_id = p.id "
            f"AND a2.name IN ({attr_placeholders}) "
            "GROUP BY pa2.pokemon_id "
            f"HAVING COUNT(DISTINCT a2.name) = {len(attrs)}"
            ")"
        )
        params.extend(attrs)

    if egg_groups:
        egg_placeholders = ", ".join(["%s"] * len(egg_groups))
        # 蛋组多选按交集处理：必须同时属于所选全部蛋组
        conditions.append(
            "EXISTS ("
            "SELECT 1 FROM pokemon_egg_group peg "
            "WHERE peg.pokemon_id = p.id "
            f"AND peg.group_name IN ({egg_placeholders}) "
            "GROUP BY peg.pokemon_id "
            f"HAVING COUNT(DISTINCT peg.group_name) = {len(egg_groups)}"
            ")"
        )
        params.extend(egg_groups)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


def _build_order_clause(order_by: str = "no", order_dir: str = "asc") -> str:
    """构建安全排序子句，仅允许白名单字段。"""
    order_field_map = {
        "no": "p.no",
        "total_stats": "(p.hp + p.atk + p.matk + p.def_val + p.mdef + p.spd)",
        "hp": "p.hp",
        "atk": "p.atk",
        "matk": "p.matk",
        "def_val": "p.def_val",
        "mdef": "p.mdef",
        "spd": "p.spd",
    }
    sql_field = order_field_map.get(order_by, "p.no")
    sql_dir = "DESC" if order_dir.lower() == "desc" else "ASC"
    # 同值时按编号和主键稳定排序，避免翻页抖动
    return f"ORDER BY {sql_field} {sql_dir}, p.no ASC, p.id ASC"


async def list_attributes() -> list[dict]:
    """查询所有属性。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name AS attr_name, image AS attr_image FROM attribute ORDER BY sort_order"
            )
            return await cur.fetchall()


async def list_egg_groups() -> list[dict]:
    """查询所有不重复的蛋组名称（用于筛选）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT group_name FROM pokemon_egg_group ORDER BY group_name"
            )
            return await cur.fetchall()


async def list_categories() -> list[dict]:
    """查询 category 表的全部映射数据。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, category_id, description, type
                FROM category
                ORDER BY category_id, id
                """
            )
            return await cur.fetchall()


async def list_skill_types() -> list[str]:
    """查询所有不重复的技能类型（物攻/魔攻/状态/防御），供前端筛选。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT type FROM skill WHERE type != '' ORDER BY type"
            )
            rows = await cur.fetchall()
            return [row["type"] for row in rows]


async def list_skills(
    name: str = "",
    skill_type: str = "",
    attr: str = "",
) -> list[dict]:
    """查询技能列表，三个筛选条件均可选。"""
    conditions: list[str] = []
    params: list[str] = []

    if name:
        conditions.append("s.name LIKE %s")
        params.append(f"%{name}%")
    if skill_type:
        conditions.append("s.type = %s")
        params.append(skill_type)
    if attr:
        conditions.append("a.name = %s")
        params.append(attr)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT s.name, COALESCE(a.name, '') AS attr,
                       s.power, s.type, s.consume, s.skill_desc, s.icon
                FROM skill s
                LEFT JOIN attribute a ON a.id = s.attr_id
                {where_clause}
                ORDER BY s.name
                """,
                params,
            )
            return await cur.fetchall()


async def list_skill_stones(skill_name: str = "") -> list[dict]:
    """查询技能石列表；skill_name 为空时返回全部。"""
    params: list[str] = []
    where_clause = ""
    if skill_name:
        where_clause = "WHERE s.name LIKE %s"
        params.append(f"%{skill_name}%")

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT s.name AS skill_name, ss.obtain_method, s.icon
                FROM skill_stone ss
                JOIN skill s ON s.id = ss.skill_id
                {where_clause}
                ORDER BY s.name
                """,
                params,
            )
            return await cur.fetchall()


async def count_pokemon(
    name: str = "",
    attrs: list[str] | None = None,
    egg_groups: list[str] | None = None,
) -> int:
    """查询符合条件的精灵总数。"""
    where_clause, params = _build_filters(name=name, attrs=attrs, egg_groups=egg_groups)
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) AS cnt FROM pokemon p {where_clause}",
                params,
            )
            row = await cur.fetchone() or {}
            return row.get("cnt", 0)


async def list_pokemon(
    name: str = "",
    attrs: list[str] | None = None,
    egg_groups: list[str] | None = None,
    order_by: str = "no",
    order_dir: str = "asc",
    page: int = 1,
    page_size: int = 30,
) -> list[dict]:
    """分页查询精灵基础信息与属性。"""
    where_clause, params = _build_filters(name=name, attrs=attrs, egg_groups=egg_groups)
    order_clause = _build_order_clause(order_by=order_by, order_dir=order_dir)
    offset = (page - 1) * page_size

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT
                    p.no, p.name, p.image, p.image_lc, p.image_yise, p.type, p.type_name, p.form, p.form_name,
                    string_agg(a.name, ',' ORDER BY pa.id) AS attr_names,
                    string_agg(a.image, '|||' ORDER BY pa.id) AS attr_images,
                    (SELECT string_agg(peg.group_name, ',' ORDER BY peg.id)
                     FROM pokemon_egg_group peg WHERE peg.pokemon_id = p.id) AS egg_group_names
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_id = p.id
                LEFT JOIN attribute a ON a.id = pa.attr_id
                {where_clause}
                GROUP BY p.id, p.no, p.name, p.image, p.image_lc, p.image_yise, p.type, p.type_name, p.form, p.form_name,
                         p.hp, p.atk, p.matk, p.def_val, p.mdef, p.spd
                {order_clause}
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            return await cur.fetchall()


async def list_pokemon_by_body_metrics(height_cm: int, weight_g: int) -> list[dict]:
    """按身高和体重区间匹配宠物，并合并同名变种结果。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    p.name AS pokemon_name,
                    p.image,
                    p.no,
                    p.form,
                    p.form_name,
                    p.id
                FROM egg_hatch_pet e
                JOIN pokemon p ON p.id = e.pokemon_id
                WHERE e.is_leader_form = FALSE
                  AND e.height_low <= %s
                  AND e.height_high >= %s
                  AND e.weight_low <= %s
                  AND e.weight_high >= %s
                ORDER BY p.no, p.id, p.name
                """,
                (height_cm, height_cm, weight_g, weight_g),
            )
            rows = await cur.fetchall()
            return _dedupe_body_metric_rows(rows)


async def list_pet_map_points() -> list[dict]:
    """查询地图点位表的全部数据。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, source_id, map_id, title, latitude, longitude, category_id
                FROM pet_map_point
                ORDER BY id
                """
            )
            return await cur.fetchall()


async def get_pokemon_base(name: str) -> dict | None:
    """查询单只精灵的基础信息与属性。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT p.no, p.name, p.image, p.image_lc, p.image_yise, p.type, p.type_name, p.form, p.form_name,
                       string_agg(a.name, ',' ORDER BY pa.id) AS attr_names,
                       string_agg(a.image, '|||' ORDER BY pa.id) AS attr_images,
                       (SELECT string_agg(peg.group_name, ',' ORDER BY peg.id)
                        FROM pokemon_egg_group peg WHERE peg.pokemon_id = p.id) AS egg_group_names
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_id = p.id
                LEFT JOIN attribute a ON a.id = pa.attr_id
                WHERE p.name = %s
                GROUP BY p.id, p.no, p.name, p.image, p.image_lc, p.image_yise, p.type, p.type_name, p.form, p.form_name
                """,
                (name,),
            )
            return await cur.fetchone()


async def get_pokemon_detail(name: str) -> dict:
    """查询单只精灵的详情行（种族值、特性、获取方式）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT p.hp, p.atk, p.matk, p.def_val, p.mdef, p.spd,
                       p.obtain_method,
                       pt.name AS trait_name, pt.description AS trait_desc
                FROM pokemon p
                JOIN pokemon_trait pt ON pt.id = p.trait_id
                WHERE p.name = %s
                """,
                (name,),
            )
            return await cur.fetchone() or {}


async def get_pokemon_chain_id(name: str) -> int | None:
    """查询某个具体形态所属的进化链编号。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT chain_id FROM pokemon WHERE name = %s",
                (name,),
            )
            row = await cur.fetchone() or {}
            return row.get("chain_id")


async def list_evolution_chain_members(chain_id: int) -> list[dict]:
    """按顺序查询一条进化链的基础阶段数据。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT chain_id, sort_order, pokemon_name, evolution_condition
                FROM evolution_chain
                WHERE chain_id = %s
                ORDER BY sort_order
                """,
                (chain_id,),
            )
            return await cur.fetchall()


async def list_pokemon_variants_by_base_names(base_names: list[str]) -> list[dict]:
    """按基础名查出所有具体形态，用于组装进化链图片与名称。"""
    if not base_names:
        return []

    conditions: list[str] = []
    params: list[str] = []
    for base_name in dict.fromkeys(base_names):
        conditions.append("(p.name = %s OR p.name LIKE %s)")
        params.extend([base_name, f"{base_name}（%"])

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT p.no, p.id, p.name, p.image
                FROM pokemon p
                WHERE {' OR '.join(conditions)}
                ORDER BY p.no, p.id, p.name
                """,
                params,
            )
            return await cur.fetchall()


async def get_pokemon_skills(name: str) -> list[dict]:
    """查询单只精灵的技能列表。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT s.name, COALESCE(a.name, '') AS attr,
                       s.power, s.type, s.consume, s.skill_desc, s.icon,
                       ps.type AS source
                FROM pokemon_skill ps
                JOIN skill s ON s.id = ps.skill_id
                LEFT JOIN attribute a ON a.id = s.attr_id
                WHERE ps.pokemon_id = (SELECT id FROM pokemon WHERE name = %s)
                ORDER BY ps.sort_order
                """,
                (name,),
            )
            return await cur.fetchall()
