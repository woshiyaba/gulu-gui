from datetime import date, datetime

from pydantic import BaseModel, Field


# ── 前台展示 ────────────────────────────────────────────


class ChronologyListItem(BaseModel):
    """前台时间轴列表项：时间 + 标题 + id + 封面图。"""

    id: int
    event_date: date
    title: str = ""
    cover_image: str = ""


class ChronologyDetail(BaseModel):
    """前台详情：图文等完整信息。"""

    id: int
    event_date: date
    title: str = ""
    content: str = ""
    images: list[str] = Field(default_factory=list)


# ── 后台维护 ────────────────────────────────────────────


class OpsChronologyItem(BaseModel):
    """后台编辑用的完整事迹。"""

    id: int
    event_date: date
    title: str = ""
    content: str = ""
    images: list[str] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OpsChronologyListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[OpsChronologyItem] = Field(default_factory=list)


class OpsChronologyUpsertRequest(BaseModel):
    event_date: date
    title: str = ""
    content: str = ""
    images: list[str] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True
