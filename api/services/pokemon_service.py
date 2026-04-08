from api.repositories import pokemon_repository
from api.utils.pokemon_mapper import (
    to_attribute_item,
    to_pokemon_detail,
    to_pokemon_list_item,
)


class PokemonNotFoundError(Exception):
    """精灵不存在。"""


def get_attributes() -> list[dict]:
    rows = pokemon_repository.list_attributes()
    return [to_attribute_item(row) for row in rows]


def get_pokemon(name: str = "", attr: str = "", page: int = 1, page_size: int = 30) -> dict:
    total = pokemon_repository.count_pokemon(name=name, attr=attr)
    rows = pokemon_repository.list_pokemon(
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


def get_pokemon_detail(name: str) -> dict:
    base = pokemon_repository.get_pokemon_base(name)
    if not base:
        raise PokemonNotFoundError(name)

    detail = pokemon_repository.get_pokemon_detail(name)
    skills = pokemon_repository.get_pokemon_skills(name)
    return to_pokemon_detail(base=base, detail=detail, skills_raw=skills)
