"""用户反馈接口。

- 用户在小程序提交反馈（公开接口，自动关联当前登录用户 id）。
- 后台分页查看反馈、更新处理状态（需运营 Bearer 鉴权）。
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from api.routes.ops import get_current_ops_user
from api.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackItem,
    FeedbackListResponse,
    FeedbackStatusUpdateRequest,
)
from api.services import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def _parse_user_id(authorization: str | None) -> int | None:
    """从 Authorization 头还原小程序登录用户 id；匿名 / 非数字时返回 None。"""
    if not authorization:
        return None
    token = authorization.strip()
    return int(token) if token.isdigit() else None


@router.post("", response_model=FeedbackItem)
async def create_feedback(
    payload: FeedbackCreateRequest,
    authorization: str | None = Header(default=None),
):
    """用户提交反馈，自动关联当前登录用户 id（匿名也可提交）。"""
    return await feedback_service.submit_feedback(
        user_id=_parse_user_id(authorization),
        content=payload.content,
        contact=payload.contact,
        feedback_type=payload.feedback_type,
    )


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    status: str | None = Query(default=None, description="按处理状态过滤：pending / handled"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_ops_user),
):
    """后台分页查看反馈，按时间倒序，可按状态过滤。"""
    return await feedback_service.list_feedback(status=status, limit=limit, offset=offset)


@router.patch("/{feedback_id}/status", response_model=FeedbackItem)
async def update_feedback_status(
    feedback_id: int,
    payload: FeedbackStatusUpdateRequest,
    _current_user: dict = Depends(get_current_ops_user),
):
    """后台更新某条反馈的处理状态。"""
    item = await feedback_service.update_status(feedback_id, payload.status)
    if not item:
        raise HTTPException(status_code=404, detail="反馈不存在")
    return item
