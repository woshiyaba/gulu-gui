from pydantic import BaseModel, Field


class AnnouncementLikeResponse(BaseModel):
    like_count: int = Field(ge=0, description="公告点赞总数")
