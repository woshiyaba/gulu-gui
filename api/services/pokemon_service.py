import re
from decimal import Decimal
from fractions import Fraction

from common.utils.eggExperimentalMatcher import match_spirit_by_egg_experiment

from api.repositories import (
    attribute_matchup_repository,
    pokemon_filter_repository,
    pokemon_repository,
)
from api.utils.pokemon_mapper import (
    to_attribute_item,
    to_pokemon_detail,
    to_pokemon_list_item,
    to_skill_item,
)
from api.utils.type_chart import build_defensive_type_chart_payload, combine_defensive_multipliers


class PokemonNotFoundError(Exception):
    """精灵不存在。"""


def _strip_variant_suffix(name: str) -> str:
    """去掉形态括号后缀，便于把同阶段的多个样子归到一起。"""
    return name.split("（", 1)[0].strip()


def _build_fallback_evolution_chain(base: dict) -> dict:
    """当数据库还没有进化链数据时，至少返回当前形态自己。"""
    return {
        "chain_id": None,
        "stages": [
            {
                "sort_order": 1,
                "next_condition": "",
                "pre_condition": "",
                "items": [
                    {
                        "name": base["name"],
                        "image_url": base.get("image_lc") or "",
                    }
                ],
            }
        ],
    }


def _group_variants_by_base_name(variant_rows: list[dict]) -> dict[str, list[dict]]:
    """把所有具体形态按基础名分组，并去重。"""
    grouped: dict[str, list[dict]] = {}
    seen_names: set[str] = set()

    for row in variant_rows:
        name = row["name"]
        if name in seen_names:
            continue
        seen_names.add(name)
        # 先添加一次原本的形态，再添加一次去掉形态后缀的形态
        grouped.setdefault(name, []).append(
            {
                "name": name,
                "image_url": row.get("image_lc") or "",
            }
        )
        base_name = _strip_variant_suffix(name)
        # 判断grouped 中是否已经有base_name的key
        if base_name == name:
            continue
        grouped.setdefault(base_name, []).append(
            {
                "name": name,
                "image_url": row.get("image_lc") or "",
            }
        )

    return grouped


def _fraction_from_db(value) -> Fraction:
    """把 PG NUMERIC / Decimal / str / float 安全转为 Fraction。"""
    if value is None:
        return Fraction(1, 1)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(str(value))
    return Fraction(str(value)).limit_denominator(10_000)


def _compute_restrain(
        defender_attrs: list[str],
        defensive_rows: list[dict],
        offensive_rows: list[dict],
) -> dict:
    """
    从属性克制矩阵计算 restrain 四个列表：
    - weak_against：进攻方对该精灵倍率 > 1 的属性（被克制）
    - resist：进攻方对该精灵倍率 < 1 的属性（抵抗）
    - strong_against：该精灵进攻对方倍率 > 1 的属性（克制）
    - resisted：该精灵进攻对方倍率 < 1 的属性（被抵抗）
    """
    # 防守侧：合并多属性倍率（使用洛克王国规则）
    # 先按进攻属性分组收集所有防守倍率
    def_multipliers: dict[str, list[Fraction]] = {}
    for row in defensive_rows:
        attacker = row.get("attacker_attr")
        if not attacker:
            continue
        mul = _fraction_from_db(row.get("multiplier"))
        def_multipliers.setdefault(attacker, []).append(mul)

    # 使用洛克王国规则合并倍率
    def_combined: dict[str, Fraction] = {}
    for attacker, multipliers in def_multipliers.items():
        def_combined[attacker] = combine_defensive_multipliers(multipliers)

    weak_against = [a for a, m in def_combined.items() if m > 1]
    resist = [a for a, m in def_combined.items() if 0 < m < 1]

    # 进攻侧：合并多属性倍率（取最优）
    off_by_defender: dict[str, Fraction] = {}
    for row in offensive_rows:
        defender = row.get("defender_attr")
        if not defender:
            continue
        mul = _fraction_from_db(row.get("multiplier"))
        # 多进攻属性对同一防守属性取最大倍率
        if defender not in off_by_defender or mul > off_by_defender[defender]:
            off_by_defender[defender] = mul

    strong_against = [d for d, m in off_by_defender.items() if m > 1]
    resisted = [d for d, m in off_by_defender.items() if 0 < m < 1]

    return {
        "strong_against": strong_against,
        "weak_against": weak_against,
        "resist": resist,
        "resisted": resisted,
    }


async def get_attributes() -> list[dict]:
    rows = await pokemon_repository.list_attributes()
    return [to_attribute_item(row) for row in rows]


