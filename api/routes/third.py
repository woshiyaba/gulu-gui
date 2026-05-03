from datetime import datetime, timedelta, timezone
from typing import Any

import anyio
import requests
from fastapi import APIRouter, HTTPException, status

from config import MERCHANT_API_KEY, MERCHANT_API_URL

router = APIRouter(prefix="/api/third", tags=["third"])

BEIJING_TZ = timezone(timedelta(hours=8))


def _format_ts(ts_ms: Any) -> str:
    if not ts_ms:
        return ""
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=BEIJING_TZ)
    return dt.strftime("%Y-%m-%d %H:%M")


def _build_product(item: dict[str, Any]) -> dict[str, Any]:
    s_time = item.get("start_time")
    e_time = item.get("end_time")
    icon = item.get("icon_url") or item.get("main_url") or ""
    name = item.get("name", "未知")

    if s_time and e_time:
        time_label = f"{_format_ts(s_time)} - {_format_ts(e_time)}"
    else:
        time_label = "全天供应"

    return {
        "name": name,
        "icon_url": icon,
        "start_time": s_time,
        "end_time": e_time,
        "time_label": time_label,
    }


def _process_merchant_data(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}

    now_ms = int(datetime.now(tz=BEIJING_TZ).timestamp() * 1000)
    activities = data.get("merchantActivities") or []
    activity = activities[0] if activities else {}
    items = (activity.get("get_props") or []) + (activity.get("get_pets") or [])

    products = []
    for item in items:
        s_time = item.get("start_time")
        e_time = item.get("end_time")

        if s_time and e_time:
            if int(s_time) <= now_ms < int(e_time):
                products.append(_build_product(item))
        else:
            products.append(_build_product(item))

    return {
        "title": activity.get("name", "远行商人"),
        "subtitle": activity.get("start_date", ""),
        "start_time": activity.get("start_time"),
        "end_time": activity.get("end_time"),
        "product_count": len(products),
        "products": products,
    }


def _fetch_merchant_info() -> dict[str, Any]:
    response = requests.get(
        MERCHANT_API_URL,
        headers={"X-API-Key": MERCHANT_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


@router.get("/merchant")
async def get_merchant_info() -> dict[str, Any]:
    if not MERCHANT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MERCHANT_API_KEY 未配置",
        )

    try:
        payload = await anyio.to_thread.run_sync(_fetch_merchant_info)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="远行商人接口调用失败",
        ) from exc

    if payload.get("code", 0) != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=payload.get("message") or "远行商人接口返回异常",
        )

    return _process_merchant_data(payload.get("data") or {})
