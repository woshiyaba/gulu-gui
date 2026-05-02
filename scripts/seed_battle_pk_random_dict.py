"""
向 PostgreSQL sys_dict 写入阵容 PK「随机精灵」选项（dict_type=battle_pk_random_pokemon）。

- 一条「随机精灵」：全库随机意向，extra.kind=any，不默认血脉。
- 各系一条「随机某系精灵」：extra.kind=attr + bloodline_code（与 pet_bloodline / types.json 的 name 一致），用于前端默认血脉。

执行：
    uv run python scripts/seed_battle_pk_random_dict.py
    uv run python scripts/seed_battle_pk_random_dict.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG

DICT_TYPE = "battle_pk_random_pokemon"
TYPES_JSON_PATH = Path(__file__).resolve().parent.parent / "docs" / "pets" / "types.json"


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def load_rows() -> list[tuple[str, str, str, str, int]]:
    raw = json.loads(TYPES_JSON_PATH.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str, str, int]] = []

    rows.append(
        (
            DICT_TYPE,
            "any",
            "随机精灵",
            '{"k":"a"}',
            0,
        )
    )

    sort_base = 10
    for i, item in enumerate(raw):
        code_name = str(item["name"]).strip()
        zh = str(item.get("localized", {}).get("zh", "")).strip()
        if not code_name or not zh:
            raise ValueError(f"类型数据不完整: {item}")
        code = f"t_{code_name}"[:30]
        label = f"随机{zh}系精灵"
        extra = json.dumps({"k": "t", "c": code_name}, ensure_ascii=False)
        if len(extra) > 100:
            raise ValueError(f"extra 超长: {extra}")
        rows.append((DICT_TYPE, code, label, extra, sort_base + i))

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="写入 battle_pk_random_pokemon 字典")
    parser.add_argument("--dry-run", action="store_true", help="回滚，不提交")
    args = parser.parse_args()

    t0 = time.time()
    rows = load_rows()

    print("=" * 60)
    print(f"  seed sys_dict: dict_type={DICT_TYPE}, rows={len(rows)}")
    print(f"  source: {TYPES_JSON_PATH}")
    print("=" * 60)

    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO sys_dict (dict_type, code, label, extra, sort_order)
                VALUES %s
                ON CONFLICT (dict_type, code) DO UPDATE
                SET label = EXCLUDED.label,
                    extra = EXCLUDED.extra,
                    sort_order = EXCLUDED.sort_order
                """,
                rows,
            )
        if args.dry_run:
            conn.rollback()
            print(f"\n[dry-run] 已回滚 ({time.time() - t0:.2f}s)")
        else:
            conn.commit()
            print(f"\n[commit] 已提交 {len(rows)} 条 ({time.time() - t0:.2f}s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
