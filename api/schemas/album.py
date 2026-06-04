from datetime import datetime

from pydantic import BaseModel, Field


class AlbumPhoto(BaseModel):
    """一张相册照片。"""

    id: int
    user_id: int
    pet_id: int
    image_url: str
    is_featured: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlbumCreateRequest(BaseModel):
    """新增相册照片：用户 id + 宠物 id + 图片 URL。"""

    user_id: int = Field(..., description="用户 id")
    pet_id: int = Field(..., description="宠物（精灵）id")
    image_url: str = Field(..., min_length=1, description="图片访问 URL（OSS 地址）")
    is_featured: bool = Field(False, description="是否直接标记为精选")


class AlbumFeaturedRequest(BaseModel):
    """设置 / 取消某张照片的精选状态。"""

    is_featured: bool = Field(..., description="True 设为精选，False 取消精选")
