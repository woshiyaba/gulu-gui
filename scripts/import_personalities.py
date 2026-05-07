"""
从 docs/pets/personalities.json 导入精灵性格字典到 PostgreSQL。

性格规则：
- 每个性格对六维（HP / 物攻 / 魔攻 / 物防 / 魔防 / 速度）做乘法修正；
- 恰好一项 +10% (0.10)、一项 -10% (-0.10)，其余为 0；
- 六维两两组合（加/减不同项）共 30 种。
- 最终战斗属性：floor(base_stat * (1 + mod_pct))

用法：
    uv run python scripts/import_personalities.py
    uv run python scripts/import_personalities.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG


JSON_PATH = Path(__file__).resolve().parent.parent / "docs" / "pets" / "personalities.json"


# ── DDL ──────────────────────────────────────────────────────

PG_DDL = """
CREATE TABLE IF NOT EXISTS personality (
    id              SMALLINT     PRIMARY KEY,
    name            VARCHAR(32)  NOT NULL,
    hp_mod_pct      NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    spd_mod_pct     NUMERIC(3,2) NOT NULL DEFAULT 0,
    CONSTRAINT uk_personality_name UNIQUE (name)
);
"""


# ── 数据加载 ──────────────────────────────────────────────────

def _load_rows() -> list[tuple]:
    with open(JSON_PATH, encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)

    rows: list[tuple] = []
    seen_ids: set[int] = set()
    for idx, item in enumerate(data, start=1):
        pid = int(item.get("id") or idx)
        if pid in seen_ids:
            raise ValueError(f"重复的性格 id={pid}")
        seen_ids.add(pid)

        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError(f"空名称，id={pid}")
        rows.append((
            pid,
            name,
            item.get("hp_mod_pct", 0),
            item.get("phy_atk_mod_pct", 0),
            item.get("mag_atk_mod_pct", 0),
            item.get("phy_def_mod_pct", 0),
            item.get("mag_def_mod_pct", 0),
            item.get("spd_mod_pct", 0),
        ))
    rows.sort(key=lambda r: r[0])
    return rows


# ── PostgreSQL ───────────────────────────────────────────────

def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def write_pg(rows: list[tuple], dry_run: bool) -> None:
    t = time.time()
    print("\n[>>] 写入 PostgreSQL.personality ...", flush=True)
    conn = pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # 保留外键关系：先临时移除引用 personality 的外键，再重建 personality，最后再加回
            cur.execute("ALTER TABLE IF EXISTS pokemon_lineup_member DROP CONSTRAINT IF EXISTS pokemon_lineup_member_personality_id_fkey")
            cur.execute("DROP TABLE IF EXISTS personality")
            cur.execute(PG_DDL)
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO personality
                   (id, name,
                    hp_mod_pct, phy_atk_mod_pct, mag_atk_mod_pct,
                    phy_def_mod_pct, mag_def_mod_pct, spd_mod_pct)
                   VALUES %s""",
                rows,
            )
            cur.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_name = 'pokemon_lineup_member'
                    ) THEN
                        ALTER TABLE pokemon_lineup_member
                        ADD CONSTRAINT pokemon_lineup_member_personality_id_fkey
                        FOREIGN KEY (personality_id) REFERENCES personality(id);
                    END IF;
                EXCEPTION
                    WHEN duplicate_object THEN
                        NULL;
                END
                $$;
                """
            )
        if dry_run:
            conn.rollback()
            print(f"    [dry-run] PG 已回滚 ({time.time()-t:.2f}s)", flush=True)
        else:
            conn.commit()
            print(f"    [ok] PG 写入 {len(rows)} 条 ({time.time()-t:.2f}s)", flush=True)
    finally:
        conn.close()


# ── 主流程 ───────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="导入精灵性格字典到 PG")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不实际写入")
    args = parser.parse_args()

    rows = _load_rows()
    total = time.time()
    print("=" * 60)
    print(f"  导入性格字典: {len(rows)} 条，来源 {JSON_PATH}")
    print("=" * 60)

    write_pg(rows, args.dry_run)

    print(f"\n完成，总耗时 {time.time() - total:.2f}s")


if __name__ == "__main__":
    main()
