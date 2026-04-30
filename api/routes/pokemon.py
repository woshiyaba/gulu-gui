import asyncio

from fastapi import APIRouter, HTTPException, Query

from api.schemas.pokemon import (
    AttributeItem,
    CategoryItem,
    PetMapPointItem,
    PokemonEggListResponse,
    PokemonFruitListResponse,
    PokemonEvolutionChainResponse,
    PokemonBodyMatchResponse,
    PokemonDetailResponse,
    PokemonListResponse,
    PokemonMarkItem,
    SkillListResponse,
    SkillStoneListResponse,
)
from api.schemas.banner import BannerItem
from api.schemas.personality import PersonalityItem
from api.schemas.pokemon_lineup import (
    BattlePkRequest,
    BattlePkResponse,
    BloodlineOption,
    PokemonLineupDetail,
    PokemonLineupPublicList,
    ResonanceMagicOption,
)
from api.repositories import ops_repository
from api.services import pokemon_lineup_service
from api.services.pokemon_service import (
    PokemonNotFoundError,
    get_attributes as get_attributes_service,
    get_categories as get_categories_service,
    get_egg_group_names as get_egg_group_names_service,
    get_pet_map_points as get_pet_map_points_service,
    get_pokemon_eggs as get_pokemon_eggs_service,
    get_pokemon_fruits as get_pokemon_fruits_service,
    get_pokemon_marks as get_pokemon_marks_service,
    get_pokemon_by_body_metrics as get_pokemon_by_body_metrics_service,
    get_pokemon as get_pokemon_service,
    get_pokemon_detail as get_pokemon_detail_service,
    get_pokemon_evolution_chain as get_pokemon_evolution_chain_service,
    get_skill_stones as get_skill_stones_service,
    get_skill_types as get_skill_types_service,
    get_skills as get_skills_service,
)
from api.services import banner_service, personality_service

router = APIRouter(prefix="/api")


@router.get("/banners", response_model=list[BannerItem])
async def get_banners():
    return await banner_service.list_active_banners()


@router.get("/starlight-duel/latest", response_model=PokemonLineupDetail | None)
async def get_starlight_duel_latest():
    items = await pokemon_lineup_service.list_active_lineups(source_type="starlight_duel")
    return items[0] if items else None


@router.get("/starlight-duel/{lineup_id}", response_model=PokemonLineupDetail)
async def get_starlight_duel_by_lineup(lineup_id: int):
    lineup = await pokemon_lineup_service.get_lineup_detail(lineup_id)
    if not lineup:
        raise HTTPException(status_code=404, detail="阵容不存在或未启用")
    return lineup


@router.get("/pokemon-lineups", response_model=PokemonLineupPublicList)
async def get_pokemon_lineups(
    source_type: str = Query(default="", description="阵容分类筛选"),
    ids: list[int] = Query(default=[], description="按 ID 列表筛选"),
):
    items = await pokemon_lineup_service.list_active_lineups(
        source_type=source_type, ids=ids or None,
    )
    return {"items": items}


@router.get("/pokemon-lineups/{lineup_id}", response_model=PokemonLineupDetail)
async def get_pokemon_lineup_detail(lineup_id: int):
    lineup = await pokemon_lineup_service.get_lineup_detail(lineup_id)
    if not lineup:
        raise HTTPException(status_code=404, detail="阵容不存在或未启用")
    return lineup


@router.post("/battle-pk", response_model=BattlePkResponse)
async def battle_pk(payload: BattlePkRequest):
    """用户提交两套阵容，由 PK 子智能体按经典回合制规则模拟对战并返回结构化分析。"""
    if not payload.team_a.members or not payload.team_b.members:
        raise HTTPException(status_code=400, detail="双方阵容均需至少配置 1 只精灵")

    from agents.sub.pk_subagent import analyze_battle

    team_a = payload.team_a.model_dump()
    team_b = payload.team_b.model_dump()
    return await asyncio.to_thread(analyze_battle, team_a, team_b)


