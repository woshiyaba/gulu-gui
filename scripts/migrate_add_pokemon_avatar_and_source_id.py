"""
仅针对 PostgreSQL：给 pokemon 表新增两列
- avatar: 精灵头像（字符串路径/文件名）
- source_id: 来源原始 id（用于映射外部数据源 id）

用法：
    uv run python scripts/migrate_add_pokemon_avatar_and_source_id.py
    uv run python scripts/migrate_add_pokemon_avatar_and_source_id.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

from config import PG_CONFIG


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE table_schema = current_schema()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    return cur.fetchone()[0] > 0


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="给 pokemon 表新增 avatar/source_id 两列")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将执行的 SQL，不实际修改数据库",
    )
    args = parser.parse_args()

    alter_sql_list = []

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            if not _column_exists(cur, "pokemon", "avatar"):
                alter_sql_list.append(
                    """
                    ALTER TABLE pokemon
                    ADD COLUMN avatar VARCHAR(255) NOT NULL DEFAULT ''
                    """
                )

            if not _column_exists(cur, "pokemon", "source_id"):
                alter_sql_list.append(
                    """
                    ALTER TABLE pokemon
                    ADD COLUMN source_id BIGINT DEFAULT NULL
                    """
                )

            if not alter_sql_list:
                print("[skip] pokemon.avatar 与 pokemon.source_id 已存在，无需变更")
                return

            for sql in alter_sql_list:
                clean_sql = " ".join(sql.split())
                if args.dry_run:
                    print(f"[dry-run] {clean_sql}")
                    continue
                cur.execute(sql)
                print(f"[ok] {clean_sql}")

        if args.dry_run:
            conn.rollback()
            print("[done] dry-run 完成，未提交任何变更")
        else:
            conn.commit()
            print("[done] 迁移完成并已提交")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
