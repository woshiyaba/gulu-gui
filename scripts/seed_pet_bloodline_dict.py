"""
+向 PostgreSQL 的 sys_dict 表写入精灵血脉字典（dict_type='pet_bloodline'）。

用途：
- 从 docs/pets/types.json 提取血脉定义
- name -> code
- localized.zh -> label
- id -> sort_order

执行：
    uv run python scripts/seed_pet_bloodline_dict.py
    uv run python scripts/seed_pet_bloodline_dict.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG


DICT_TYPE = "pet_bloodline"
TYPES_JSON_PATH = Path(__file__).resolve().parent.parent / "docs" / "pets" / "types.json"


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def load_rows() -> list[tuple[str, str, str, int]]:
    raw = json.loads(TYPES_JSON_PATH.read_text(encoding="utf-8"))

    rows: list[tuple[str, str, str, int]] = []
    for item in raw:
        code = str(item["name"]).strip()
        label = str(item.get("localized", {}).get("zh", "")).strip()
        sort_order = int(item["id"])

        if not code:
            raise ValueError(f"发现空 name: {item}")
        if not label:
            raise ValueError(f"发现空 localized.zh: {item}")

        rows.append((DICT_TYPE, code, label, sort_order))

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="写入 pet_bloodline 字典到 PG.sys_dict")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    args = parser.parse_args()

    total = time.time()
    rows = load_rows()

    print("=" * 60)
    print(f"  seed sys_dict: dict_type={DICT_TYPE}, rows={len(rows)}")
    print(f"  source: {TYPES_JSON_PATH}")
    print("=" * 60)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO sys_dict (dict_type, code, label, sort_order)
                VALUES %s
                ON CONFLICT (dict_type, code) DO UPDATE
                SET label = EXCLUDED.label,
                    sort_order = EXCLUDED.sort_order
                """,
                rows,
            )
        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚，未写入 ({time.time()-total:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 已提交 {len(rows)} 条 ({time.time()-total:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
