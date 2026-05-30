from datetime import datetime, timedelta, timezone
from typing import Any

import anyio
import requests
from fastapi import APIRouter, HTTPException, status

from config import MERCHANT_API_KEY, MERCHANT_API_URL, MERCHANT_API_URL_BACKUP

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


def _build_backup_product(item: dict[str, Any]) -> dict[str, Any]:
    # 备用接口的时间戳为秒级，统一转换成毫秒以保持返回结构一致
    s_int = item.get("sxtime_int")
    e_int = item.get("extime_int")
    s_time = int(s_int) * 1000 if s_int else None
    e_time = int(e_int) * 1000 if e_int else None

    category = item.get("djcategory") or {}
    name = category.get("name", "未知")
    icon = (category.get("pic_file") or {}).get("path", "") or ""

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


def _process_backup_data(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}

    now_ms = int(datetime.now(tz=BEIJING_TZ).timestamp() * 1000)
    items = data.get("data") or []

    products = []
    for item in items:
        product = _build_backup_product(item)
        s_time = product["start_time"]
        e_time = product["end_time"]

        if s_time and e_time:
            if int(s_time) <= now_ms < int(e_time):
                products.append(product)
        else:
            products.append(product)

    if not products:
        return {}

    return {
        "title": "远行商人",
        "subtitle": "",
        "start_time": None,
        "end_time": None,
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


def _fetch_merchant_info_backup() -> dict[str, Any]:
    response = requests.get(MERCHANT_API_URL_BACKUP, timeout=10)
    response.raise_for_status()
    return response.json()


async def _try_primary_merchant() -> dict[str, Any]:
    """调用主接口，失败或返回异常时返回空结果（不抛错，交由备用接口兜底）。"""
    if not MERCHANT_API_KEY:
        return {}

    try:
        payload = await anyio.to_thread.run_sync(_fetch_merchant_info)
    except requests.RequestException:
        return {}

    if payload.get("code", 0) != 0:
        return {}

    return _process_merchant_data(payload.get("data") or {})


async def _try_backup_merchant() -> dict[str, Any]:
    """调用备用接口，失败或返回异常时返回空结果。"""
    try:
        payload = await anyio.to_thread.run_sync(_fetch_merchant_info_backup)
    except requests.RequestException:
        return {}

    if payload.get("code", 0) != 0:
        return {}

    return _process_backup_data(payload.get("data") or {})


@router.get("/merchant")
async def get_merchant_info() -> dict[str, Any]:
    # 优先主接口，主接口异常 / 非 0 code / 无商品时回退到备用接口
    result = await _try_primary_merchant()
    if result.get("products"):
        return result

    backup_result = await _try_backup_merchant()
    if backup_result.get("products"):
        return backup_result

    # 两个接口都拿不到数据时才报错
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="远行商人接口暂无数据",
    )
