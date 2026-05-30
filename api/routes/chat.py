"""宠物对话前台接口。"""

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
