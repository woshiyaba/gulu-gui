from fastapi import APIRouter, HTTPException, Query

from api.schemas.pokemon import (
    AttributeItem,
    PokemonEvolutionChainResponse,
    PokemonBodyMatchResponse,
    PokemonDetailResponse,
    PokemonListResponse,
)
from api.services.pokemon_service import (
    PokemonNotFoundError,
    get_attributes as get_attributes_service,
    get_egg_group_names as get_egg_group_names_service,
    get_pokemon_by_body_metrics as get_pokemon_by_body_metrics_service,
    get_pokemon as get_pokemon_service,
    get_pokemon_detail as get_pokemon_detail_service,
    get_pokemon_evolution_chain as get_pokemon_evolution_chain_service,
)

router = APIRouter(prefix="/api")

@router.get("/attributes", response_model=list[AttributeItem])
async def get_attributes():
    """返回所有不重复的属性列表，用于前端筛选栏。"""
    return await get_attributes_service()


@router.get("/egg-groups", response_model=list[str])
async def get_egg_groups():
    """返回所有不重复的蛋组名称，用于前端筛选。"""
    return await get_egg_group_names_service()


@router.get("/pokemon", response_model=PokemonListResponse)
async def get_pokemon(
    name: str = Query(default="", description="精灵名称关键词"),
    attr: list[str] | None = Query(default=None, description="属性多选筛选（同类 AND，需同时命中）"),
    egg_group: list[str] | None = Query(default=None, description="蛋组多选筛选（同类 AND，需同时命中）"),
    order_by: str = Query(default="no", description="排序字段：no/total_stats/hp/atk/matk/def_val/mdef/spd"),
    order_dir: str = Query(default="asc", description="排序方向：asc/desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    """
    分页查询精灵列表，支持按名称模糊搜索、属性与蛋组精确筛选（条件之间为 AND）。
    返回 {total, page, page_size, items}。
    """
    return await get_pokemon_service(
        name=name,
        attrs=attr,
        egg_groups=egg_group,
        order_by=order_by,
        order_dir=order_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/pokemon/body-match", response_model=PokemonBodyMatchResponse)
async def get_pokemon_by_body_metrics(
    height_m: float = Query(..., gt=0, description="身高，单位 m"),
    weight_kg: float = Query(..., gt=0, description="体重，单位 kg"),
):
    """
    根据用户输入的身高和体重，查询区间内可命中的精灵名称列表。
    """
    return await get_pokemon_by_body_metrics_service(height_m=height_m, weight_kg=weight_kg)


@router.get("/pokemon/evolution-chain/{pokemon_name}", response_model=PokemonEvolutionChainResponse)
async def get_pokemon_evolution_chain(pokemon_name: str):
    """
    查询某只精灵所在的完整进化链，并按阶段返回每层的所有形态图片与名称。
    """
    try:
        return await get_pokemon_evolution_chain_service(pokemon_name)
    except PokemonNotFoundError as exc:
        raise HTTPException(status_code=404, detail="精灵不存在") from exc


@router.get("/pokemon/{pokemon_name}", response_model=PokemonDetailResponse)
async def get_pokemon_detail(pokemon_name: str):
    """
    查询单只精灵的完整详情：基础信息、种族值、特性、属性克制、技能列表。
    """
    try:
        return await get_pokemon_detail_service(pokemon_name)
    except PokemonNotFoundError as exc:
        raise HTTPException(status_code=404, detail="精灵不存在") from exc
