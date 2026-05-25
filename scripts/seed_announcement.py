"""
将当前前台硬编码的公告整合进公告管理表 site_announcement。

内容与 front/pc-front/src/data/announcement.ts、docs/公告/公告.txt 保持一致，
写入后默认设置为不可用（is_active=False），前台不会展示。

注意：site_announcement 只有 title / content 文本字段，没有图片列，
故 notice.png 配图不会迁移，仅迁移标题与正文文本。

执行：
    uv run python scripts/seed_announcement.py
    uv run python scripts/seed_announcement.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from config import PG_CONFIG

TITLE = "公告"
CONTENT = "官方公告毫无诚意，立刻回退版本，打开S2版本退款通道，清理涉事员工和管理人员。"
IS_ACTIVE = False

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS site_announcement (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="整合当前公告到 site_announcement（默认禁用）")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚")
    args = parser.parse_args()

    total = time.time()
    print("=" * 60)
    print(f"  seed site_announcement: title={TITLE!r}, is_active={IS_ACTIVE}")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(TABLE_SQL)
            cur.execute("SELECT id FROM site_announcement ORDER BY id LIMIT 1")
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """
                    INSERT INTO site_announcement (title, content, is_active)
                    VALUES (%s, %s, %s)
                    """,
                    (TITLE, CONTENT, IS_ACTIVE),
                )
                print("[insert] 新建公告配置行")
            else:
                cur.execute(
                    """
                    UPDATE site_announcement
                    SET title = %s, content = %s, is_active = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (TITLE, CONTENT, IS_ACTIVE, row[0]),
                )
                print(f"[update] 更新公告配置行 id={row[0]}")

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
