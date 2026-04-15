"""
MySQL → PostgreSQL 数据迁移脚本。

读取 MySQL 旧表数据，按新版 PG 表结构（字典表 + ID 外键）写入 PostgreSQL。

前置条件：
    1. pip install psycopg2-binary   （或 uv add psycopg2-binary）
    2. PG 端已创建好数据库 wikiroco
    3. MySQL .env 配置正确

用法：
    uv run python scripts/migrate_mysql_to_pg.py
    uv run python scripts/migrate_mysql_to_pg.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
import psycopg2
import psycopg2.extras
from config import DB_CONFIG

# ── PG 连接配置 ──────────────────────────────────────────────
PG_CONFIG = {
    "host": os.getenv("PG_HOST", "101.126.137.23"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "dbname": os.getenv("PG_DATABASE", "wikiroco"),
    "user": os.getenv("PG_USER", "wikiroco"),
    "password": os.getenv("PG_PASSWORD", "wikiroco1234"),
}

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "sql" / "schema_pg.sql"

# ── 工具函数 ─────────────────────────────────────────────────

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


def pg_execute_schema() -> None:
    """用独立的 autocommit 连接执行 DDL，避免被其他事务锁阻塞。"""
    conn = pg_conn()
    conn.autocommit = True
    cur = conn.cursor()

    # 先终止其他连接，释放可能的残留锁
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = current_database() AND pid <> pg_backend_pid()
    """)
    terminated = cur.fetchall()
    if terminated:
        print(f"[schema] 已终止 {len(terminated)} 个残留连接")

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    cur.execute(sql)
    conn.close()
    print(f"[schema] 已执行 {SCHEMA_SQL.name}")


def pg_load_dict(pg_cur, table: str, key_col: str) -> dict[str, int]:
    """从 PG 字典表加载 {name/code → id} 映射。"""
    pg_cur.execute(f"SELECT id, {key_col} FROM {table}")
    return {row[key_col]: row["id"] for row in pg_cur.fetchall()}


def pg_reset_seq(pg_cur, table: str, column: str = "id") -> None:
    """重置序列到 max(id)+1，避免后续插入冲突。"""
    pg_cur.execute(
        f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
        f"COALESCE((SELECT MAX({column}) FROM {table}), 0) + 1, false)"
    )


def _bulk_insert(pg_cur, sql: str, values: list[tuple], page_size: int = 1000) -> None:
    """使用 execute_values 批量插入，比 executemany 快 10-50 倍。"""
    psycopg2.extras.execute_values(pg_cur, sql, values, page_size=page_size)


def _copy_insert(pg_cur, table: str, columns: list[str], values: list[tuple]) -> None:
    """使用 COPY 协议批量写入，最快的方式。适合无冲突处理的大表。"""
    buf = StringIO()
    for row in values:
        line = "\t".join("\\N" if v is None else str(v) for v in row)
        buf.write(line + "\n")
    buf.seek(0)
    cols = ", ".join(columns)
    pg_cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)


def _step(msg: str) -> float:
    print(f"\n[>>] {msg} ...", flush=True)
    return time.time()


def _done(count: int, start: float) -> None:
    elapsed = time.time() - start
    print(f"    [ok] {count} 条  ({elapsed:.2f}s)", flush=True)


def _warn_skipped(label: str, items: list[str], limit: int = 30) -> None:
    """打印未匹配的详细记录。"""
    if not items:
        return
    print(f"    [warn] 跳过 {len(items)} 条（{label}）:")
    for item in items[:limit]:
        print(f"      - {item}")
    if len(items) > limit:
        print(f"      ... 还有 {len(items) - limit} 条，已省略")


# ── 迁移各表 ─────────────────────────────────────────────────

