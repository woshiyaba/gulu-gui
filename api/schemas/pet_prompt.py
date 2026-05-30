from datetime import datetime

from pydantic import BaseModel, Field


class OpsPetPromptItem(BaseModel):
    """后台编辑用的宠物 prompt（含所绑定宠物的名称 / 图片，便于列表展示）。"""

    id: int
    pet_id: int
    pet_name: str = ""
    pet_image: str = ""
    prompt: str = ""
    enabled: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OpsPetPromptListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[OpsPetPromptItem] = Field(default_factory=list)


class OpsPetPromptUpsertRequest(BaseModel):
    pet_id: int
    prompt: str = ""
    enabled: bool = False
