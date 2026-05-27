"""洛克纪年（大事记）后台维护接口。

可配置时间、标题、正文、图片，增删改查一条事迹。图片走通用 /api/file/upload
拿到 URL 后，以字符串数组形式提交到 images 字段。需 Bearer 鉴权。
"""

from fastapi import APIRouter, Depends, Query, Response

from api.routes.ops import get_current_ops_user
from api.schemas.roco_chronology import (
    OpsChronologyItem,
    OpsChronologyListResponse,
    OpsChronologyUpsertRequest,
)
from api.services import roco_chronology_service

router = APIRouter(prefix="/api/ops/chronology", tags=["ops"])


@router.get("", response_model=OpsChronologyListResponse)
async def list_ops_chronology(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await roco_chronology_service.list_for_ops(
        current_user,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=OpsChronologyItem)
async def create_ops_chronology(
    payload: OpsChronologyUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await roco_chronology_service.create_for_ops(current_user, payload.model_dump())


@router.get("/{item_id}", response_model=OpsChronologyItem)
async def get_ops_chronology(
    item_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await roco_chronology_service.get_for_ops(current_user, item_id)


@router.put("/{item_id}", response_model=OpsChronologyItem)
async def update_ops_chronology(
    item_id: int,
    payload: OpsChronologyUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await roco_chronology_service.update_for_ops(current_user, item_id, payload.model_dump())


@router.delete("/{item_id}", status_code=204)
async def delete_ops_chronology(
    item_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await roco_chronology_service.delete_for_ops(current_user, item_id)
    return Response(status_code=204)
