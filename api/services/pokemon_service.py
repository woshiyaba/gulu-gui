from api.repositories import pokemon_repository
from api.utils.pokemon_mapper import (
    to_attribute_item,
    to_pokemon_detail,
    to_pokemon_list_item,
)


class PokemonNotFoundError(Exception):
    """精灵不存在。"""


async def get_attributes() -> list[dict]:
    rows = await pokemon_repository.list_attributes()
    return [to_attribute_item(row) for row in rows]


async def get_pokemon(
    name: str = "", attr: str = "", page: int = 1, page_size: int = 30
) -> dict:
    total = await pokemon_repository.count_pokemon(name=name, attr=attr)
    rows = await pokemon_repository.list_pokemon(
        name=name,
        attr=attr,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [to_pokemon_list_item(row) for row in rows],
    }


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
        "items": [{"pet_name": r["pokemon_name"]} for r in rows],
    }


async def get_pokemon_detail(name: str) -> dict:
    base = await pokemon_repository.get_pokemon_base(name)
    if not base:
        raise PokemonNotFoundError(name)

    detail = await pokemon_repository.get_pokemon_detail(name)
    skills = await pokemon_repository.get_pokemon_skills(name)
    return to_pokemon_detail(base=base, detail=detail, skills_raw=skills)
