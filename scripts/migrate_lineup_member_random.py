"""
将 pokemon_lineup_member 升级为：具体精灵 (pokemon_id) 与随机精灵 (random_pk_dict_id) 二选一。

- 使用 config.PG_CONFIG 连接 PostgreSQL（与 .env 一致）。
- 旧数据：已有行均为「有 pokemon_id、无 random」，迁移后仍合法，无需 UPDATE。

执行：
    uv run python scripts/migrate_lineup_member_random.py
    uv run python scripts/migrate_lineup_member_random.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG

MIGRATION_SQL = """
ALTER TABLE pokemon_lineup_member
  ALTER COLUMN pokemon_id DROP NOT NULL;

ALTER TABLE pokemon_lineup_member
  ADD COLUMN IF NOT EXISTS random_pk_dict_id INTEGER REFERENCES sys_dict(id);

ALTER TABLE pokemon_lineup_member
  DROP CONSTRAINT IF EXISTS chk_lineup_member_pokemon_or_random;

ALTER TABLE pokemon_lineup_member
  ADD CONSTRAINT chk_lineup_member_pokemon_or_random CHECK (
    (pokemon_id IS NOT NULL AND random_pk_dict_id IS NULL)
    OR (pokemon_id IS NULL AND random_pk_dict_id IS NOT NULL)
  );
"""


def pg_conn():
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def run_migration(*, dry_run: bool) -> None:
    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for stmt in MIGRATION_SQL.split(";"):
                s = stmt.strip()
                if not s:
                    continue
                print(f"执行: {s[:80]}{'...' if len(s) > 80 else ''}")
                cur.execute(s)
        if dry_run:
            conn.rollback()
            print("\n[--dry-run] 已回滚，未提交。")
        else:
            conn.commit()
            print("\n迁移已提交。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="pokemon_lineup_member 支持随机精灵成员")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="在同一事务中执行后回滚，不写库",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
