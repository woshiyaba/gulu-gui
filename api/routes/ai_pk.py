"""AI PK 路由 —— 提交流式任务 / 查询结果"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas.pokemon_lineup import BattlePkRequest, BattlePkResponse
from api.services import ai_pk_service

router = APIRouter(prefix="/api/ai-pk", tags=["ai-pk"])


class SubmitBattleRequest(BattlePkRequest):
    user_id: str


class SubmitBattleResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    user_id: str = ""
    status: str
    result: BattlePkResponse | None = None
    error: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@router.post("/battle-pk", response_model=SubmitBattleResponse)
async def submit_battle_pk(payload: SubmitBattleRequest):
    """提交两套阵容创建 PK 任务。立刻返回 task_id，分析过程通过 ws 流式推送。"""
    if not payload.team_a.members or not payload.team_b.members:
        raise HTTPException(status_code=400, detail="双方阵容均需至少配置 1 只精灵")
    if not payload.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id 不能为空")

    team_a = payload.team_a.model_dump()
    team_b = payload.team_b.model_dump()
    task_id = await ai_pk_service.submit_battle_task(payload.user_id, team_a, team_b)
    return SubmitBattleResponse(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    """根据 task_id 查询任务状态及最终结构化结果。"""
    row = await ai_pk_service.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    result_obj: BattlePkResponse | None = None
    if row.get("status") == "completed" and row.get("result"):
        result_obj = BattlePkResponse.model_validate(row["result"])

    return TaskStatusResponse(
        task_id=row["task_id"],
        user_id=row.get("user_id") or "",
        status=row["status"],
        result=result_obj,
        error=row.get("error") or "",
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