async def get_egg_group_names() -> list[str]:
    rows = await pokemon_repository.list_egg_groups()
    return [row["group_name"] for row in rows]


async def get_categories() -> list[dict]:
    """返回 category 表的全量映射数据。"""
    rows = await pokemon_repository.list_categories()
    return [
        {**row, "category_image_url": row.get("category_image_url") or ""}
        for row in rows
    ]


async def get_skill_types() -> list[str]:
    return await pokemon_repository.list_skill_types()


async def get_pokemon_marks() -> list[dict]:
    """返回 pokemon_mark 表的全部词条。"""
    rows = await pokemon_repository.list_pokemon_marks()
    return [
        {
            "id": row["id"],
            "key": row["key"],
            "zh_name": row["zh_name"],
            "zh_description": row.get("zh_description", ""),
            "sort_order": row["sort_order"],
            "image": row.get("image") or "",
        }
        for row in rows
    ]


async def get_skills(
        name: str = "",
        skill_type: str = "",
        attr: str = "",
) -> dict:
    rows = await pokemon_repository.list_skills(
        name=name.strip(),
        skill_type=skill_type.strip(),
        attr=attr.strip(),
    )
    return {
        "total": len(rows),
        "items": [to_skill_item(row) for row in rows],
    }


async def get_skill_stones(skill_name: str = "") -> dict:
    rows = await pokemon_repository.list_skill_stones(skill_name=skill_name.strip())
    return {
        "total": len(rows),
        "items": [
            {
                "skill_name": row["skill_name"],
                "obtain_method": row["obtain_method"],
                "icon": row.get("icon") or "",
            }
            for row in rows
        ],
    }


async def list_pokemon_filter_options() -> list[dict]:
    """返回小程序图鉴页可用的筛选/排序按钮，由 pokemon_filter_option 表统一维护。"""
    rows = await pokemon_filter_repository.list_active_filter_options()
    return [
        {
            "id": row["id"],
            "code": row.get("code") or "",
            "label": row.get("label") or "",
            "filter_type": row.get("filter_type") or "",
            "order_by": row.get("order_by") or "",
            "order_dir": row.get("order_dir") or "",
            "sort_order": int(row.get("sort_order") or 0),
        }
        for row in rows
    ]


async def _resolve_filter_codes(
        filter_codes: list[str] | None,
        *,
        shiny_only: bool,
        order_by: str,
        order_dir: str,
) -> tuple[bool, str, str]:
    """根据 filter_code 列表覆盖 shiny_only / order_by / order_dir。多个 sort 类按顺序后者覆盖前者。"""
    if not filter_codes:
        return shiny_only, order_by, order_dir
    codes = [c.strip() for c in filter_codes if c and c.strip()]
    if not codes:
        return shiny_only, order_by, order_dir
    rows = await pokemon_filter_repository.get_filter_options_by_codes(codes)
    by_code = {row["code"]: row for row in rows}
    # 按用户请求顺序应用，保持"后者覆盖前者"
    for code in codes:
        row = by_code.get(code)
        if not row:
            continue
        ftype = (row.get("filter_type") or "").strip()
        if ftype == "shiny":
            shiny_only = True
        elif ftype == "sort":
            ob = (row.get("order_by") or "").strip()
            od = (row.get("order_dir") or "").strip()
            if ob:
                order_by = ob
            if od:
                order_dir = od
    return shiny_only, order_by, order_dir


async def get_pokemon(
        name: str = "",
        attrs: list[str] | None = None,
        egg_groups: list[str] | None = None,
        shiny_only: bool = False,
        order_by: str = "no",
        order_dir: str = "asc",
        filter_codes: list[str] | None = None,
        page: int = 1,
        page_size: int = 30,
) -> dict:
    attrs = _normalize_multi_filter(attrs)
    egg_groups = _normalize_multi_filter(egg_groups)
    shiny_only, order_by, order_dir = await _resolve_filter_codes(
        filter_codes,
        shiny_only=shiny_only,
        order_by=order_by,
        order_dir=order_dir,
    )
    total = await pokemon_repository.count_pokemon(
        name=name,
        attrs=attrs,
        egg_groups=egg_groups,
        shiny_only=shiny_only,
    )
    rows = await pokemon_repository.list_pokemon(
        name=name,
        attrs=attrs,
        egg_groups=egg_groups,
        shiny_only=shiny_only,
        order_by=order_by,
        order_dir=order_dir,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [to_pokemon_list_item(row) for row in rows],
    }


