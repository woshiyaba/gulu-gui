"""洛克王国（lkgc）小程序云函数请求封装。"""

import json
from typing import Any, Dict, List, Optional

import requests

from common.utils.sha256 import (
    canonical_body,
    current_timestamp_ms,
    generate_authorization,
)

# =========================================
# 配置
# =========================================

ACCESS_KEY = "Y8OQpKSpRYnjPAYB"
SECRET_KEY = "E8KwT8Rb9UgiFhur"

ENV_ID = "env-00jxhb62nv6n"
FUNCTION_NAME = "m-pet-co"
APP_ID = "2021004147646503"

URL = f"https://{ENV_ID}.api-hz.cloudbasefunction.cn/functions/invokeFunction"
PATH = "/functions/invokeFunction"

UNI_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI2OWQ1ZjVkZDM5OTMzMmIyYTQ1NGY1Y2YiLCJyb2xlIjpbXSwicGVybWlzc2lvbiI6W10sInVuaUlkVmVyc2lvbiI6IjEuMC4xOCIsImlhdCI6MTc3OTE3MjEzOSwiZXhwIjoxNzc5Nzc2OTM5fQ.3sPjYSdq3jks_P99wO3JwnFhivitQPIgvMy0maImPy8")

CLIENT_INFO: Dict[str, Any] = {
    "PLATFORM": "mp-weixin",
    "OS": "ios",
    "APPID": "__UNI__A807A48",
    "DEVICEID": "17784311178584987447",
    "scene": 1106,
    "appName": "rcgd-m",
    "appId": "__UNI__A807A48",
    "appVersion": "1.0.25",
    "appVersionCode": "1025",
    "appLanguage": "zh-Hans",
    "hostVersion": "8.0.71",
    "hostName": "WeChat",
    "uniPlatform": "mp-weixin",
    "uniCompilerVersion": "4.87",
    "uniRuntimeVersion": "4.87",
    "deviceId": "17784311178584987447",
    "deviceType": "phone",
    "deviceBrand": "iphone",
    "deviceModel": "iPhone 17<iPhone18,3>",
    "osName": "ios",
    "osVersion": "26.4.2",
    "locale": "zh-Hans",
    "LOCALE": "zh-Hans",
}


# =========================================
# 内部工具
# =========================================

def _build_body(method: str, params: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "method": method,
        "params": params,
        "clientInfo": CLIENT_INFO,
        "uniIdToken": UNI_TOKEN,
    }


def _build_headers(timestamp: str) -> Dict[str, str]:
    return {
        "content-type": "application/json",
        "x-client-timestamp": timestamp,
        "x-from-instance-id": timestamp,
        "x-from-env-id": ENV_ID,
        "x-from-function-name": FUNCTION_NAME,
        "x-from-app-id": APP_ID,
        "x-to-env-id": ENV_ID,
        "x-to-function-name": FUNCTION_NAME,
    }


def invoke(method: str, params: List[Dict[str, Any]], timeout: int = 20) -> Optional[Dict[str, Any]]:
    """统一的云函数调用入口：构造 body、签名、发请求并返回 JSON。"""
    timestamp = current_timestamp_ms()
    body_data = _build_body(method, params)
    body_str = canonical_body(body_data)
    headers = _build_headers(timestamp)

    headers["Authorization"] = generate_authorization(
        method="POST",
        path=PATH,
        query="",
        body=body_data,
        headers=headers,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        timestamp=timestamp,
    )

    response = requests.post(URL, headers=headers, data=body_str.encode("utf-8"), timeout=timeout)
    try:
        return response.json()
    except ValueError:
        print("[lkgc] 响应非 JSON:", response.status_code, response.text)
        return None


# =========================================
# 业务方法
# =========================================

def fetch_pet_list(
    page: int = 1,
    page_size: int = 12,
    query: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """分页获取宠物列表。"""
    return invoke(
        "getList",
        [{
            "curPage": page,
            "pageSize": page_size,
            "query": query if query is not None else {"is_show_form": False},
        }],
    )


def get_pet_info(pet_id: str) -> Optional[Dict[str, Any]]:
    """获取单只宠物详情。"""
    return invoke("getPetInfo", [{"pet_id": pet_id}])


def fetch_all_pets(
    max_pages: int = 100,
    page_size: int = 12,
    sleep_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """翻页拉取全部宠物列表（遇到空页或失败自动停止）。"""
    import time

    all_data: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        data = fetch_pet_list(page=page, page_size=page_size)
        if not data:
            break
        records = data if isinstance(data, list) else (data.get("data") or {}).get("list") or []
        if not records:
            break
        all_data.extend(records)
        time.sleep(sleep_seconds)
    return all_data


if __name__ == "__main__":
    info = get_pet_info("127-1")
    print(json.dumps(info, ensure_ascii=False, indent=2))
