"""洛克纪年（大事记）前台接口。

- 列表：返回时间 + 标题 + id + 封面图，供时间轴展示。
- 详情：点击某条后返回图文等完整信息。
"""

from fastapi import APIRouter

from api.schemas.roco_chronology import ChronologyDetail, ChronologyListItem
from api.services import roco_chronology_service

router = APIRouter(prefix="/api/chronology", tags=["chronology"])


@router.get("", response_model=list[ChronologyListItem])
async def list_chronology():
    """时间轴列表，按事件时间倒序，仅返回已启用项。"""
    return await roco_chronology_service.list_published()


@router.get("/{item_id}", response_model=ChronologyDetail)
async def get_chronology_detail(item_id: int):
    """事迹详情（图文）。"""
    return await roco_chronology_service.get_published_detail(item_id)
