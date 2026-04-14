from api.repositories import attribute_matchup_repository, pokemon_repository
from api.utils.media import build_image_url
from api.utils.pokemon_mapper import (
    to_attribute_item,
    to_pokemon_detail,
    to_pokemon_list_item,
    to_skill_item,
)
from api.utils.type_chart import build_defensive_type_chart_payload

_CATEGORY_ICON_BASE_URL = "http://101.126.137.23/images/icon"


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
                "items": [
                    {
                        "name": base["name"],
                        "image_url": build_image_url(base.get("image", "")),
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
        base_name = _strip_variant_suffix(name)
        grouped.setdefault(base_name, []).append(
            {
                "name": name,
                "image_url": build_image_url(row.get("image", "")),
            }
        )

    return grouped


async def get_attributes() -> list[dict]:
    rows = await pokemon_repository.list_attributes()
    return [to_attribute_item(row) for row in rows]


async def get_egg_group_names() -> list[str]:
    rows = await pokemon_repository.list_egg_groups()
    return [row["group_name"] for row in rows]


async def get_categories() -> list[dict]:
    """返回 category 表的全量映射数据，并补 category_id 对应图标地址。"""
    rows = await pokemon_repository.list_categories()
    return [
        {**row, "category_image_url": f"{_CATEGORY_ICON_BASE_URL}/{row['category_id']}.png"}
        for row in rows
    ]


async def get_skill_types() -> list[str]:
    return await pokemon_repository.list_skill_types()


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
                "icon": build_image_url(row.get("icon", "")),
            }
            for row in rows
        ],
    }


async def get_pokemon(
    name: str = "",
    attrs: list[str] | None = None,
    egg_groups: list[str] | None = None,
    order_by: str = "no",
    order_dir: str = "asc",
    page: int = 1,
    page_size: int = 30,
) -> dict:
    attrs = _normalize_multi_filter(attrs)
    egg_groups = _normalize_multi_filter(egg_groups)
    total = await pokemon_repository.count_pokemon(
        name=name,
        attrs=attrs,
        egg_groups=egg_groups,
    )
    rows = await pokemon_repository.list_pokemon(
        name=name,
        attrs=attrs,
        egg_groups=egg_groups,
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
    仅按“集合语义”处理：attr=火&attr=恶。
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


async def get_pokemon_by_body_metrics(height_m: float, weight_kg: float) -> dict:
    # 单位换算统一放在后端，避免前端和后端口径不一致。
    height_cm = round(height_m * 100)
    weight_g = round(weight_kg * 1000)
    rows = await pokemon_repository.list_pokemon_by_body_metrics(
        height_cm=height_cm,
        weight_g=weight_g,
    )
    return {
        "height_m": height_m,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "weight_g": weight_g,
        "total": len(rows),
        "items": [
            {
                "pet_name": r["pokemon_name"],
                "image_url": build_image_url(r.get("image", "")),
            }
            for r in rows
        ],
    }


async def get_pet_map_points() -> list[dict]:
    """返回 pet_map_point 表全量点位，并补 category_id 对应图标地址。"""
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
            "category_image_url": f"{_CATEGORY_ICON_BASE_URL}/{row['category_id']}.png",
        }
        for row in rows
    ]


async def get_pokemon_detail(name: str) -> dict:
    base = await pokemon_repository.get_pokemon_base(name)
    if not base:
        raise PokemonNotFoundError(name)

    detail = await pokemon_repository.get_pokemon_detail(name)
    skills = await pokemon_repository.get_pokemon_skills(name)
    payload = to_pokemon_detail(base=base, detail=detail, skills_raw=skills)

    axis = await attribute_matchup_repository.list_attr_axis_order()
    defender_names = [a["attr_name"] for a in payload.get("attributes") or []]
    rows = await attribute_matchup_repository.list_matchups_for_defenders(defender_names)
    payload["defensive_type_chart"] = build_defensive_type_chart_payload(
        defender_attrs=defender_names,
        axis=axis,
        matchup_rows=rows,
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
                "next_condition": member.get("evolution_condition", ""),
                "items": items,
            }
        )

    return {
        "chain_id": chain_id,
        "stages": stages,
    }
