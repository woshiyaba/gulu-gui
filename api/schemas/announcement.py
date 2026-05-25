from datetime import datetime

from pydantic import BaseModel


class AnnouncementItem(BaseModel):
    """后台编辑用的完整公告配置（单条）。"""

    id: int
    title: str = ""
    content: str = ""
    is_active: bool = False
    updated_at: datetime | None = None


class PublicAnnouncement(BaseModel):
    """前台展示用的公告，未启用或为空时接口返回 null。"""

    title: str = ""
    content: str = ""
    updated_at: datetime | None = None


class AnnouncementUpdateRequest(BaseModel):
    title: str = ""
    content: str = ""
    is_active: bool = False