@router.get("/bloodlines", response_model=list[BloodlineOption])
async def get_bloodlines():
    """公开返回精灵血脉字典（sys_dict 中 dict_type=pet_bloodline），供用户配置阵容时使用。"""
    rows = await ops_repository.list_dicts_all(dict_type="pet_bloodline")
    return [
        {"id": row["id"], "code": row.get("code") or "", "label": row.get("label") or ""}
        for row in rows
    ]


@router.get("/resonance-magics", response_model=list[ResonanceMagicOption])
async def get_resonance_magics_public():
    """公开返回共鸣魔法列表，供用户配置阵容时使用。"""
    _, rows = await ops_repository.list_resonance_magics_for_ops(page=1, page_size=200)
    from api.utils.media import build_resonance_magic_icon_url

    return [
        {
            "id": row["id"],
            "name": row.get("name") or "",
            "description": row.get("description") or "",
            "icon_url": build_resonance_magic_icon_url((row.get("icon") or "").strip()),
            "max_usage_count": int(row.get("max_usage_count") or 0),
        }
        for row in rows
    ]


@router.get("/attributes", response_model=list[AttributeItem])
async def get_attributes():
    """返回所有不重复的属性列表，用于前端筛选栏。"""
    return await get_attributes_service()


@router.get("/personalities", response_model=list[PersonalityItem])
async def get_personalities_public():
    """返回全部精灵性格字典（公共只读，供图鉴/计算器使用）。"""
    return await personality_service.list_personalities_public()


@router.get("/egg-groups", response_model=list[str])
async def get_egg_groups():
    """返回所有不重复的蛋组名称，用于前端筛选。"""
    return await get_egg_group_names_service()


@router.get("/pokemon/categories", response_model=list[CategoryItem])
async def get_categories():
    """全量返回 category 表中的 category_id 映射数据。"""
    return await get_categories_service()


@router.get("/pokemon/map-points", response_model=list[PetMapPointItem])
async def get_pet_map_points():
    """全量返回 pet_map_point 表数据，并补 category_id 对应图标地址。"""
    return await get_pet_map_points_service()


@router.get("/pokemon-eggs", response_model=PokemonEggListResponse)
async def get_pokemon_eggs(
    name: str = Query(default="", description="精灵蛋名称关键词（模糊匹配）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    """分页返回 pokemon_egg 表全部字段，支持按名称模糊筛选。"""
    return await get_pokemon_eggs_service(name=name, page=page, page_size=page_size)


@router.get("/pokemon-fruits", response_model=PokemonFruitListResponse)
async def get_pokemon_fruits(
    name: str = Query(default="", description="果实名称关键词（模糊匹配）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    """分页返回 pokemon_fruit 表全部字段，支持按名称模糊筛选。"""
    return await get_pokemon_fruits_service(name=name, page=page, page_size=page_size)


@router.get("/pokemon-marks", response_model=list[PokemonMarkItem])
async def get_pokemon_marks():
    """返回 pokemon_mark 表的全部词条（印记、状态、增益、减益、环境等战斗术语）。"""
    return await get_pokemon_marks_service()


@router.get("/skill-stones", response_model=SkillStoneListResponse)
async def get_skill_stones(
    skill_name: str = Query(default="", description="技能名关键词；为空时返回全部技能石"),
):
    """按技能名查询技能石；不传 skill_name 时返回全部。"""
    return await get_skill_stones_service(skill_name=skill_name)


@router.get("/skill-types", response_model=list[str])
async def get_skill_types():
    """返回所有不重复的技能类型（物攻/魔攻/状态/防御），用于前端筛选。"""
    return await get_skill_types_service()


@router.get("/skills", response_model=SkillListResponse)
async def get_skills(
    name: str = Query(default="", description="技能名关键词"),
    skill_type: str = Query(default="", description="技能类型：物攻/魔攻/状态/防御"),
    attr: str = Query(default="", description="技能属性：草/火/水 等"),
):
    """查询技能列表，支持按名称模糊搜索、按类型和属性筛选。"""
    return await get_skills_service(name=name, skill_type=skill_type, attr=attr)


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
