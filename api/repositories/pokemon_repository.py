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


def _build_filters(name: str = "", attr: str = "", egg_group: str = "") -> tuple[str, list]:
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

    if egg_group:
        conditions.append(
            "EXISTS (SELECT 1 FROM pokemon_egg_group peg "
            "WHERE peg.pokemon_id = p.id AND peg.group_name = %s)"
        )
        params.append(egg_group)

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


async def list_egg_groups() -> list[dict]:
    """查询所有不重复的蛋组名称（用于筛选）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT group_name FROM pokemon_egg_group ORDER BY group_name"
            )
            return await cur.fetchall()


async def count_pokemon(name: str = "", attr: str = "", egg_group: str = "") -> int:
    """查询符合条件的精灵总数。"""
    where_clause, params = _build_filters(name=name, attr=attr, egg_group=egg_group)
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
    egg_group: str = "",
    page: int = 1,
    page_size: int = 30,
) -> list[dict]:
    """分页查询精灵基础信息与属性。"""
    where_clause, params = _build_filters(name=name, attr=attr, egg_group=egg_group)
    offset = (page - 1) * page_size

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT
                    p.no, p.name, p.image, p.image_lc, p.type, p.type_name, p.form, p.form_name,
                    GROUP_CONCAT(pa.attr_name ORDER BY pa.id SEPARATOR ',') AS attr_names,
                    GROUP_CONCAT(pa.attr_image ORDER BY pa.id SEPARATOR '|||') AS attr_images,
                    (SELECT GROUP_CONCAT(peg.group_name ORDER BY peg.id SEPARATOR ',')
                     FROM pokemon_egg_group peg WHERE peg.pokemon_id = p.id) AS egg_group_names
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_name = p.name
                {where_clause}
                GROUP BY p.id, p.no, p.name, p.image, p.image_lc, p.type, p.type_name, p.form, p.form_name
                ORDER BY p.no, p.id
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            return await cur.fetchall()


async def list_pokemon_by_body_metrics(height_cm: int, weight_g: int) -> list[dict]:
    """按身高和体重区间匹配宠物，并合并同名变种结果。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    e.pokemon_name,
                    p.image,
                    p.no,
                    p.form,
                    p.form_name,
                    p.id
                FROM egg_hatch_pet e
                JOIN pokemon p ON p.name = e.pokemon_name
                WHERE e.is_leader_form = 0
                  AND e.height_low <= %s
                  AND e.height_high >= %s
                  AND e.weight_low <= %s
                  AND e.weight_high >= %s
                ORDER BY p.no, p.id, e.pokemon_name
                """,
                (height_cm, height_cm, weight_g, weight_g),
            )
            rows = await cur.fetchall()
            return _dedupe_body_metric_rows(rows)


async def get_pokemon_base(name: str) -> dict | None:
    """查询单只精灵的基础信息与属性。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT p.no, p.name, p.image, p.image_lc, p.type, p.type_name, p.form, p.form_name,
                       GROUP_CONCAT(pa.attr_name ORDER BY pa.id SEPARATOR ',') AS attr_names,
                       GROUP_CONCAT(pa.attr_image ORDER BY pa.id SEPARATOR '|||') AS attr_images,
                       (SELECT GROUP_CONCAT(peg.group_name ORDER BY peg.id SEPARATOR ',')
                        FROM pokemon_egg_group peg WHERE peg.pokemon_id = p.id) AS egg_group_names
                FROM pokemon p
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_name = p.name
                WHERE p.name = %s
                GROUP BY p.id, p.no, p.name, p.image, p.image_lc, p.type, p.type_name, p.form, p.form_name
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


async def get_pokemon_chain_id(name: str) -> int | None:
    """查询某个具体形态所属的进化链编号。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT chain_id FROM pokemon_detail WHERE pokemon_name = %s",
                (name,),
            )
            row = await cur.fetchone() or {}
            return row.get("chain_id")


async def list_evolution_chain_members(chain_id: int) -> list[dict]:
    """按顺序查询一条进化链的基础阶段数据。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
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
        conditions.append("(p.name = %s OR p.name LIKE CONCAT(%s, '（', '%%'))")
        params.extend([base_name, base_name])

    pool = await get_pool()
    async with pool.acquire() as conn:
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
