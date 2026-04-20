"""
向 PostgreSQL 的 sys_dict 表写入精灵六维种族值字典（dict_type='pokemon_stat'）。

用途：
- ops 后台「性格维护」页面把「加成项 / 削弱项」下拉改为从字典取值，
  需要一份与后端 STAT_KEY_TO_COL 对齐的字典数据。

字典内容（幂等 upsert）：
    hp       -> HP
    phy_atk  -> 物攻
    mag_atk  -> 魔攻
    phy_def  -> 物防
    mag_def  -> 魔防
    spd      -> 速度

用法：
    uv run python scripts/seed_pokemon_stat_dict.py
    uv run python scripts/seed_pokemon_stat_dict.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG


DICT_TYPE = "pokemon_stat"

ROWS: list[tuple[str, str, str, int]] = [
    (DICT_TYPE, "hp",      "HP",  1),
    (DICT_TYPE, "phy_atk", "物攻", 2),
    (DICT_TYPE, "mag_atk", "魔攻", 3),
    (DICT_TYPE, "phy_def", "物防", 4),
    (DICT_TYPE, "mag_def", "魔防", 5),
    (DICT_TYPE, "spd",     "速度", 6),
]


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="写入 pokemon_stat 字典到 PG.sys_dict")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    args = parser.parse_args()

    total = time.time()
    print("=" * 60)
    print(f"  seed sys_dict: dict_type={DICT_TYPE}, rows={len(ROWS)}")
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
                ROWS,
            )
        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚，未写入 ({time.time()-total:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 已提交 {len(ROWS)} 条 ({time.time()-total:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
