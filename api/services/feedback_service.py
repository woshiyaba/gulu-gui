"""用户反馈业务逻辑。

- 提交反馈：保存内容 / 联系方式 / 分类 / 提交用户。
- 查询反馈：后台分页查看，可按状态过滤。
- 更新状态：后台标记反馈处理进度。
"""

from api.repositories import feedback_repository


async def submit_feedback(
    user_id: int | None,
    content: str,
    contact: str | None,
    feedback_type: str | None,
) -> dict:
    return await feedback_repository.create_feedback(user_id, content, contact, feedback_type)


async def list_feedback(status: str | None, limit: int, offset: int) -> dict:
    total, items = await feedback_repository.list_feedback(status, limit, offset)
    return {"total": total, "items": items}


async def update_status(feedback_id: int, status: str) -> dict | None:
    return await feedback_repository.update_status(feedback_id, status)
