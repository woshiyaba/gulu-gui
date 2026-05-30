"""宠物对话 prompt 后台维护接口。

每只宠物（精灵）绑定一段独立人设 prompt（支持 Markdown），可控制是否启用对话。
增删改查一条 prompt，需 Bearer 鉴权（编辑需 editor/admin，删除需 admin）。
"""

from fastapi import APIRouter, Depends, Query, Response

from api.routes.ops import get_current_ops_user
from api.schemas.pet_prompt import (
    OpsPetPromptItem,
    OpsPetPromptListResponse,
    OpsPetPromptUpsertRequest,
)
from api.services import pet_prompt_service

router = APIRouter(prefix="/api/ops/pet-prompt", tags=["ops"])


@router.get("", response_model=OpsPetPromptListResponse)
async def list_ops_pet_prompt(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_ops_user),
):
    return await pet_prompt_service.list_for_ops(
        current_user,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=OpsPetPromptItem)
async def create_ops_pet_prompt(
    payload: OpsPetPromptUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pet_prompt_service.create_for_ops(current_user, payload.model_dump())


@router.get("/{item_id}", response_model=OpsPetPromptItem)
async def get_ops_pet_prompt(
    item_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pet_prompt_service.get_for_ops(current_user, item_id)


@router.put("/{item_id}", response_model=OpsPetPromptItem)
async def update_ops_pet_prompt(
    item_id: int,
    payload: OpsPetPromptUpsertRequest,
    current_user: dict = Depends(get_current_ops_user),
):
    return await pet_prompt_service.update_for_ops(current_user, item_id, payload.model_dump())


@router.delete("/{item_id}", status_code=204)
async def delete_ops_pet_prompt(
    item_id: int,
    current_user: dict = Depends(get_current_ops_user),
):
    await pet_prompt_service.delete_for_ops(current_user, item_id)
    return Response(status_code=204)
