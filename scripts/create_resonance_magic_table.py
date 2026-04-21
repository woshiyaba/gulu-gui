"""
在 PostgreSQL 中创建共鸣魔法表。

用法：
    uv run python scripts/create_resonance_magic_table.py
    uv run python scripts/create_resonance_magic_table.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG


PG_DDL = """
DROP TABLE IF EXISTS resonance_magic CASCADE;

CREATE TABLE IF NOT EXISTS resonance_magic (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL UNIQUE,
    description     TEXT,
    max_usage_count INT             NOT NULL DEFAULT 1,
    icon            VARCHAR(255)    NOT NULL DEFAULT '',
    sort_order      INT             NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);
"""


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="在 PostgreSQL 中创建共鸣魔法表")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正提交")
    args = parser.parse_args()

    total = time.time()

    print("=" * 60)
    print("  create resonance magic table")
    print("  target: PostgreSQL")
    print("  table: resonance_magic")
    print("=" * 60)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(PG_DDL)

        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚，未提交建表 ({time.time() - total:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 建表完成 ({time.time() - total:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
