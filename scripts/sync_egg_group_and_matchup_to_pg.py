"""
同步 pokemon_egg_group 和 attribute_matchup 到 PostgreSQL。

流程：
    1. 在 PG 中创建 pokemon_egg_group / attribute_matchup 表（如不存在）
    2. 从 MySQL pokemon_egg_group 读取数据，通过 pokemon.name 匹配 PG 的 pokemon.id，写入 PG
    3. 从 MySQL attribute_matchup 读取数据，通过 attribute.name 匹配 PG 的 attribute.id，写入 PG

用法：
    uv run python scripts/sync_egg_group_and_matchup_to_pg.py
    uv run python scripts/sync_egg_group_and_matchup_to_pg.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
import psycopg2
import psycopg2.extras

from config import DB_CONFIG

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "101.126.137.23"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "dbname": os.getenv("PG_DATABASE", "wikiroco"),
    "user": os.getenv("PG_USER", "wikiroco"),
    "password": os.getenv("PG_PASSWORD", "wikiroco1234"),
}


def mysql_conn() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset=DB_CONFIG["charset"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def mysql_fetch(cur, sql: str) -> list[dict]:
    cur.execute(sql)
    return cur.fetchall()


def _step(msg: str) -> float:
    print(f"\n[>>] {msg} ...", flush=True)
    return time.time()


def _done(count: int, start: float) -> None:
    print(f"    [ok] {count} 条 ({time.time() - start:.2f}s)", flush=True)


def _bulk_insert(pg_cur, sql: str, values: list[tuple], page_size: int = 1000) -> None:
    if not values:
        return
    psycopg2.extras.execute_values(pg_cur, sql, values, page_size=page_size)


def _warn_skipped(label: str, items: list[str], limit: int = 30) -> None:
    if not items:
        return
    print(f"    [warn] 跳过 {len(items)} 条（{label}）:")
    for item in items[:limit]:
        print(f"      - {item}")
    if len(items) > limit:
        print(f"      ... 还有 {len(items) - limit} 条，已省略")


# ── PG 建表 DDL ─────────────────────────────────────────────

PG_DDL = """
CREATE TABLE IF NOT EXISTS pokemon_egg_group (
    id           SERIAL      PRIMARY KEY,
    pokemon_id   INT         NOT NULL,
    group_name   VARCHAR(50) NOT NULL,
    CONSTRAINT uk_peg_pokemon_group UNIQUE (pokemon_id, group_name),
    CONSTRAINT fk_peg_pokemon FOREIGN KEY (pokemon_id)
        REFERENCES pokemon (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attribute_matchup (
    defender_attr_id INT            NOT NULL,
    attacker_attr_id INT            NOT NULL,
    multiplier       NUMERIC(10, 8) NOT NULL,
    PRIMARY KEY (defender_attr_id, attacker_attr_id),
    CONSTRAINT fk_am_defender FOREIGN KEY (defender_attr_id)
        REFERENCES attribute (id) ON DELETE CASCADE,
    CONSTRAINT fk_am_attacker FOREIGN KEY (attacker_attr_id)
        REFERENCES attribute (id) ON DELETE CASCADE
);
"""


def ensure_pg_tables(pg_cur) -> None:
    t = _step("确保 PG 表存在")
    pg_cur.execute(PG_DDL)
    print("    [ok] pokemon_egg_group, attribute_matchup 已就绪", flush=True)


# ── 同步 pokemon_egg_group ──────────────────────────────────

def sync_egg_group(my_cur, pg_cur) -> None:
    t = _step("同步 pokemon_egg_group")

    # 1. 从 MySQL 读取蛋组数据，联查 pokemon.name
    rows = mysql_fetch(my_cur, """
        SELECT eg.pokemon_id, eg.group_name, p.name AS pokemon_name
        FROM pokemon_egg_group eg
        JOIN pokemon p ON p.id = eg.pokemon_id
        ORDER BY eg.id
    """)
    if not rows:
        _done(0, t)
        return

    # 2. 加载 PG 的 {name → id} 映射
    pg_cur.execute("SELECT id, name FROM pokemon")
    pg_name_id = {r["name"]: r["id"] for r in pg_cur.fetchall()}

    # 3. 匹配并构建插入数据
    values = []
    skipped: list[str] = []
    for r in rows:
        pg_pid = pg_name_id.get(r["pokemon_name"])
        if pg_pid is None:
            skipped.append(f"pokemon_name={r['pokemon_name']!r} group={r['group_name']!r}")
            continue
        values.append((pg_pid, r["group_name"]))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO pokemon_egg_group (pokemon_id, group_name)
               VALUES %s ON CONFLICT (pokemon_id, group_name) DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("PG 中未找到对应精灵", skipped)


# ── 同步 attribute_matchup ──────────────────────────────────

def sync_attribute_matchup(my_cur, pg_cur) -> None:
    t = _step("同步 attribute_matchup")

    # 1. 从 MySQL 读取属性克制数据
    rows = mysql_fetch(my_cur, "SELECT defender_attr, attacker_attr, multiplier FROM attribute_matchup")
    if not rows:
        _done(0, t)
        return

    # 2. 加载 PG 的 {name → id} 映射
    pg_cur.execute("SELECT id, name FROM attribute")
    attr_map = {r["name"]: r["id"] for r in pg_cur.fetchall()}

    # 3. 匹配并构建插入数据
    values = []
    skipped: list[str] = []
    for r in rows:
        did = attr_map.get(r["defender_attr"])
        aid = attr_map.get(r["attacker_attr"])
        if did is None or aid is None:
            skipped.append(f"defender={r['defender_attr']!r} attacker={r['attacker_attr']!r}")
            continue
        values.append((did, aid, r["multiplier"]))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO attribute_matchup (defender_attr_id, attacker_attr_id, multiplier)
               VALUES %s ON CONFLICT (defender_attr_id, attacker_attr_id) DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("PG 中未找到对应属性", skipped)


# ── 主流程 ───────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="同步 egg_group + attribute_matchup 到 PG")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    args = parser.parse_args()

    total = time.time()
    print("=" * 60)
    print("  同步 pokemon_egg_group + attribute_matchup → PostgreSQL")
    print("=" * 60)

    my = mysql_conn()
    pg = pg_conn()
    pg.autocommit = False

    try:
        my_cur = my.cursor()
        pg_cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        ensure_pg_tables(pg_cur)
        sync_egg_group(my_cur, pg_cur)
        sync_attribute_matchup(my_cur, pg_cur)

        if args.dry_run:
            pg.rollback()
            print(f"\n[dry-run] 已回滚，未写入 PG")
        else:
            pg.commit()
            print(f"\n[commit] 已提交")

        print(f"\n完成，总耗时 {time.time() - total:.2f}s")

    except Exception:
        pg.rollback()
        raise
    finally:
        my.close()
        pg.close()


if __name__ == "__main__":
    main()
