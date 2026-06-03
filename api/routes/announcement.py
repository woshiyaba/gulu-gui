"""站点公告前台接口。

- 公告内容：返回当前启用中的站点公告。
- 公告点赞：查询 / +1。
"""

from fastapi import APIRouter

from api.schemas.announcement import (
    AboutResponse,
    AnnouncementLikeResponse,
    PublicAnnouncement,
)
from api.services import announcement_service

router = APIRouter(prefix="/api/announcement", tags=["announcement"])


@router.get("", response_model=PublicAnnouncement | None)
async def get_announcement():
    """返回当前启用中的站点公告；未启用或内容为空时返回 null。"""
    return await announcement_service.get_active_announcement()


@router.get("/about", response_model=AboutResponse)
async def get_about():
    """"关于"卡片话语（存于 sys_dict：dict_type=about，按 sort_order 排序）。

    每条 label 可含 \\n 换行，原样下发，由前端拆分渲染。
    """
    texts = await announcement_service.get_about_texts()
    return {"texts": texts}


@router.get("/likes", response_model=AnnouncementLikeResponse)
async def get_announcement_likes():
    """公告点赞总数（存于 sys_dict：dict_type=announcement, code=like_count）。"""
    count = await announcement_service.get_announcement_like_count()
    return {"like_count": count}


@router.post("/likes", response_model=AnnouncementLikeResponse)
async def like_announcement():
    """公告点赞 +1。"""
    count = await announcement_service.like_announcement()
    return {"like_count": count}
