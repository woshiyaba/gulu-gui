"""
从 docs/pets/personalities.json 导入精灵性格字典。

性格规则：
- 每个性格对六维（HP / 物攻 / 魔攻 / 物防 / 魔防 / 速度）做乘法修正；
- 恰好一项 +10% (0.10)、一项 -10% (-0.10)，其余为 0；
- 六维两两组合（加/减不同项）共 30 种。
- 最终战斗属性：floor(base_stat * (1 + mod_pct))

写入目标：
- MySQL.personality（与其它 import_* 脚本对齐，落 MySQL 源头）
- PostgreSQL.personality（纯字典表，直接同步到 PG，无需 migrate 脚本中转）

用法：
    uv run python scripts/import_personalities.py
    uv run python scripts/import_personalities.py --dry-run
    uv run python scripts/import_personalities.py --only mysql
    uv run python scripts/import_personalities.py --only pg
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

import pymysql
import psycopg2
import psycopg2.extras

from config import DB_CONFIG, PG_CONFIG


JSON_PATH = Path(__file__).resolve().parent.parent / "docs" / "pets" / "personalities.json"


# ── DDL ──────────────────────────────────────────────────────

MYSQL_DDL = """
CREATE TABLE IF NOT EXISTS personality (
    id              SMALLINT       NOT NULL COMMENT '性格ID，来源 personalities.json',
    name_en         VARCHAR(32)    NOT NULL COMMENT '英文名',
    name_zh         VARCHAR(16)    NOT NULL COMMENT '中文名',
    hp_mod_pct      DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT 'HP修正：+0.10/-0.10/0',
    phy_atk_mod_pct DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT '物攻修正',
    mag_atk_mod_pct DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT '魔攻修正',
    phy_def_mod_pct DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT '物防修正',
    mag_def_mod_pct DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT '魔防修正',
    spd_mod_pct     DECIMAL(3, 2)  NOT NULL DEFAULT 0 COMMENT '速度修正',
    PRIMARY KEY (id),
    UNIQUE KEY uk_personality_en (name_en),
    UNIQUE KEY uk_personality_zh (name_zh)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵性格字典（六维乘法修正）';
"""

PG_DDL = """
CREATE TABLE IF NOT EXISTS personality (
    id              SMALLINT     PRIMARY KEY,
    name_en         VARCHAR(32)  NOT NULL,
    name_zh         VARCHAR(16)  NOT NULL,
    hp_mod_pct      NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_atk_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    phy_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    mag_def_mod_pct NUMERIC(3,2) NOT NULL DEFAULT 0,
    spd_mod_pct     NUMERIC(3,2) NOT NULL DEFAULT 0,
    CONSTRAINT uk_personality_en UNIQUE (name_en),
    CONSTRAINT uk_personality_zh UNIQUE (name_zh)
);
"""


# ── 数据加载 ──────────────────────────────────────────────────

def _load_rows() -> list[tuple]:
    with open(JSON_PATH, encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)

    rows: list[tuple] = []
    seen_ids: set[int] = set()
    for item in data:
        pid = int(item["id"])
        if pid in seen_ids:
            raise ValueError(f"重复的性格 id={pid}")
        seen_ids.add(pid)

        name_en = item["name"]
        name_zh = item["localized"]["zh"]
        rows.append((
            pid,
            name_en,
            name_zh,
            item.get("hp_mod_pct", 0),
            item.get("phy_atk_mod_pct", 0),
            item.get("mag_atk_mod_pct", 0),
            item.get("phy_def_mod_pct", 0),
            item.get("mag_def_mod_pct", 0),
            item.get("spd_mod_pct", 0),
        ))
    rows.sort(key=lambda r: r[0])
    return rows


# ── MySQL ────────────────────────────────────────────────────

def mysql_conn() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def write_mysql(rows: list[tuple], dry_run: bool) -> None:
    t = time.time()
    print("\n[>>] 写入 MySQL.personality ...", flush=True)
    conn = mysql_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(MYSQL_DDL)
            cur.execute("DELETE FROM personality")
            cur.executemany(
                """INSERT INTO personality
                   (id, name_en, name_zh,
                    hp_mod_pct, phy_atk_mod_pct, mag_atk_mod_pct,
                    phy_def_mod_pct, mag_def_mod_pct, spd_mod_pct)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                rows,
            )
        if dry_run:
            conn.rollback()
            print(f"    [dry-run] MySQL 已回滚 ({time.time()-t:.2f}s)", flush=True)
        else:
            conn.commit()
            print(f"    [ok] MySQL 写入 {len(rows)} 条 ({time.time()-t:.2f}s)", flush=True)
    finally:
        conn.close()


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
            cur.execute(PG_DDL)
            cur.execute("DELETE FROM personality")
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO personality
                   (id, name_en, name_zh,
                    hp_mod_pct, phy_atk_mod_pct, mag_atk_mod_pct,
                    phy_def_mod_pct, mag_def_mod_pct, spd_mod_pct)
                   VALUES %s""",
                rows,
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
    parser = argparse.ArgumentParser(description="导入精灵性格字典到 MySQL/PG")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不实际写入")
    parser.add_argument(
        "--only",
        choices=("mysql", "pg", "both"),
        default="both",
        help="仅写入指定库（默认两边都写）",
    )
    args = parser.parse_args()

    rows = _load_rows()
    total = time.time()
    print("=" * 60)
    print(f"  导入性格字典: {len(rows)} 条，来源 {JSON_PATH}")
    print("=" * 60)

    if args.only in ("mysql", "both"):
        write_mysql(rows, args.dry_run)
    if args.only in ("pg", "both"):
        write_pg(rows, args.dry_run)

    print(f"\n完成，总耗时 {time.time() - total:.2f}s")


if __name__ == "__main__":
    main()
