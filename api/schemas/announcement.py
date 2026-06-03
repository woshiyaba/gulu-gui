from datetime import datetime

from pydantic import BaseModel, Field


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


class AnnouncementLikeResponse(BaseModel):
    like_count: int = Field(ge=0, description="公告点赞总数")


class AboutResponse(BaseModel):
    """"关于"卡片话语；每条 text 可含 \\n 换行，由前端拆分渲染。"""

    texts: list[str] = Field(default_factory=list, description="关于我们的话语列表")
