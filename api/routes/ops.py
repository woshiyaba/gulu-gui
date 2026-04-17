from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

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
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    _: dict = Depends(get_current_ops_user),
):
    return await ops_service.get_dicts(
        dict_type=dict_type,
        keyword=keyword,
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
