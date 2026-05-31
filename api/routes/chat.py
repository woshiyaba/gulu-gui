"""宠物对话前台接口。"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services import pet_chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class PetChatEnabledResponse(BaseModel):
    pet_id: int
    enabled: bool


class PetAvatarResponse(BaseModel):
    pet_id: int
    avatar: str


class PetPromptExtraField(BaseModel):
    code: str
    label: str
    type: Literal["select", "text"]
    options: list[str] = []
    value: str = ""


class PetPromptExtraFormResponse(BaseModel):
    pet_id: int
    fields: list[PetPromptExtraField]


class PetPromptExtraUpdateRequest(BaseModel):
    user_id: str | int
    pet_id: int
    values: dict[str, str] = {}


class PetPromptExtraUpdateResponse(BaseModel):
    pet_id: int
    nickname: str
    attributes: dict[str, str]


@router.get("/pets/{pet_id}/enabled", response_model=PetChatEnabledResponse)
async def get_pet_chat_enabled(pet_id: int):
    """根据宠物 id 返回是否开启对话（pet_prompt.enabled），无配置视为未开启。"""
    enabled = await pet_chat_service.is_pet_chat_enabled(pet_id)
    return PetChatEnabledResponse(pet_id=pet_id, enabled=enabled)


@router.get("/pets/{pet_id}/avatar", response_model=PetAvatarResponse)
async def get_pet_avatar(pet_id: int):
    """根据宠物 id 从 pokemon 表查询头像（image）。宠物不存在时返回 404。"""
    avatar = await pet_chat_service.get_pet_avatar(pet_id)
    if avatar is None:
        raise HTTPException(status_code=404, detail="宠物不存在")
    return PetAvatarResponse(pet_id=pet_id, avatar=avatar)


@router.get("/pet-prompt-extra", response_model=PetPromptExtraFormResponse)
async def get_pet_prompt_extra(pet_id: int, user_id: str | None = None):
    """返回用户可编辑的自定义宠物信息字段及当前值（字段定义来自 sys_dict）。"""
    return await pet_chat_service.get_pet_prompt_extra_form(user_id, pet_id)


@router.post("/pet-prompt-extra-update", response_model=PetPromptExtraUpdateResponse)
async def update_pet_prompt_extra(payload: PetPromptExtraUpdateRequest):
    """保存用户填写的自定义宠物信息（nickname 入列，其余按中文 label 写入 attributes）。"""
    return await pet_chat_service.save_pet_prompt_extra(
        payload.user_id, payload.pet_id, payload.values,
    )