def migrate_pokemon(my_cur, pg_cur, sys_dict_map: dict) -> dict[str, int]:
    """迁移 pokemon 表，返回 {name → pg_id} 映射。"""
    t = _step("迁移 pokemon")

    type_map: dict[str, int | None] = {}
    form_map: dict[str, int | None] = {}
    for (dtype, code), did in sys_dict_map.items():
        if dtype == "pokemon_type":
            type_map[code] = did
        elif dtype == "pokemon_form":
            form_map[code] = did

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon ORDER BY id")
    if not rows:
        _done(0, t)
        return {}

    unmatched_type: list[str] = []
    unmatched_form: list[str] = []
    values = []
    for r in rows:
        raw_type = r.get("type", "")
        raw_form = r.get("form", "")
        type_id = type_map.get(raw_type) if raw_type else None
        form_id = form_map.get(raw_form) if raw_form else None

        if raw_type and type_id is None:
            unmatched_type.append(f"id={r['id']} name={r['name']} type={raw_type!r}")
        if raw_form and form_id is None:
            unmatched_form.append(f"id={r['id']} name={r['name']} form={raw_form!r}")

        values.append((
            r["id"], r["no"], r["name"], r.get("image", ""),
            type_id, form_id,
            r.get("detail_url", ""), r.get("image_lc", ""),
        ))

    _bulk_insert(
        pg_cur,
        """INSERT INTO pokemon (id, no, name, image, type_id, form_id, detail_url, image_lc)
           VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    pg_reset_seq(pg_cur, "pokemon")

    name_id = {r["name"]: r["id"] for r in rows}
    _done(len(values), t)
    _warn_skipped("type 未匹配 sys_dict", unmatched_type)
    _warn_skipped("form 未匹配 sys_dict", unmatched_form)
    return name_id


def migrate_pokemon_attribute(
    my_cur, pg_cur,
    pokemon_name_id: dict[str, int],
    attr_map: dict[str, int],
) -> None:
    """迁移 pokemon_attribute；顺带把 attr_image 回写到 dict_attribute.image。"""
    t = _step("迁移 pokemon_attribute")

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_attribute ORDER BY id")

    # 收集每个属性的第一张图片，回写 dict_attribute.image
    attr_images: dict[str, str] = {}
    for r in rows:
        name = r.get("attr_name", "")
        img = r.get("attr_image", "")
        if name and img and name not in attr_images:
            attr_images[name] = img

    for attr_name, img in attr_images.items():
        if attr_name in attr_map:
            pg_cur.execute(
                "UPDATE dict_attribute SET image = %s WHERE id = %s",
                (img, attr_map[attr_name]),
            )

    values = []
    skipped: list[str] = []
    for r in rows:
        pid = pokemon_name_id.get(r["pokemon_name"])
        aid = attr_map.get(r.get("attr_name", ""))
        if pid is None or aid is None:
            reason = []
            if pid is None:
                reason.append(f"pokemon={r['pokemon_name']!r} 未找到")
            if aid is None:
                reason.append(f"attr={r.get('attr_name', '')!r} 未找到")
            skipped.append(f"id={r['id']} {', '.join(reason)}")
            continue
        values.append((pid, aid))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO pokemon_attribute (pokemon_id, attr_id)
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("属性或精灵未匹配", skipped)


def migrate_pokemon_egg_group(
    my_cur, pg_cur,
    egg_group_map: dict[str, int],
) -> None:
    """迁移 pokemon_egg_group（MySQL 已用 pokemon_id）。"""
    t = _step("迁移 pokemon_egg_group")

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_egg_group ORDER BY id")
    values = []
    skipped: list[str] = []
    for r in rows:
        gid = egg_group_map.get(r["group_name"])
        if gid is None:
            skipped.append(f"id={r['id']} pokemon_id={r['pokemon_id']} group_name={r['group_name']!r}")
            continue
        values.append((r["pokemon_id"], gid))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO pokemon_egg_group (pokemon_id, egg_group_id)
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("蛋组未匹配 dict_egg_group", skipped)


def migrate_skill(
    my_cur, pg_cur,
    attr_map: dict[str, int],
    skill_type_map: dict[str, int],
) -> dict[str, int]:
    """迁移 skill 表，返回 {name → pg_id} 映射。"""
    t = _step("迁移 skill")

    rows = mysql_fetch(my_cur, "SELECT * FROM skill ORDER BY id")
    if not rows:
        _done(0, t)
        return {}

    unmatched_attr: list[str] = []
    unmatched_type: list[str] = []
    values = []
    for r in rows:
        raw_attr = r.get("attr", "")
        raw_type = r.get("type", "")
        attr_id = attr_map.get(raw_attr) if raw_attr else None
        type_id = skill_type_map.get(raw_type) if raw_type else None

        if raw_attr and attr_id is None:
            unmatched_attr.append(f"id={r['id']} name={r['name']} attr={raw_attr!r}")
        if raw_type and type_id is None:
            unmatched_type.append(f"id={r['id']} name={r['name']} type={raw_type!r}")

        values.append((
            r["id"], r["name"], attr_id, r.get("power", 0),
            type_id, r.get("consume", 0),
            r.get("skill_desc"), r.get("icon", ""),
        ))

    _bulk_insert(
        pg_cur,
        """INSERT INTO skill (id, name, attr_id, power, skill_type_id, consume, skill_desc, icon)
           VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    pg_reset_seq(pg_cur, "skill")

    name_id = {r["name"]: r["id"] for r in rows}
    _done(len(values), t)
    _warn_skipped("attr 未匹配 dict_attribute", unmatched_attr)
    _warn_skipped("type 未匹配 dict_skill_type", unmatched_type)
    return name_id


def migrate_evolution_chain(my_cur, pg_cur) -> None:
    """迁移 evolution_chain（结构不变，COPY 写入）。"""
    t = _step("迁移 evolution_chain")

    rows = mysql_fetch(my_cur, "SELECT * FROM evolution_chain ORDER BY id")
    if not rows:
        _done(0, t)
        return

    values = [
        (r["id"], r["chain_id"], r["sort_order"],
         r["pokemon_name"], r.get("evolution_condition", ""))
        for r in rows
    ]

    _copy_insert(pg_cur, "evolution_chain",
                 ["id", "chain_id", "sort_order", "pokemon_name", "evolution_condition"],
                 values)
    pg_reset_seq(pg_cur, "evolution_chain")
    _done(len(values), t)


def migrate_pokemon_detail(my_cur, pg_cur, pokemon_name_id: dict[str, int]) -> None:
    """迁移 pokemon_detail（pokemon_name → pokemon_id，丢弃 JSON 克制列）。"""
    t = _step("迁移 pokemon_detail")

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_detail ORDER BY id")
    values = []
    skipped: list[str] = []
    for r in rows:
        pid = pokemon_name_id.get(r["pokemon_name"])
        if pid is None:
            skipped.append(f"id={r['id']} pokemon_name={r['pokemon_name']!r}")
            continue
        values.append((
            pid, r.get("chain_id"),
            r.get("hp", 0), r.get("atk", 0), r.get("matk", 0),
            r.get("def_val", 0), r.get("mdef", 0), r.get("spd", 0),
            r.get("trait_name", ""), r.get("trait_desc"),
            r.get("obtain_method", ""),
        ))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO pokemon_detail
                   (pokemon_id, chain_id, hp, atk, matk, def_val, mdef, spd,
                    trait_name, trait_desc, obtain_method)
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("精灵未匹配", skipped)


def migrate_pokemon_skill(
    my_cur, pg_cur,
    pokemon_name_id: dict[str, int],
    skill_name_id: dict[str, int],
) -> None:
    """迁移 pokemon_skill（name → id）。"""
    t = _step("迁移 pokemon_skill")

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_skill ORDER BY id")
    values = []
    skipped: list[str] = []
    for r in rows:
        pid = pokemon_name_id.get(r["pokemon_name"])
        sid = skill_name_id.get(r["skill_name"])
        if pid is None or sid is None:
            reason = []
            if pid is None:
                reason.append(f"pokemon={r['pokemon_name']!r}")
            if sid is None:
                reason.append(f"skill={r['skill_name']!r}")
            skipped.append(f"id={r['id']} {' / '.join(reason)} 未找到")
            continue
        values.append((pid, sid, r.get("sort_order", 0)))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO pokemon_skill (pokemon_id, skill_id, sort_order)
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("精灵或技能未匹配", skipped)


def migrate_egg_hatch_pet(my_cur, pg_cur, pokemon_name_id: dict[str, int]) -> None:
    """迁移 egg_hatch_pet（pokemon_name → pokemon_id）。"""
    t = _step("迁移 egg_hatch_pet")

    rows = mysql_fetch(my_cur, "SELECT * FROM egg_hatch_pet ORDER BY id")
    values = []
    skipped: list[str] = []
    for r in rows:
        pid = pokemon_name_id.get(r["pokemon_name"])
        if pid is None:
            skipped.append(f"id={r['id']} pokemon_name={r['pokemon_name']!r}")
            continue
        values.append((
            pid, bool(r.get("is_leader_form", 0)),
            r.get("hatch_data", 0),
            r.get("weight_low", 0), r.get("weight_high", 0),
            r.get("height_low", 0), r.get("height_high", 0),
        ))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO egg_hatch_pet
                   (pokemon_id, is_leader_form, hatch_data,
                    weight_low, weight_high, height_low, height_high)
               VALUES %s""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("精灵未匹配", skipped)


def migrate_skill_stone(my_cur, pg_cur, skill_name_id: dict[str, int]) -> None:
    """迁移 skill_stone（skill_name → skill_id）。"""
    t = _step("迁移 skill_stone")

    try:
        rows = mysql_fetch(my_cur, "SELECT * FROM skill_stone ORDER BY id")
    except pymysql.err.ProgrammingError:
        print("    [skip] MySQL 中 skill_stone 表不存在")
        return

    values = []
    skipped: list[str] = []
    for r in rows:
        sid = skill_name_id.get(r["skill_name"])
        if sid is None:
            skipped.append(f"id={r['id']} skill_name={r['skill_name']!r}")
            continue
        values.append((sid, r.get("obtain_method", "")))

    if values:
        _bulk_insert(
            pg_cur,
            """INSERT INTO skill_stone (skill_id, obtain_method)
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("技能未匹配", skipped)


def migrate_attribute_matchup(my_cur, pg_cur, attr_map: dict[str, int]) -> None:
    """迁移 attribute_matchup（attr_name → attr_id）。"""
    t = _step("迁移 attribute_matchup")

    rows = mysql_fetch(my_cur, "SELECT * FROM attribute_matchup")
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
               VALUES %s ON CONFLICT DO NOTHING""",
            values,
        )

    _done(len(values), t)
    _warn_skipped("属性未匹配 dict_attribute", skipped)


def migrate_category(my_cur, pg_cur) -> None:
    """迁移 category（COPY 写入）。"""
    t = _step("迁移 category")

    try:
        rows = mysql_fetch(my_cur, "SELECT * FROM category ORDER BY id")
    except pymysql.err.ProgrammingError:
        print("    [skip] MySQL 中 category 表不存在")
        return

    if not rows:
        _done(0, t)
        return

    values = [
        (r["id"], r["category_id"], r.get("description", ""),
         r.get("type", ""), r.get("category_image_url", ""))
        for r in rows
    ]

    _copy_insert(pg_cur, "category",
                 ["id", "category_id", "description", "type", "category_image_url"],
                 values)
    pg_reset_seq(pg_cur, "category")
    _done(len(values), t)


def migrate_pet_map_point(my_cur, pg_cur) -> None:
    """迁移 pet_map_point（COPY 写入，数据量最大）。"""
    t = _step("迁移 pet_map_point")

    rows = mysql_fetch(my_cur, "SELECT * FROM pet_map_point ORDER BY id")
    if not rows:
        _done(0, t)
        return

    values = [
        (r["id"], r["source_id"], r["map_id"], r.get("title", ""),
         r["latitude"], r["longitude"], r["category_id"])
        for r in rows
    ]

    _copy_insert(pg_cur, "pet_map_point",
                 ["id", "source_id", "map_id", "title", "latitude", "longitude", "category_id"],
                 values)
    pg_reset_seq(pg_cur, "pet_map_point")
    _done(len(values), t)


# ── 主流程 ───────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MySQL → PostgreSQL 数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    args = parser.parse_args()

    total_start = time.time()
    print("=" * 55)
    print("  MySQL → PostgreSQL 迁移")
    print("=" * 55)

    # 1. 建表 + 插入字典数据（独立 autocommit 连接，会清理残留锁）
    #    必须在打开数据连接之前执行，否则 terminate 会断掉自己
    pg_execute_schema()

    my = mysql_conn()
    pg = pg_conn()
    pg.autocommit = False

    try:
        my_cur = my.cursor()
        pg_cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 2. 加载字典映射
        attr_map = pg_load_dict(pg_cur, "dict_attribute", "name")
        skill_type_map = pg_load_dict(pg_cur, "dict_skill_type", "name")
        egg_group_map = pg_load_dict(pg_cur, "dict_egg_group", "name")

        pg_cur.execute("SELECT id, dict_type, code FROM sys_dict")
        sys_dict_map = {(r["dict_type"], r["code"]): r["id"] for r in pg_cur.fetchall()}

        print(f"\n[dict] attr={len(attr_map)}  skill_type={len(skill_type_map)}  "
              f"egg_group={len(egg_group_map)}  sys_dict={len(sys_dict_map)}")

        # 3. 按依赖顺序迁移业务表
        pokemon_name_id = migrate_pokemon(my_cur, pg_cur, sys_dict_map)
        skill_name_id = migrate_skill(my_cur, pg_cur, attr_map, skill_type_map)

        migrate_pokemon_attribute(my_cur, pg_cur, pokemon_name_id, attr_map)
        migrate_pokemon_egg_group(my_cur, pg_cur, egg_group_map)
        migrate_evolution_chain(my_cur, pg_cur)
        migrate_pokemon_detail(my_cur, pg_cur, pokemon_name_id)
        migrate_pokemon_skill(my_cur, pg_cur, pokemon_name_id, skill_name_id)
        migrate_egg_hatch_pet(my_cur, pg_cur, pokemon_name_id)
        migrate_skill_stone(my_cur, pg_cur, skill_name_id)
        migrate_attribute_matchup(my_cur, pg_cur, attr_map)
        migrate_category(my_cur, pg_cur)
        migrate_pet_map_point(my_cur, pg_cur)

        if args.dry_run:
            pg.rollback()
            print(f"\n[dry-run] 已全部回滚，未写入 PG")
        else:
            pg.commit()

        total = time.time() - total_start
        print(f"\n{'=' * 55}")
        print(f"  {'回滚' if args.dry_run else '迁移'}完成！总耗时 {total:.2f}s")
        print(f"{'=' * 55}")

    except Exception:
        pg.rollback()
        raise
    finally:
        my.close()
        pg.close()


if __name__ == "__main__":
    main()
