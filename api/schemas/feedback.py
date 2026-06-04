from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    """用户提交反馈：内容必填，联系方式 / 分类可选。"""

    content: str = Field(..., min_length=1, max_length=2000, description="反馈内容")
    contact: str | None = Field(None, max_length=128, description="联系方式（可选）")
    feedback_type: str | None = Field(None, max_length=32, description="反馈分类（可选，如 bug/建议/其他）")


class FeedbackItem(BaseModel):
    """一条反馈记录。"""

    id: int
    user_id: int | None = None
    content: str
    contact: str | None = None
    feedback_type: str | None = None
    status: str = "pending"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FeedbackListResponse(BaseModel):
    """后台反馈列表。"""

    total: int
    items: list[FeedbackItem]


class FeedbackStatusUpdateRequest(BaseModel):
    """后台更新反馈处理状态。"""

    status: str = Field(..., description="处理状态：pending / handled")
