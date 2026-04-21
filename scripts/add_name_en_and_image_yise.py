"""
为 PostgreSQL pokemon 表添加 name_en 和 image_yise 字段并填充数据。

1. name_en: 从 image_lc 字段提取，如 JL_banbanke_tuipi.webp → banbanke_tuipi
2. image_yise: 读取 yise.txt，解析文件名中的 name 部分（去掉 _yise 后缀），
   通过 name_en 匹配宠物，写入 /yise/friends/JL_xxx_yise.webp

用法：
    uv run python scripts/add_name_en_and_image_yise.py
    uv run python scripts/add_name_en_and_image_yise.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG

YISE_TXT_PATH = Path(__file__).resolve().parent.parent / "docs" / "pets" / "yise.txt"


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def _ensure_column(cur, column_name: str, column_type: str, default: str) -> None:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.columns
        WHERE table_name = 'pokemon'
          AND column_name = %s
        """,
        (column_name,),
    )
    row = cur.fetchone()
    if row[0] == 0:
        cur.execute(
            f"ALTER TABLE pokemon ADD COLUMN {column_name} {column_type} NOT NULL DEFAULT {default}"
        )
        print(f"[migrate] pokemon.{column_name} 列已添加")


def _extract_name_en(image_lc: str) -> str | None:
    m = re.match(r"^JL_(.+)\.webp$", image_lc)
    if not m:
        return None
    return m.group(1)


def _parse_yise_file(path: Path) -> dict[str, str]:
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^JL_(.+)_yise\.webp$", line)
            if m:
                mapping[m.group(1)] = line
            else:
                print(f"[warn] yise.txt 无法解析行: {line}")
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="添加 name_en 和 image_yise 字段（PostgreSQL）")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写库")
    args = parser.parse_args()

    if not YISE_TXT_PATH.is_file():
        print(f"[error] 文件不存在: {YISE_TXT_PATH}")
        sys.exit(1)

    yise_map = _parse_yise_file(YISE_TXT_PATH)
    print(f"[info] 从 yise.txt 解析到 {len(yise_map)} 条异色记录")

    conn = pg_conn()
    try:
        cur = conn.cursor()

        if not args.dry_run:
            _ensure_column(cur, "name_en", "VARCHAR(255)", "''")
            _ensure_column(cur, "image_yise", "VARCHAR(255)", "''")
            conn.commit()

        cur.execute("SELECT id, name, image_lc FROM pokemon WHERE image_lc != ''")
        rows = cur.fetchall()

        name_en_updated = 0
        yise_updated = 0
        yise_matched_keys = set()

        for row in rows:
            pid, pname, image_lc = row[0], row[1], row[2]
            name_en = _extract_name_en(image_lc)

            if not name_en:
                print(f"[skip] id={pid} name={pname!r} image_lc={image_lc!r} 无法提取 name_en")
                continue

            if args.dry_run:
                print(f"[dry-run] id={pid} name={pname!r} -> name_en={name_en!r}")
            else:
                cur.execute(
                    "UPDATE pokemon SET name_en = %s WHERE id = %s",
                    (name_en, pid),
                )
            name_en_updated += 1

            yise_filename = yise_map.get(name_en)
            if yise_filename:
                image_yise = f"/yise/friends/{yise_filename}"
                if args.dry_run:
                    print(f"  [dry-run] -> image_yise={image_yise!r}")
                else:
                    cur.execute(
                        "UPDATE pokemon SET image_yise = %s WHERE id = %s",
                        (image_yise, pid),
                    )
                yise_updated += 1
                yise_matched_keys.add(name_en)

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

        unmatched = set(yise_map.keys()) - yise_matched_keys
        if unmatched:
            print(f"\n[info] 以下 {len(unmatched)} 条异色记录未匹配到宠物:")
            for key in sorted(unmatched):
                print(f"  {key} -> {yise_map[key]}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(
        f"\n[summary] name_en更新={name_en_updated} "
        f"image_yise更新={yise_updated} "
        f"dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()
