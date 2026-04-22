"""
为 sys_dict 表添加 extra 列，并更新 pokemon_lineup_type 的展示模式。

用法：
    uv run python scripts/alter_sys_dict_add_extra.py
    uv run python scripts/alter_sys_dict_add_extra.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG

ALTER_SQL = """
ALTER TABLE sys_dict ADD COLUMN IF NOT EXISTS extra VARCHAR(100) NOT NULL DEFAULT '';
"""

LINEUP_TYPE_EXTRA = [
    ("single", "pokemon_lineup_type", "starlight_duel"),
    ("multi",  "pokemon_lineup_type", "shining_contest"),
    ("single", "pokemon_lineup_type", "open_battle"),
    ("single", "pokemon_lineup_type", "season_battle"),
]

UPDATE_EXTRA_SQL = """
UPDATE sys_dict SET extra = %s WHERE dict_type = %s AND code = %s
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
    parser = argparse.ArgumentParser(description="sys_dict 添加 extra 列")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正提交")
    args = parser.parse_args()

    total = time.time()

    print("=" * 60)
    print("  alter sys_dict: add extra column")
    print("  update pokemon_lineup_type extra values")
    print("=" * 60)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(ALTER_SQL)
            cur.executemany(UPDATE_EXTRA_SQL, LINEUP_TYPE_EXTRA)

        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚 ({time.time() - total:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 迁移完成 ({time.time() - total:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
