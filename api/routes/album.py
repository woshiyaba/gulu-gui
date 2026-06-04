"""精灵相册接口。

用户可上传与某只宠物的合照、设置精选、查询相册、删除照片。
"""

from fastapi import APIRouter, HTTPException, Query

from api.schemas.album import AlbumCreateRequest, AlbumFeaturedRequest, AlbumPhoto
from api.services import album_service

router = APIRouter(prefix="/api/album", tags=["album"])


@router.post("", response_model=AlbumPhoto)
async def create_photo(payload: AlbumCreateRequest):
    """新增一张相册照片：用户 id + 宠物 id + 图片 URL。"""
    return await album_service.add_photo(
        user_id=payload.user_id,
        pet_id=payload.pet_id,
        image_url=payload.image_url,
        is_featured=payload.is_featured,
    )


@router.get("", response_model=list[AlbumPhoto])
async def list_photos(
    user_id: int = Query(..., description="用户 id"),
    pet_id: int = Query(..., description="宠物（精灵）id"),
):
    """查询某用户某宠物的相册，精选照片永远排在最前面。"""
    return await album_service.list_photos(user_id=user_id, pet_id=pet_id)


@router.post("/{photo_id}/featured", response_model=AlbumPhoto)
async def set_featured(photo_id: int, payload: AlbumFeaturedRequest):
    """设置 / 取消某张照片的精选状态。"""
    photo = await album_service.set_featured(photo_id, payload.is_featured)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    return photo


@router.delete("/{photo_id}", response_model=AlbumPhoto)
async def delete_photo(photo_id: int):
    """删除一张照片，并从 OSS 删除对应图片对象。"""
    photo = await album_service.delete_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    return photo
