from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status

from api.schemas.ops import (
    OpsDictItem,
    OpsDictListResponse,
    OpsDictUpsertRequest,
    OpsLoginRequest,
    OpsLoginResponse,
    OpsProfileUpdateRequest,
    OpsUserCreateRequest,
    OpsUserInfo,
    OpsUserListResponse,
    OpsUserUpdateRequest,
    OpsPokemonDetailResponse,
    OpsPokemonListResponse,
    OpsPokemonOptionsResponse,
    OpsPokemonUpsertRequest,
    OpsEvolutionChainResponse,
    OpsEvolutionChainUpsertRequest,
    OpsFriendImageUploadResponse,
    OpsYiseImageUploadResponse,
    OpsSkillDetailResponse,
    OpsSkillIconUploadResponse,
    OpsSkillListResponse,
    OpsSkillOptionsResponse,
    OpsSkillUpsertRequest,
    OpsSkillUsageResponse,
    OpsSkillStoneAvailableResponse,
    OpsSkillStoneCreateRequest,
    OpsSkillStoneItem,
    OpsSkillStoneListResponse,
    OpsSkillStoneUpdateRequest,
    OpsResonanceMagicListResponse,
    OpsResonanceMagicDetailResponse,
    OpsResonanceMagicUpsertRequest,
    OpsResonanceMagicIconUploadResponse,
)
from api.schemas.banner import BannerItem, BannerListResponse, BannerUpsertRequest
from api.schemas.personality import (
    PersonalityItem,
    PersonalityListResponse,
    PersonalityResetResponse,
    PersonalityUpsertRequest,
)
from api.schemas.starlight_duel import (
    StarlightDuelEpisodeDetail,
    StarlightDuelEpisodeListResponse,
    StarlightDuelEpisodeUpsertRequest,
    StarlightDuelSearchResponse,
)
from api.schemas.pokemon_lineup import (
    PokemonLineupDetail,
    PokemonLineupListResponse,
    PokemonLineupSearchResponse,
    PokemonLineupUpsertRequest,
)
from api.services import ops_service, banner_service, personality_service, starlight_duel_service, pokemon_lineup_service

router = APIRouter(prefix="/api/ops", tags=["ops"])


async def get_current_ops_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    token = authorization.split(" ", 1)[1].strip()
    return await ops_service.get_current_user_from_token(token)


@router.post("/auth/login", response_model=OpsLoginResponse)
async def ops_login(payload: OpsLoginRequest):
    return await ops_service.login(payload.username, payload.password)


@router.get("/auth/me", response_model=OpsUserInfo)
async def ops_me(current_user: dict = Depends(get_current_ops_user)):
    return ops_service.serialize_ops_user(current_user)


