"""
从 docs/fruit/list_* 导入果实数据到 PostgreSQL 的 pokemon_fruit。

字段映射：
- id -> source_id
- name -> name
- icon -> icon
- related_pet_id -> pokemon_source_id
- item_quality -> item_quality

用法：
    uv run python scripts/import_pokemon_fruit.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PG_CONFIG

ROOT = Path(__file__).resolve().parent.parent
FRUIT_DIR = ROOT / "docs" / "fruit"

DDL = """
CREATE TABLE IF NOT EXISTS pokemon_fruit (
    id                SERIAL PRIMARY KEY,
    source_id         BIGINT       NOT NULL,
    name              VARCHAR(100) NOT NULL DEFAULT '',
    icon              VARCHAR(500) NOT NULL DEFAULT '',
    pokemon_source_id BIGINT,
    item_quality      SMALLINT     NOT NULL DEFAULT 0,
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_pf_source_id UNIQUE (source_id)
);

CREATE INDEX IF NOT EXISTS idx_pf_pokemon_source_id ON pokemon_fruit (pokemon_source_id);
CREATE INDEX IF NOT EXISTS idx_pf_item_quality ON pokemon_fruit (item_quality);
CREATE INDEX IF NOT EXISTS idx_pf_name ON pokemon_fruit (name);
"""


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _load_one_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ((payload.get("result") or {}).get("list")) or []


def _load_all_rows() -> tuple[list[dict[str, Any]], list[str]]:
    files = sorted(FRUIT_DIR.glob("list_*"))
    if not files:
        raise FileNotFoundError(f"未找到果实数据文件：{FRUIT_DIR}/list_*")

    merged_by_source_id: dict[int, dict[str, Any]] = {}
    warnings: list[str] = []

    for file_path in files:
        items = _load_one_file(file_path)
        for item in items:
            source_id = _to_int(item.get("id"))
            if source_id is None:
                warnings.append(f"[warn] 文件 {file_path.name} 存在无效 id，已跳过：{item!r}")
                continue

            merged_by_source_id[source_id] = {
                "source_id": source_id,
                "name": str(item.get("name") or "").strip(),
                "icon": str(item.get("icon") or "").strip(),
                "pokemon_source_id": _to_int(item.get("related_pet_id")),
                "item_quality": _to_int(item.get("item_quality")) or 0,
            }

    rows = [merged_by_source_id[k] for k in sorted(merged_by_source_id.keys())]
    return rows, warnings


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def main() -> None:
    rows, warnings = _load_all_rows()
    if not rows:
        raise SystemExit("未解析到有效果实数据")

    conn = _pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.executemany(
                """
                INSERT INTO pokemon_fruit (
                    source_id, name, icon, pokemon_source_id, item_quality
                ) VALUES (
                    %(source_id)s, %(name)s, %(icon)s, %(pokemon_source_id)s, %(item_quality)s
                )
                ON CONFLICT (source_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    icon = EXCLUDED.icon,
                    pokemon_source_id = EXCLUDED.pokemon_source_id,
                    item_quality = EXCLUDED.item_quality,
                    updated_at = NOW()
                """,
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    print(f"[import_pokemon_fruit] 已写入/更新 {len(rows)} 条记录，来源目录：{FRUIT_DIR}")
    for warning in warnings:
        print(warning, file=sys.stderr)


if __name__ == "__main__":
    main()

