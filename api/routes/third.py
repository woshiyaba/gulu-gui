from datetime import datetime, timedelta, timezone
from typing import Any

import anyio
import requests
from fastapi import APIRouter, HTTPException, status

from config import MERCHANT_API_KEY, MERCHANT_API_URL, MERCHANT_API_URL_BACKUP

router = APIRouter(prefix="/api/third", tags=["third"])

BEIJING_TZ = timezone(timedelta(hours=8))

# 远行商人结果内存缓存：过期时间取「数据时间边界」与「最长 TTL」的较小值
_CACHE_MAX_TTL_MS = 5 * 60 * 1000  # 最长缓存 5 分钟
_CACHE_MIN_TTL_MS = 30 * 1000  # 最短缓存 30 秒，避免临界点频繁刷新
_merchant_cache: dict[str, Any] = {"result": None, "expire_ms": 0}
_merchant_cache_lock = anyio.Lock()


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


def _compute_expire_ms(result: dict[str, Any], now_ms: int) -> int:
    """根据数据自身的时间边界计算缓存过期时间，并用最长/最短 TTL 收敛。"""
    boundaries: list[int] = []
    end = result.get("end_time")
    if end:
        boundaries.append(int(end))
    for product in result.get("products", []):
        for key in ("start_time", "end_time"):
            ts = product.get(key)
            if ts and int(ts) > now_ms:
                boundaries.append(int(ts))

    ttl_cap = now_ms + _CACHE_MAX_TTL_MS
    future = [b for b in boundaries if b > now_ms]
    expire = min(min(future), ttl_cap) if future else ttl_cap
    # 距离边界过近时兜底一个最短 TTL，避免临界点反复回源
    return max(expire, now_ms + _CACHE_MIN_TTL_MS)


async def _resolve_merchant_info() -> dict[str, Any]:
    """优先主接口，主接口异常 / 非 0 code / 无商品时回退到备用接口。"""
    result = await _try_primary_merchant()
    if result.get("products"):
        return result

    backup_result = await _try_backup_merchant()
    if backup_result.get("products"):
        return backup_result

    return {}


@router.get("/merchant")
async def get_merchant_info() -> dict[str, Any]:
    now_ms = int(datetime.now(tz=BEIJING_TZ).timestamp() * 1000)

    cached = _merchant_cache["result"]
    if cached is not None and now_ms < _merchant_cache["expire_ms"]:
        return cached

    async with _merchant_cache_lock:
        # 等锁期间可能已被其他请求刷新，二次校验避免重复回源
        now_ms = int(datetime.now(tz=BEIJING_TZ).timestamp() * 1000)
        cached = _merchant_cache["result"]
        if cached is not None and now_ms < _merchant_cache["expire_ms"]:
            return cached

        result = await _resolve_merchant_info()
        if not result.get("products"):
            # 两个接口都拿不到数据时不缓存，直接报错
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="远行商人接口暂无数据",
            )

        _merchant_cache["result"] = result
        _merchant_cache["expire_ms"] = _compute_expire_ms(result, now_ms)
        return result