def _normalize_multi_filter(values: list[str] | None) -> list[str]:
    """
    仅按"集合语义"处理：attr=火&attr=恶。
    不做逗号拆分，避免把合法值误切分。
    """
    if not values:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        v = raw.strip()
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _parse_pokemon_no(raw) -> int | None:
    """从形如 'NO.375' 的编号中提取数字，剪掉 'NO.' 前缀。"""
    if raw is None:
        return None
    match = re.search(r"\d+", str(raw))
    return int(match.group()) if match else None


def _to_number(value) -> float:
    """把 DB 数值安全转成 float，None / 非数转 0。"""
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _compute_size_tag(row: dict, height_cm: int, weight_g: int) -> str:
    """按蛋孵化的大小阈值判定体型标签（阈值单位与 height_cm/weight_g 一致）。

    - 大块头：身高、体重均 >= 大体型下限（且两个下限都不为 0）
    - 小不点：身高、体重均 <= 小体型上限（且两个上限都不为 0）
    其余返回空字符串。
    """
    big_len_min = _to_number(row.get("big_size_length_min"))
    big_wt_min = _to_number(row.get("big_size_weight_min"))
    if big_len_min and big_wt_min and height_cm >= big_len_min and weight_g >= big_wt_min:
        return "大块头"

    small_len_max = _to_number(row.get("small_size_length_max"))
    small_wt_max = _to_number(row.get("small_size_weight_max"))
    if small_len_max and small_wt_max and height_cm <= small_len_max and weight_g <= small_wt_max:
        return "小不点"

    return ""


def _to_pokemon_egg_hatch_size(row: dict | None, current_pokemon_id: int) -> dict | None:
    """把蛋孵化尺寸阈值行转成详情接口字段。"""
    if not row:
        return None
    source_pokemon_id = row["source_pokemon_id"]
    return {
        "source_pokemon_id": source_pokemon_id,
        "source_pokemon_name": row.get("source_pokemon_name") or "",
        "is_chain_reused": source_pokemon_id != current_pokemon_id,
        "big_size_length_min": row.get("big_size_length_min") or 0,
        "big_size_weight_min": row.get("big_size_weight_min") or 0,
        "small_size_length_max": row.get("small_size_length_max") or 0,
        "small_size_weight_max": row.get("small_size_weight_max") or 0,
    }


async def get_pokemon_by_body_metrics(height_m: float, weight_kg: float) -> dict:
    # 单位换算统一放在后端，避免前端和后端口径不一致。
    height_cm = round(height_m * 100)
    weight_g = round(weight_kg * 1000)
    rows = await pokemon_repository.list_pokemon_by_body_metrics(
        height_cm=height_cm,
        weight_g=weight_g,
    )

    # 套用蛋实验匹配规律：长度用米、重量用千克；no 取 pokemon.no 去掉 "NO." 前缀
    base_spirits = [
        {
            "id": r["id"],
            "no": _parse_pokemon_no(r.get("no")),
            "lengthMin": float(r.get("height_low") or 0) / 100,
            "lengthMax": float(r.get("height_high") or 0) / 100,
            "weightMin": float(r.get("weight_low") or 0) / 1000,
            "weightMax": float(r.get("weight_high") or 0) / 1000,
        }
        for r in rows
    ]
    match_result = match_spirit_by_egg_experiment(height_m, weight_kg, base_spirits)

    row_by_id = {r["id"]: r for r in rows}
    items: list[dict] = []
    seen_ids: set = set()

    # 按匹配概率降序（匹配器已排序）输出，并写入百分比字段；全部返回，不过滤低概率
    for m in match_result["experimentMatches"]:
        r = row_by_id.get(m["id"])
        if r is None:
            continue
        items.append(
            {
                "pet_name": r["pokemon_name"],
                "image_url": r.get("image") or "",
                "match_percent": m.get("experimentScore", 0),
                "match_percent_text": m.get("experimentScoreText", "<1%"),
                "tag": _compute_size_tag(r, height_cm, weight_g),
            }
        )
        seen_ids.add(m["id"])

    # 兜底：匹配器未覆盖的行（理论上不会出现）也一并返回，概率置 0
    for r in rows:
        if r["id"] in seen_ids:
            continue
        items.append(
            {
                "pet_name": r["pokemon_name"],
                "image_url": r.get("image") or "",
                "match_percent": 0,
                "match_percent_text": "<1%",
                "tag": _compute_size_tag(r, height_cm, weight_g),
            }
        )

    return {
        "height_m": height_m,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "weight_g": weight_g,
        "total": len(items),
        "items": items,
    }


