"""
在 PostgreSQL 中创建精灵阵容系统相关表。

当前只创建：
- pokemon_lineup
- pokemon_lineup_member

用法：
    uv run python scripts/create_pokemon_lineup_tables.py
    uv run python scripts/create_pokemon_lineup_tables.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG

LINEUP_TYPE_DICT = "pokemon_lineup_type"
LINEUP_TYPE_ROWS = [
    (LINEUP_TYPE_DICT, "shining_contest", "闪耀大赛", 1),
    (LINEUP_TYPE_DICT, "open_battle", "露天对战", 2),
    (LINEUP_TYPE_DICT, "season_battle", "赛季对战", 3),
    (LINEUP_TYPE_DICT, "starlight_duel", "星光对决", 4),
]


PG_DDL = """
DROP TABLE IF EXISTS pokemon_lineup_member CASCADE;
DROP TABLE IF EXISTS pokemon_lineup CASCADE;

CREATE TABLE IF NOT EXISTS pokemon_lineup (
    id            SERIAL       PRIMARY KEY,
    title         VARCHAR(100) NOT NULL DEFAULT '',
    lineup_desc   TEXT         NOT NULL DEFAULT '',
    source_type   VARCHAR(30)  NOT NULL DEFAULT '',
    sort_order    INT          NOT NULL DEFAULT 0,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pokemon_lineup_member (
    id                SERIAL PRIMARY KEY,
    lineup_id         INT    NOT NULL REFERENCES pokemon_lineup(id) ON DELETE CASCADE,
    sort_order        INT    NOT NULL DEFAULT 1,
    pokemon_id        INT    NOT NULL REFERENCES pokemon(id),
    bloodline_dict_id INT    REFERENCES sys_dict(id),
    personality_id    SMALLINT REFERENCES personality(id),
    qual_1           VARCHAR(20) NOT NULL DEFAULT '',
    qual_2           VARCHAR(20) NOT NULL DEFAULT '',
    qual_3           VARCHAR(20) NOT NULL DEFAULT '',
    skill_1_id        INT REFERENCES skill(id),
    skill_2_id        INT REFERENCES skill(id),
    skill_3_id        INT REFERENCES skill(id),
    skill_4_id        INT REFERENCES skill(id),
    member_desc       TEXT NOT NULL DEFAULT '',
    CONSTRAINT uk_pokemon_lineup_member_order UNIQUE (lineup_id, sort_order)
);
"""

DICT_DELETE_SQL = "DELETE FROM sys_dict WHERE dict_type = %s"

DICT_UPSERT_SQL = """
INSERT INTO sys_dict (dict_type, code, label, sort_order)
VALUES (%s, %s, %s, %s)
ON CONFLICT (dict_type, code) DO UPDATE
SET label = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order
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
    parser = argparse.ArgumentParser(description="在 PostgreSQL 中创建精灵阵容相关表")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正提交")
    args = parser.parse_args()

    total = time.time()

    print("=" * 60)
    print("  create pokemon lineup tables")
    print("  target: PostgreSQL")
    print("  tables: pokemon_lineup, pokemon_lineup_member")
    print(f"  dict seed: {LINEUP_TYPE_DICT} ({len(LINEUP_TYPE_ROWS)} items)")
    print("=" * 60)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(PG_DDL)
            cur.execute(DICT_DELETE_SQL, (LINEUP_TYPE_DICT,))
            cur.executemany(DICT_UPSERT_SQL, LINEUP_TYPE_ROWS)

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
