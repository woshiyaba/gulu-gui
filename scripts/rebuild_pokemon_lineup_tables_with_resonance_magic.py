"""
备份精灵阵容数据，重建表结构，并补上共鸣魔法字段。

执行步骤：
1. 读取旧表 `pokemon_lineup` / `pokemon_lineup_member` 数据
2. 将备份落盘为 JSON 文件
3. DROP 旧表并按新结构重建
4. 回填旧数据（`resonance_magic_id` 统一回填为 NULL）
5. 修正自增序列

用法：
    uv run python scripts/rebuild_pokemon_lineup_tables_with_resonance_magic.py
    uv run python scripts/rebuild_pokemon_lineup_tables_with_resonance_magic.py --dry-run
    uv run python scripts/rebuild_pokemon_lineup_tables_with_resonance_magic.py --backup-dir scripts/backups
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

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
    id                 SERIAL       PRIMARY KEY,
    title              VARCHAR(100) NOT NULL DEFAULT '',
    lineup_desc        TEXT         NOT NULL DEFAULT '',
    source_type        VARCHAR(30)  NOT NULL DEFAULT '',
    resonance_magic_id INT          REFERENCES resonance_magic(id),
    sort_order         INT          NOT NULL DEFAULT 0,
    is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pokemon_lineup_member (
    id                SERIAL PRIMARY KEY,
    lineup_id         INT    NOT NULL REFERENCES pokemon_lineup(id) ON DELETE CASCADE,
    sort_order        INT    NOT NULL DEFAULT 1,
    pokemon_id        INT    NOT NULL REFERENCES pokemon(id),
    bloodline_dict_id INT    REFERENCES sys_dict(id),
    personality_id    SMALLINT REFERENCES personality(id),
    qual_1            VARCHAR(20) NOT NULL DEFAULT '',
    qual_2            VARCHAR(20) NOT NULL DEFAULT '',
    qual_3            VARCHAR(20) NOT NULL DEFAULT '',
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


def json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table_name,))
    row = cur.fetchone() or {}
    return bool(row.get("exists"))


def column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        ) AS exists
        """,
        (table_name, column_name),
    )
    row = cur.fetchone() or {}
    return bool(row.get("exists"))


def fetch_backup(cur) -> dict:
    lineups: list[dict] = []
    members: list[dict] = []

    if table_exists(cur, "pokemon_lineup"):
        has_resonance_magic_id = column_exists(cur, "pokemon_lineup", "resonance_magic_id")
        cur.execute(
            f"""
            SELECT
                id,
                title,
                lineup_desc,
                source_type,
                {'resonance_magic_id,' if has_resonance_magic_id else 'NULL AS resonance_magic_id,'}
                sort_order,
                is_active,
                created_at,
                updated_at
            FROM pokemon_lineup
            ORDER BY id
            """
        )
        lineups = cur.fetchall()

    if table_exists(cur, "pokemon_lineup_member"):
        cur.execute(
            """
            SELECT
                id, lineup_id, sort_order, pokemon_id, bloodline_dict_id, personality_id,
                qual_1, qual_2, qual_3, skill_1_id, skill_2_id, skill_3_id, skill_4_id, member_desc
            FROM pokemon_lineup_member
            ORDER BY id
            """
        )
        members = cur.fetchall()

    return {
        "backup_at": datetime.now().isoformat(),
        "lineups": lineups,
        "members": members,
    }


def write_backup_file(backup: dict, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pokemon_lineup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = backup_dir / filename
    backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    return backup_path


def restore_backup(cur, backup: dict) -> None:
    for lineup in backup.get("lineups", []):
        cur.execute(
            """
            INSERT INTO pokemon_lineup (
                id, title, lineup_desc, source_type, resonance_magic_id, sort_order, is_active, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                lineup["id"],
                lineup.get("title", ""),
                lineup.get("lineup_desc", ""),
                lineup.get("source_type", ""),
                lineup.get("resonance_magic_id"),
                lineup.get("sort_order", 0),
                lineup.get("is_active", True),
                lineup.get("created_at"),
                lineup.get("updated_at"),
            ),
        )

    for member in backup.get("members", []):
        cur.execute(
            """
            INSERT INTO pokemon_lineup_member (
                id, lineup_id, sort_order, pokemon_id, bloodline_dict_id, personality_id,
                qual_1, qual_2, qual_3, skill_1_id, skill_2_id, skill_3_id, skill_4_id, member_desc
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                member["id"],
                member["lineup_id"],
                member.get("sort_order", 1),
                member["pokemon_id"],
                member.get("bloodline_dict_id"),
                member.get("personality_id"),
                member.get("qual_1", ""),
                member.get("qual_2", ""),
                member.get("qual_3", ""),
                member.get("skill_1_id"),
                member.get("skill_2_id"),
                member.get("skill_3_id"),
                member.get("skill_4_id"),
                member.get("member_desc", ""),
            ),
        )


def reset_sequences(cur) -> None:
    cur.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('pokemon_lineup', 'id'),
            COALESCE((SELECT MAX(id) FROM pokemon_lineup), 1),
            (SELECT COUNT(*) > 0 FROM pokemon_lineup)
        )
        """
    )
    cur.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('pokemon_lineup_member', 'id'),
            COALESCE((SELECT MAX(id) FROM pokemon_lineup_member), 1),
            (SELECT COUNT(*) > 0 FROM pokemon_lineup_member)
        )
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="备份并重建精灵阵容表，新增共鸣魔法字段")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚数据库变更")
    parser.add_argument(
        "--backup-dir",
        default=str(Path(__file__).resolve().parent / "backups"),
        help="JSON 备份文件输出目录",
    )
    args = parser.parse_args()

    started_at = time.time()
    backup_dir = Path(args.backup_dir).resolve()

    print("=" * 72)
    print("  rebuild pokemon lineup tables with resonance magic")
    print("  target: PostgreSQL")
    print(f"  backup dir: {backup_dir}")
    print("  steps: backup -> rebuild -> restore")
    print("=" * 72)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            backup = fetch_backup(cur)
            backup_path = write_backup_file(backup, backup_dir)
            print(f"[backup] lineups={len(backup['lineups'])}, members={len(backup['members'])}")
            print(f"[backup] file={backup_path}")

            cur.execute(PG_DDL)
            cur.execute(DICT_DELETE_SQL, (LINEUP_TYPE_DICT,))
            cur.executemany(DICT_UPSERT_SQL, LINEUP_TYPE_ROWS)
            restore_backup(cur, backup)
            reset_sequences(cur)

        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 数据库已回滚，备份文件已保留 ({time.time() - started_at:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 阵容表重建并回填完成 ({time.time() - started_at:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
