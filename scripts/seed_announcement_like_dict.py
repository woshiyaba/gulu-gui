"""
向 PostgreSQL sys_dict 写入公告点赞计数初始项。

dict_type=announcement, code=like_count, label=点赞数（字符串）。

执行：
    uv run python scripts/seed_announcement_like_dict.py
    uv run python scripts/seed_announcement_like_dict.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG

DICT_TYPE = "announcement"
CODE = "like_count"
INITIAL_COUNT = "0"


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化公告点赞字典项")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚")
    args = parser.parse_args()

    total = time.time()
    print("=" * 60)
    print(f"  seed sys_dict: dict_type={DICT_TYPE}, code={CODE}, label={INITIAL_COUNT}")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sys_dict (dict_type, code, label, extra, sort_order)
                VALUES (%s, %s, %s, '', 0)
                ON CONFLICT (dict_type, code) DO NOTHING
                """,
                (DICT_TYPE, CODE, INITIAL_COUNT),
            )
        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚 ({time.time() - total:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 已提交 ({time.time() - total:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
