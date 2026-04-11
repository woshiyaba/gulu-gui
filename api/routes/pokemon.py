from fastapi import APIRouter, HTTPException, Query

from api.schemas.pokemon import (
    AttributeItem,
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
    attr: str = Query(default="", description="属性名称精确筛选"),
    egg_group: str = Query(default="", description="蛋组名称精确筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    """
    分页查询精灵列表，支持按名称模糊搜索、属性与蛋组精确筛选（条件之间为 AND）。
    返回 {total, page, page_size, items}。
    """
    return await get_pokemon_service(
        name=name,
        attr=attr,
        egg_group=egg_group,
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


@router.get("/pokemon/{pokemon_name}", response_model=PokemonDetailResponse)
async def get_pokemon_detail(pokemon_name: str):
    """
    查询单只精灵的完整详情：基础信息、种族值、特性、属性克制、技能列表。
    """
    try:
        return await get_pokemon_detail_service(pokemon_name)
    except PokemonNotFoundError as exc:
        raise HTTPException(status_code=404, detail="精灵不存在") from exc
