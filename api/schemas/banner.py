from pydantic import BaseModel, Field


class BannerItem(BaseModel):
    id: int
    title: str = ""
    image_url: str = ""
    link_type: str = ""
    link_param: str = ""
    sort_order: int = 0
    is_active: bool = True


class BannerListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 10
    items: list[BannerItem] = Field(default_factory=list)


class BannerUpsertRequest(BaseModel):
    title: str = ""
    image_url: str
    link_type: str = ""
    link_param: str = ""
    sort_order: int = 0
    is_active: bool = True
