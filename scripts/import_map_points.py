"""
从 17173 地图 API 拉取点位数据，导入 PostgreSQL pet_map_point 表。

数据来源：https://map-api.17173.com/map/lkwg/map/4010/point/list
目标表结构见 sql/wikiroco.sql 中的 pet_map_point。

用法：
    uv run python scripts/import_map_points.py
    uv run python scripts/import_map_points.py --dry-run
    uv run python scripts/import_map_points.py --from-file docs/pets/maps.json
"""

import argparse
import json
import os
import sys
from collections import Counter
from decimal import Decimal


import http.client
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PG_CONFIG

API_HOST = "terra-api.17173.com"
API_PATH = "/app/location/list?mapIds=4010"
JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "pets", "maps.json",
)

_BATCH = 500


def _fetch_from_api() -> list[dict]:
    """从 17173 API 拉取数据。"""
    headers = {
        "pragma": "no-cache",
        "priority": "u=1, i",
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Accept": "*/*",
        "Host": API_HOST,
        "Connection": "keep-alive",
    }
    conn = http.client.HTTPSConnection(API_HOST)
    conn.request("GET", API_PATH, "", headers)
    res = conn.getresponse()
    payload = json.loads(res.read().decode("utf-8"))
    conn.close()

    items = payload.get("data")
    if not isinstance(items, list):
        raise ValueError("API 返回的 data 不是数组")
    print(f"[fetch] 从 API 获取到 {len(items)} 条数据")
    return items


def _load_from_file() -> list[dict]:
    """从本地 maps.json 读取数据。"""
    with open(JSON_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    items = payload.get("data")
    if not isinstance(items, list):
        raise ValueError("maps.json 顶层 data 不是数组")
    print(f"[load] 从文件读取到 {len(items)} 条数据")
    return items


def _save_to_file(items: list[dict]) -> None:
    """将拉取的数据保存到本地 maps.json 作为备份。"""
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"code": 200, "message": "操作成功", "data": items}, f, ensure_ascii=False, indent=4)
    print(f"[save] 已保存到 {JSON_PATH}")


def _require_value(item: dict, field_name: str):
    value = item.get(field_name)
    if value in (None, ""):
        raise ValueError(f"缺少必填字段: {field_name}")
    return value


def _normalize_record(item: dict) -> dict:
    """将 API 返回的 JSON 映射为数据库字段。"""
    map_id = item.get("mapId")
    if map_id in (None, ""):
        map_id = _require_value(item, "map_id")

    return {
        "source_id": int(_require_value(item, "id")),
        "map_id": int(map_id),
        "title": str(_require_value(item, "title")).strip(),
        "latitude": Decimal(str(_require_value(item, "latitude"))),
        "longitude": Decimal(str(_require_value(item, "longitude"))),
        "category_id": int(_require_value(item, "category_id")),
    }


def _build_records(items: list[dict]) -> list[dict]:
    records: list[dict] = []
    source_ids: set[int] = set()

    for index, item in enumerate(items, start=1):
        record = _normalize_record(item)
        source_id = record["source_id"]
        if source_id in source_ids:
            raise ValueError(f"第 {index} 条数据 source_id 重复: {source_id}")
        source_ids.add(source_id)
        records.append(record)

    return records


def _print_analysis(records: list[dict]) -> None:
    map_counter = Counter(row["map_id"] for row in records)
    category_counter = Counter(row["category_id"] for row in records)
    print(f"[analyze] 总记录数: {len(records)}")
    print(f"[analyze] 地图数量: {len(map_counter)}")
    print(f"[analyze] 分类数量: {len(category_counter)}")
    print(f"[analyze] 地图分布 Top10: {map_counter.most_common(10)}")
    print(f"[analyze] 分类分布 Top10: {category_counter.most_common(10)}")


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def _truncate_and_insert(conn, records: list[dict]) -> int:
    """清空表后批量插入。"""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE pet_map_point RESTART IDENTITY CASCADE")
        print("[migrate] pet_map_point 已清空")

        sql = """
            INSERT INTO pet_map_point (source_id, map_id, title, latitude, longitude, category_id)
            VALUES %s
        """
        values = [
            (r["source_id"], r["map_id"], r["title"], r["latitude"], r["longitude"], r["category_id"])
            for r in records
        ]
        psycopg2.extras.execute_values(cur, sql, values, page_size=_BATCH)

    conn.commit()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="从 17173 API 拉取地图点位数据并导入 PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="只分析数据，不写库")
    parser.add_argument("--from-file", action="store_true", help="从本地 maps.json 读取，不请求 API")
    args = parser.parse_args()

    if args.from_file:
        items = _load_from_file()
    else:
        items = _fetch_from_api()
        _save_to_file(items)

    records = _build_records(items)
    _print_analysis(records)

    if args.dry_run:
        print("[done] dry-run 模式，不执行数据库写入")
        return

    conn = _pg_conn()
    try:
        inserted = _truncate_and_insert(conn, records)
        print(f"[done] 共导入 {inserted} 条记录到 pet_map_point")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
