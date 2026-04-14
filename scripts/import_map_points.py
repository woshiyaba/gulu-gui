"""
从 docs/pets/maps.json 读取地图点位数据，分析 data 内容后导入 pet_map_point 表。

写库字段：
- map_id      <- mapId（兼容 map_id）
- title       <- title
- latitude    <- latitude
- longitude   <- longitude
- category_id <- category_id
- source_id   <- id（改名，避免占用数据库自增主键）

用法：
    uv run python scripts/import_map_points.py
    uv run python scripts/import_map_points.py --dry-run
"""

import argparse
import json
import os
import sys
from collections import Counter
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "maps.json",
)

DDL = """
CREATE TABLE IF NOT EXISTS pet_map_point (
    id          INT             NOT NULL AUTO_INCREMENT,
    source_id   BIGINT          NOT NULL COMMENT 'maps.json 原始 id，避免占用数据库自增主键',
    map_id      INT             NOT NULL COMMENT '地图 id，优先取 mapId，兼容 map_id',
    title       VARCHAR(100)    NOT NULL DEFAULT '' COMMENT '点位标题',
    latitude    DECIMAL(18, 15) NOT NULL COMMENT '纬度',
    longitude   DECIMAL(18, 15) NOT NULL COMMENT '经度',
    category_id BIGINT          NOT NULL COMMENT '分类 id',
    PRIMARY KEY (id),
    UNIQUE KEY uk_source_id (source_id),
    KEY idx_map_id (map_id),
    KEY idx_category_id (category_id),
    KEY idx_map_category (map_id, category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地图点位数据';
"""

_BATCH = 500


def _load_items() -> list[dict]:
    """读取 maps.json 顶层 data 数组。"""
    with open(JSON_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    items = payload.get("data")
    if not isinstance(items, list):
        raise ValueError("maps.json 顶层 data 不是数组，无法导入")
    return items


def _require_value(item: dict, field_name: str):
    """校验字段存在且非空，避免脏数据悄悄入库。"""
    value = item.get(field_name)
    if value in (None, ""):
        raise ValueError(f"缺少必填字段: {field_name}")
    return value


def _normalize_record(item: dict) -> dict:
    """把来源 JSON 统一映射成数据库字段。"""
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
    """构建入库记录，并检查 source_id 是否重复。"""
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


def _analyze_records(records: list[dict]) -> dict:
    """生成导入前分析信息，方便确认数据整体情况。"""
    map_counter = Counter(row["map_id"] for row in records)
    category_counter = Counter(row["category_id"] for row in records)
    title_counter = Counter((row["map_id"], row["title"]) for row in records)
    duplicate_title_groups = sum(1 for count in title_counter.values() if count > 1)

    return {
        "total": len(records),
        "map_count": len(map_counter),
        "category_count": len(category_counter),
        "top_maps": map_counter.most_common(10),
        "top_categories": category_counter.most_common(10),
        "duplicate_title_groups": duplicate_title_groups,
    }


def _print_analysis(analysis: dict) -> None:
    print(f"[analyze] 总记录数: {analysis['total']}")
    print(f"[analyze] 地图数量: {analysis['map_count']}")
    print(f"[analyze] 分类数量: {analysis['category_count']}")
    print(f"[analyze] 重复标题组数（同 map_id + title）: {analysis['duplicate_title_groups']}")
    print(f"[analyze] 地图分布 Top10: {analysis['top_maps']}")
    print(f"[analyze] 分类分布 Top10: {analysis['top_categories']}")


def _recreate_table(cur) -> None:
    """重建目标表，保证每次导入结果可重复。"""
    cur.execute("DROP TABLE IF EXISTS pet_map_point")
    cur.execute(DDL)
    print("[migrate] pet_map_point 表已重建")


def _batch_insert(cur, records: list[dict]) -> int:
    sql = """
        INSERT INTO pet_map_point (
            source_id, map_id, title, latitude, longitude, category_id
        ) VALUES (
            %(source_id)s, %(map_id)s, %(title)s, %(latitude)s, %(longitude)s, %(category_id)s
        )
    """

    inserted = 0
    for i in range(0, len(records), _BATCH):
        batch = records[i : i + _BATCH]
        cur.executemany(sql, batch)
        inserted += len(batch)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 docs/pets/maps.json 到 pet_map_point 表")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只分析数据，不执行建表和入库",
    )
    args = parser.parse_args()

    items = _load_items()
    records = _build_records(items)
    analysis = _analyze_records(records)
    _print_analysis(analysis)

    if args.dry_run:
        print("[done] dry-run 模式，不执行数据库写入")
        return

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _recreate_table(cur)
            inserted = _batch_insert(cur, records)
        conn.commit()
        print(f"[done] 共导入 {inserted} 条记录到 pet_map_point")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