@router.put("/auth/me", response_model=OpsUserInfo)
async def update_ops_me(
    payload: OpsProfileUpdateRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_profile(current_user, payload.model_dump())


@router.get("/dicts", response_model=OpsDictListResponse)
async def get_dicts(
    dict_type: str = Query(default=""),
    code: str = Query(default=""),
    label: str = Query(default=""),
    page: int | None = Query(default=1, ge=1),
    page_size: int | None = Query(default=10, ge=1, le=100),
    _: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_dicts(
        dict_type=dict_type,
        code=code,
        label=label,
        page=page,
        page_size=page_size,
    )


@router.post("/dicts", response_model=OpsDictItem)
async def create_dict(
    payload: OpsDictUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_dict(current_user, payload.model_dump())


@router.put("/dicts/{dict_id}", response_model=OpsDictItem)
async def update_dict(
    dict_id: int,
    payload: OpsDictUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_dict(current_user, dict_id, payload.model_dump())


@router.delete("/dicts/{dict_id}", status_code=204)
async def delete_dict(
    dict_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_dict(current_user, dict_id)
    return Response(status_code=204)


@router.get("/users", response_model=OpsUserListResponse)
async def list_ops_users(current_user: dict = Depends(get_current_ops_user)):
    return await ops_service.list_users(current_user)


@router.post("/users", response_model=OpsUserInfo)
async def create_ops_user(
    payload: OpsUserCreateRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_user(current_user, payload.model_dump())


@router.put("/users/{user_id}", response_model=OpsUserInfo)
async def update_ops_user(
    user_id: int,
    payload: OpsUserUpdateRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_user(current_user, user_id, payload.model_dump())


@router.delete("/users/{user_id}", status_code=204)
async def delete_ops_user(
    user_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_user(current_user, user_id)
    return Response(status_code=204)


@router.get("/pokemon", response_model=OpsPokemonListResponse)
async def list_ops_pokemon(
    keyword: str = Query(default=""),
    no: str = Query(default=""),
    name: str = Query(default=""),
    attr_id: int | None = Query(default=None, ge=1),
    egg_group: str = Query(default=""),
    type_code: str = Query(default=""),
    form_code: str = Query(default=""),
    trait_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_pokemon_for_ops(
        current_user,
        keyword=keyword,
        no=no,
        name=name,
        attr_id=attr_id,
        egg_group=egg_group,
        type_code=type_code,
        form_code=form_code,
        trait_id=trait_id,
        page=page,
        page_size=page_size,
    )


@router.get("/pokemon/options", response_model=OpsPokemonOptionsResponse)
async def get_ops_pokemon_options(current_user: dict = Depends(get_current_ops_user)):
    return await ops_service.get_pokemon_options_for_ops(current_user)


@router.post("/pokemon/friend-image", response_model=OpsFriendImageUploadResponse)
async def upload_ops_friend_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.save_friend_image_upload(current_user, file)


@router.post("/pokemon/yise-image", response_model=OpsYiseImageUploadResponse)
async def upload_ops_yise_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.save_yise_image_upload(current_user, file)


@router.post("/resonance-magics/icon", response_model=OpsResonanceMagicIconUploadResponse)
async def upload_ops_resonance_magic_icon(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.save_resonance_magic_icon_upload(current_user, file)


@router.get("/pokemon/{pokemon_id}", response_model=OpsPokemonDetailResponse)
async def get_ops_pokemon_detail(
    pokemon_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_pokemon_detail_for_ops(current_user, pokemon_id)


@router.get("/pokemon/{pokemon_id}/evolution-chain", response_model=OpsEvolutionChainResponse)
async def get_ops_pokemon_evolution_chain(
    pokemon_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_pokemon_evolution_chain_for_ops(current_user, pokemon_id)


@router.put("/pokemon/{pokemon_id}/evolution-chain", response_model=OpsEvolutionChainResponse)
async def update_ops_pokemon_evolution_chain(
    pokemon_id: int,
    payload: OpsEvolutionChainUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_pokemon_evolution_chain_for_ops(current_user, pokemon_id, payload.model_dump())


@router.get("/pokemon/evolution-chain/search", response_model=OpsEvolutionChainResponse)
async def search_ops_pokemon_evolution_chain(
    keyword: str = Query(default=""),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.search_pokemon_evolution_chain_for_ops(current_user, keyword)


@router.post("/pokemon", response_model=OpsPokemonDetailResponse)
async def create_ops_pokemon(
    payload: OpsPokemonUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_pokemon_for_ops(current_user, payload.model_dump())


@router.put("/pokemon/{pokemon_id}", response_model=OpsPokemonDetailResponse)
async def update_ops_pokemon(
    pokemon_id: int,
    payload: OpsPokemonUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_pokemon_for_ops(current_user, pokemon_id, payload.model_dump())


@router.delete("/pokemon/{pokemon_id}", status_code=204)
async def delete_ops_pokemon(
    pokemon_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_pokemon_for_ops(current_user, pokemon_id)
    return Response(status_code=204)


# ── Banner ──────────────────────────────────────────────


@router.get("/banners", response_model=BannerListResponse)
async def list_ops_banners(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await banner_service.list_banners_for_ops(current_user, page=page, page_size=page_size)


@router.post("/banners", response_model=BannerItem)
async def create_ops_banner(
    payload: BannerUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await banner_service.create_banner_for_ops(current_user, payload.model_dump())


@router.put("/banners/{banner_id}", response_model=BannerItem)
async def update_ops_banner(
    banner_id: int,
    payload: BannerUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await banner_service.update_banner_for_ops(current_user, banner_id, payload.model_dump())


@router.delete("/banners/{banner_id}", status_code=204)
async def delete_ops_banner(
    banner_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await banner_service.delete_banner_for_ops(current_user, banner_id)
    return Response(status_code=204)


# ---------- 技能维护 ----------

@router.get("/skills", response_model=OpsSkillListResponse)
async def list_ops_skills(
    keyword: str = Query(default=""),
    attr: str = Query(default=""),
    type_: str = Query(default="", alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_skills_for_ops(
        current_user,
        keyword=keyword,
        attr=attr,
        type_=type_,
        page=page,
        page_size=page_size,
    )


@router.get("/skills/options", response_model=OpsSkillOptionsResponse)
async def get_ops_skill_options(current_user: dict = Depends(get_current_ops_user)):
    return await ops_service.get_skill_options_for_ops(current_user)


@router.post("/skills/icon", response_model=OpsSkillIconUploadResponse)
async def upload_ops_skill_icon(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.save_skill_icon_upload(current_user, file)


@router.post("/skills", response_model=OpsSkillDetailResponse)
async def create_ops_skill(
    payload: OpsSkillUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_skill_for_ops(current_user, payload.model_dump())


@router.get("/skills/{skill_id}", response_model=OpsSkillDetailResponse)
async def get_ops_skill_detail(
    skill_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_skill_detail_for_ops(current_user, skill_id)


@router.put("/skills/{skill_id}", response_model=OpsSkillDetailResponse)
async def update_ops_skill(
    skill_id: int,
    payload: OpsSkillUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_skill_for_ops(current_user, skill_id, payload.model_dump())


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_ops_skill(
    skill_id: int,
    force: int = Query(default=0),
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_skill_for_ops(current_user, skill_id, force=bool(force))
    return Response(status_code=204)


@router.get("/skills/{skill_id}/usages", response_model=OpsSkillUsageResponse)
async def get_ops_skill_usages(
    skill_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_skill_usages_for_ops(current_user, skill_id)


# ---------- 技能石维护 ----------

@router.get("/skill-stones", response_model=OpsSkillStoneListResponse)
async def list_ops_skill_stones(
    keyword: str = Query(default=""),
    attr: str = Query(default=""),
    type_: str = Query(default="", alias="type"),
    obtain_keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_skill_stones_for_ops(
        current_user,
        keyword=keyword,
        attr=attr,
        type_=type_,
        obtain_keyword=obtain_keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/skill-stones/available-skills", response_model=OpsSkillStoneAvailableResponse)
async def list_ops_skill_stone_available_skills(
    keyword: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_available_skills_for_stone(current_user, keyword=keyword, limit=limit)


@router.post("/skill-stones", response_model=OpsSkillStoneItem)
async def create_ops_skill_stone(
    payload: OpsSkillStoneCreateRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_skill_stone_for_ops(current_user, payload.model_dump())


@router.get("/skill-stones/{stone_id}", response_model=OpsSkillStoneItem)
async def get_ops_skill_stone_detail(
    stone_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_skill_stone_detail_for_ops(current_user, stone_id)


@router.put("/skill-stones/{stone_id}", response_model=OpsSkillStoneItem)
async def update_ops_skill_stone(
    stone_id: int,
    payload: OpsSkillStoneUpdateRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_skill_stone_for_ops(current_user, stone_id, payload.model_dump())


@router.delete("/skill-stones/{stone_id}", status_code=204)
async def delete_ops_skill_stone(
    stone_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_skill_stone_for_ops(current_user, stone_id)
    return Response(status_code=204)


# ---------- 性格维护 ----------

@router.get("/personalities", response_model=PersonalityListResponse)
async def list_ops_personalities(
    keyword: str = Query(default=""),
    buff_stat: str = Query(default=""),
    nerf_stat: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.list_personalities_for_ops(
        current_user,
        keyword=keyword,
        buff_stat=buff_stat,
        nerf_stat=nerf_stat,
        page=page,
        page_size=page_size,
    )


@router.post("/personalities/reset", response_model=PersonalityResetResponse)
async def reset_ops_personalities(
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.reset_personalities_from_json(current_user)


@router.post("/personalities", response_model=PersonalityItem)
async def create_ops_personality(
    payload: PersonalityUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.create_personality_for_ops(current_user, payload.model_dump())


@router.get("/personalities/{pid}", response_model=PersonalityItem)
async def get_ops_personality(
    pid: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.get_personality_for_ops(current_user, pid)


@router.put("/personalities/{pid}", response_model=PersonalityItem)
async def update_ops_personality(
    pid: int,
    payload: PersonalityUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await personality_service.update_personality_for_ops(current_user, pid, payload.model_dump())


@router.delete("/personalities/{pid}", status_code=204)
async def delete_ops_personality(
    pid: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await personality_service.delete_personality_for_ops(current_user, pid)
    return Response(status_code=204)


# ── 星光对决 ────────────────────────────────────────────


@router.get("/starlight-duel/search-pokemon", response_model=StarlightDuelSearchResponse)
async def search_starlight_duel_pokemon(
    keyword: str = Query(default=""),
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.search_pokemon_for_ops(current_user, keyword)


@router.get("/starlight-duel/search-skills", response_model=StarlightDuelSearchResponse)
async def search_starlight_duel_skills(
    keyword: str = Query(default=""),
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.search_skills_for_ops(current_user, keyword)


@router.get("/starlight-duel/episodes", response_model=StarlightDuelEpisodeListResponse)
async def list_ops_starlight_duel_episodes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.list_episodes_for_ops(current_user, page=page, page_size=page_size)


@router.post("/starlight-duel/episodes", response_model=StarlightDuelEpisodeDetail)
async def create_ops_starlight_duel_episode(
    payload: StarlightDuelEpisodeUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.create_episode_for_ops(current_user, payload.model_dump())


@router.get("/starlight-duel/episodes/{episode_id}", response_model=StarlightDuelEpisodeDetail)
async def get_ops_starlight_duel_episode(
    episode_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.get_episode_detail_for_ops(current_user, episode_id)


@router.put("/starlight-duel/episodes/{episode_id}", response_model=StarlightDuelEpisodeDetail)
async def update_ops_starlight_duel_episode(
    episode_id: int,
    payload: StarlightDuelEpisodeUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await starlight_duel_service.update_episode_for_ops(current_user, episode_id, payload.model_dump())


@router.delete("/starlight-duel/episodes/{episode_id}", status_code=204)
async def delete_ops_starlight_duel_episode(
    episode_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await starlight_duel_service.delete_episode_for_ops(current_user, episode_id)
    return Response(status_code=204)


# ── 精灵阵容 ────────────────────────────────────────────


@router.get("/pokemon-lineups/search-pokemon", response_model=PokemonLineupSearchResponse)
async def search_pokemon_lineup_pokemon(
    keyword: str = Query(default=""),
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.search_pokemon_for_ops(current_user, keyword)


@router.get("/pokemon-lineups/search-skills", response_model=PokemonLineupSearchResponse)
async def search_pokemon_lineup_skills(
    keyword: str = Query(default=""),
    pokemon_id: int | None = Query(default=None),
    exclude_skill_ids: list[int] = Query(default_factory=list),
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.search_skills_for_ops(
        current_user,
        keyword=keyword,
        pokemon_id=pokemon_id,
        exclude_skill_ids=exclude_skill_ids,
    )


@router.get("/pokemon-lineups", response_model=PokemonLineupListResponse)
async def list_ops_pokemon_lineups(
    keyword: str = Query(default=""),
    source_type: str = Query(default=""),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.list_lineups_for_ops(
        current_user,
        keyword=keyword,
        source_type=source_type.strip(),
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.post("/pokemon-lineups", response_model=PokemonLineupDetail)
async def create_ops_pokemon_lineup(
    payload: PokemonLineupUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.create_lineup_for_ops(current_user, payload.model_dump())


@router.get("/pokemon-lineups/{lineup_id}", response_model=PokemonLineupDetail)
async def get_ops_pokemon_lineup(
    lineup_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.get_lineup_detail_for_ops(current_user, lineup_id)


@router.put("/pokemon-lineups/{lineup_id}", response_model=PokemonLineupDetail)
async def update_ops_pokemon_lineup(
    lineup_id: int,
    payload: PokemonLineupUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pokemon_lineup_service.update_lineup_for_ops(current_user, lineup_id, payload.model_dump())


@router.delete("/pokemon-lineups/{lineup_id}", status_code=204)
async def delete_ops_pokemon_lineup(
    lineup_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await pokemon_lineup_service.delete_lineup_for_ops(current_user, lineup_id)
    return Response(status_code=204)


# ---------- 共鸣魔法维护 ----------


@router.get("/resonance-magics", response_model=OpsResonanceMagicListResponse)
async def list_ops_resonance_magics(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.list_resonance_magics_for_ops(
        current_user,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("/resonance-magics", response_model=OpsResonanceMagicDetailResponse)
async def create_ops_resonance_magic(
    payload: OpsResonanceMagicUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.create_resonance_magic_for_ops(current_user, payload.model_dump())


@router.get("/resonance-magics/{magic_id}", response_model=OpsResonanceMagicDetailResponse)
async def get_ops_resonance_magic(
    magic_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_resonance_magic_for_ops(current_user, magic_id)


@router.put("/resonance-magics/{magic_id}", response_model=OpsResonanceMagicDetailResponse)
async def update_ops_resonance_magic(
    magic_id: int,
    payload: OpsResonanceMagicUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await ops_service.update_resonance_magic_for_ops(current_user, magic_id, payload.model_dump())


@router.delete("/resonance-magics/{magic_id}", status_code=204)
async def delete_ops_resonance_magic(
    magic_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await ops_service.delete_resonance_magic_for_ops(current_user, magic_id)
    return Response(status_code=204)
