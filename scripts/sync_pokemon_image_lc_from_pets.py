"""
从 Pets.json 同步 pokemon.image_lc：用 localized.zh 拼出与 pokemon.name 一致的查找键，
将根级英文 name 写成 JL_{name}.webp。

用法：
    uv run python scripts/sync_pokemon_image_lc_from_pets.py
    uv run python scripts/sync_pokemon_image_lc_from_pets.py --json-path "E:/path/Pets.json"
    uv run python scripts/sync_pokemon_image_lc_from_pets.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "Pets.json",
)


def _ensure_image_lc_column(cur) -> None:
    """旧库无 image_lc 时 ALTER 追加。"""
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'pokemon'
          AND COLUMN_NAME = 'image_lc'
        """
    )
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            """
            ALTER TABLE pokemon
            ADD COLUMN image_lc VARCHAR(255) NOT NULL DEFAULT ''
            COMMENT '洛克素材侧图片文件名，如 JL_xxx.webp'
            """
        )
        print("[migrate] pokemon.image_lc 列已添加")


def _nonempty_str(v) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s if s else None


def _lookup_name_from_zh(zh: dict) -> str | None:
    """根据 zh 得到与 pokemon.name 对齐的查找名。"""
    base = _nonempty_str(zh.get("name"))
    if not base:
        return None
    suffix = _nonempty_str(zh.get("from")) or _nonempty_str(zh.get("form"))
    if suffix:
        return f"{base}（{suffix}）"
    return base


def _image_lc_value(root_en_name: str) -> str:
    return f"JL_{root_en_name}.webp"


def main() -> None:
    parser = argparse.ArgumentParser(description="从 Pets.json 写入 pokemon.image_lc")
    parser.add_argument(
        "--json-path",
        default=DEFAULT_JSON_PATH,
        help=f"Pets.json 路径（默认: {DEFAULT_JSON_PATH}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将执行的操作，不写库",
    )
    args = parser.parse_args()

    json_path = os.path.abspath(args.json_path)
    if not os.path.isfile(json_path):
        print(f"[error] 文件不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        pets = json.load(f)
    if not isinstance(pets, list):
        print("[error] Pets.json 根应为数组")
        sys.exit(1)

    stats = {
        "processed": 0,
        "updated": 0,
        "skip": 0,
        "miss": 0,
        "ambiguous": 0,
    }

    conn = get_conn()
    try:
        cur = conn.cursor()
        # dry-run 不写库：跳过 ADD COLUMN，避免试跑也改表结构
        if not args.dry_run:
            _ensure_image_lc_column(cur)
            conn.commit()

        for pet in pets:
            stats["processed"] += 1
            if not isinstance(pet, dict):
                stats["skip"] += 1
                print(f"[skip] 非对象条目 index={stats['processed'] - 1}")
                continue

            pet_id = pet.get("id")
            root_en = pet.get("name")
            if not isinstance(root_en, str) or not root_en.strip():
                stats["skip"] += 1
                print(f"[skip] 缺根级 name pet_id={pet_id!r}")
                continue

            zh = pet.get("localized", {}).get("zh")
            if not isinstance(zh, dict):
                stats["skip"] += 1
                print(f"[skip] 无 localized.zh pet_id={pet_id!r} root_name={root_en!r}")
                continue

            lookup_name = _lookup_name_from_zh(zh)
            if not lookup_name:
                stats["skip"] += 1
                print(f"[skip] 无 zh.name pet_id={pet_id!r} root_name={root_en!r}")
                continue

            image_lc = _image_lc_value(root_en.strip())

            cur.execute(
                "SELECT id, name FROM pokemon WHERE name = %s",
                (lookup_name,),
            )
            rows = cur.fetchall()

            if len(rows) == 0:
                stats["miss"] += 1
                print(
                    f"[miss] pet_id={pet_id!r} root_name={root_en!r} "
                    f"lookup_name={lookup_name!r} -> would set image_lc={image_lc!r}"
                )
                continue

            if len(rows) > 1:
                stats["ambiguous"] += 1
                ids = ", ".join(str(r["id"]) for r in rows)
                print(
                    f"[ambiguous] pet_id={pet_id!r} lookup_name={lookup_name!r} "
                    f"rows={len(rows)} ids=[{ids}] -> 跳过，请手动处理"
                )
                continue

            row_id = rows[0]["id"]
            if args.dry_run:
                stats["updated"] += 1
                print(
                    f"[dry-run] id={row_id} name={lookup_name!r} -> image_lc={image_lc!r}"
                )
                continue

            cur.execute(
                "UPDATE pokemon SET image_lc = %s WHERE id = %s",
                (image_lc, row_id),
            )
            stats["updated"] += 1

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(
        "[summary] "
        f"processed={stats['processed']} updated={stats['updated']} "
        f"skip={stats['skip']} miss={stats['miss']} ambiguous={stats['ambiguous']} "
        f"dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()