async def get_pokemon_eggs(name: str = "", page: int = 1, page_size: int = 30) -> dict:
    """分页返回 pokemon_egg 表全部字段，支持按名称模糊筛选。"""
    name = name.strip()
    total = await pokemon_repository.count_pokemon_eggs(name=name)
    rows = await pokemon_repository.list_pokemon_eggs(name=name, page=page, page_size=page_size)
    items = [
        {
            "id": row["id"],
            "source_id": row["source_id"],
            "name": row.get("name") or "",
            "form": row.get("form") or "",
            "icon": row.get("icon") or "",
            "pokemon_source_id": row.get("pokemon_source_id"),
            "pokemon_id": row.get("pokemon_id"),
            "pokemon_name": row.get("pokemon_name") or "",
            "item_quality": row.get("item_quality") or 0,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
        }
        for row in rows
    ]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


async def get_pokemon_fruits(name: str = "", page: int = 1, page_size: int = 30) -> dict:
    """分页返回 pokemon_fruit 表全部字段，支持按名称模糊筛选。"""
    name = name.strip()
    total = await pokemon_repository.count_pokemon_fruits(name=name)
    rows = await pokemon_repository.list_pokemon_fruits(name=name, page=page, page_size=page_size)
    items = [
        {
            "id": row["id"],
            "source_id": row["source_id"],
            "name": row.get("name") or "",
            "icon": row.get("icon") or "",
            "pokemon_source_id": row.get("pokemon_source_id"),
            "item_quality": row.get("item_quality") or 0,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
        }
        for row in rows
    ]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


async def get_pet_map_points() -> list[dict]:
    """返回 pet_map_point 表全量点位。"""
    rows = await pokemon_repository.list_pet_map_points()
    return [
        {
            "id": row["id"],
            "source_id": row["source_id"],
            "map_id": row["map_id"],
            "title": row.get("title", ""),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "category_id": row["category_id"],
            "category_image_url": row.get("category_image_url") or "",
        }
        for row in rows
    ]


async def get_pokemon_detail(name: str) -> dict:
    base = await pokemon_repository.get_pokemon_base(name)
    if not base:
        raise PokemonNotFoundError(name)

    detail = await pokemon_repository.get_pokemon_detail(name)
    skills = await pokemon_repository.get_pokemon_skills(name)
    egg_hatch_size = await pokemon_repository.get_detail_egg_hatch_size_source(
        pokemon_id=base["id"],
        chain_id=base.get("chain_id"),
    )
    egg_hatch = await pokemon_repository.get_egg_hatch_info(name)
    payload = to_pokemon_detail(base=base, detail=detail, skills_raw=skills, egg_hatch=egg_hatch)
    payload["egg_hatch_size"] = _to_pokemon_egg_hatch_size(
        row=egg_hatch_size,
        current_pokemon_id=base["id"],
    )

    axis = await attribute_matchup_repository.list_attr_axis_order()
    defender_names = [a["attr_name"] for a in payload.get("attributes") or []]
    defensive_rows = await attribute_matchup_repository.list_matchups_for_defenders(defender_names)
    offensive_rows = await attribute_matchup_repository.list_matchups_for_attackers(defender_names)

    payload["defensive_type_chart"] = build_defensive_type_chart_payload(
        defender_attrs=defender_names,
        axis=axis,
        matchup_rows=defensive_rows,
    )
    payload["restrain"] = _compute_restrain(
        defender_attrs=defender_names,
        defensive_rows=defensive_rows,
        offensive_rows=offensive_rows,
    )
    return payload


async def get_pokemon_evolution_chain(name: str) -> dict:
    """查询精灵所属的整条进化链，并展开每一阶段的所有具体形态。"""
    base = await pokemon_repository.get_pokemon_base(name)
    if not base:
        raise PokemonNotFoundError(name)

    chain_id = await pokemon_repository.get_pokemon_chain_id(name)
    if chain_id is None:
        return _build_fallback_evolution_chain(base)

    chain_members = await pokemon_repository.list_evolution_chain_members(chain_id)
    if not chain_members:
        return _build_fallback_evolution_chain(base)

    base_names = [member["pokemon_name"] for member in chain_members]
    variant_rows = await pokemon_repository.list_pokemon_variants_by_base_names(base_names)
    grouped_variants = _group_variants_by_base_name(variant_rows)

    stages: list[dict] = []
    for member in chain_members:
        base_name = member["pokemon_name"]
        items = grouped_variants.get(base_name) or [
            {
                "name": base_name,
                "image_url": "",
            }
        ]
        stages.append(
            {
                "sort_order": member["sort_order"],
                "next_condition": member.get("evolution_condition", "") or "",
                "pre_condition": member.get("pre_evolution_condition", "") or "",
                "items": items,
            }
        )

    return {
        "chain_id": chain_id,
        "stages": stages,
    }
