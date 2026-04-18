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
    OpsSkillDetailResponse,
    OpsSkillIconUploadResponse,
    OpsSkillListResponse,
    OpsSkillOptionsResponse,
    OpsSkillUpsertRequest,
    OpsSkillUsageResponse,
)
from api.services import ops_service

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
