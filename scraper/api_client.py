import requests
from config import BASE_URL

# 超时设置：连接 10s，读取 60s（数据量大）
_TIMEOUT = (10, 60)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; lkwg-spider/1.0)",
    "Referer": BASE_URL,
}


def _get(path: str) -> dict | list:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_pokemon() -> list[dict]:
    """返回精灵列表，字段：no/name/image/attributes/attrNames/type/typeName/form/formName/detailUrl"""
    data = _get("/api/pokemon")
    return data.get("pokemon", [])


def fetch_details() -> dict:
    """返回以精灵名为 key 的详情字典，包含 stats/trait/restrain/skills。"""
    return _get("/api/details")


def fetch_skills() -> dict:
    """返回以技能名为 key 的技能字典，包含 name/attr/power/type/consume/desc/icon。"""
    return _get("/api/skills")
