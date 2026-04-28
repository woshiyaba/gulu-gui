"""
MySQL -> PostgreSQL 数据迁移脚本（对齐 sql/wikiroco.sql 新模型）。

用法：
    uv run python scripts/migrate_mysql_to_pg_wikiroco.py
    uv run python scripts/migrate_mysql_to_pg_wikiroco.py --dry-run
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

SCHEMA_SQL = Path(__file__).resolve().parent.parent / "sql" / "wikiroco.sql"


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


def _reset_seq(pg_cur, table: str, col: str = "id") -> None:
    pg_cur.execute(
        f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
        f"COALESCE((SELECT MAX({col}) FROM {table}), 0) + 1, false)"
    )


def apply_schema() -> None:
    conn = pg_conn()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = current_database() AND pid <> pg_backend_pid()
    """)
    cur.execute("""
        DROP TABLE IF EXISTS skill_stone CASCADE;
        DROP TABLE IF EXISTS egg_hatch_pet CASCADE;
        DROP TABLE IF EXISTS pokemon_skill CASCADE;
        DROP TABLE IF EXISTS pet_map_point CASCADE;
        DROP TABLE IF EXISTS pokemon_attribute CASCADE;
        DROP TABLE IF EXISTS pokemon CASCADE;
        DROP TABLE IF EXISTS evolution_chain CASCADE;
        DROP TABLE IF EXISTS category CASCADE;
        DROP TABLE IF EXISTS skill CASCADE;
        DROP TABLE IF EXISTS pokemon_trait CASCADE;
        DROP TABLE IF EXISTS sys_dict CASCADE;
        DROP TABLE IF EXISTS attribute CASCADE;
    """)
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    cur.execute(sql)
    conn.close()
    print(f"[schema] 已执行 {SCHEMA_SQL.name}")


def load_or_seed_sys_dict(my_cur, pg_cur) -> dict[tuple[str, str], int]:
    t = _step("迁移/补齐 sys_dict")

    values: list[tuple[str, str, str, int]] = []

    # pokemon_type
    for r in mysql_fetch(
        my_cur,
        "SELECT DISTINCT type AS code, type_name AS label FROM pokemon WHERE type != '' ORDER BY type",
    ):
        values.append(("pokemon_type", r["code"], r["label"] or r["code"], 0))

    # pokemon_form
    for r in mysql_fetch(
        my_cur,
        "SELECT DISTINCT form AS code, form_name AS label FROM pokemon WHERE form != '' ORDER BY form",
    ):
        values.append(("pokemon_form", r["code"], r["label"] or r["code"], 0))

    # egg_group（来自旧 pokemon_egg_group.group_name）
    for r in mysql_fetch(
        my_cur,
        "SELECT DISTINCT group_name AS code FROM pokemon_egg_group WHERE group_name != '' ORDER BY group_name",
    ):
        values.append(("egg_group", r["code"], r["code"], 0))

    # skill_type（来自旧 skill.type）
    for r in mysql_fetch(
        my_cur,
        "SELECT DISTINCT type AS code FROM skill WHERE type != '' ORDER BY type",
    ):
        values.append(("skill_type", r["code"], r["code"], 0))

    # pokemon_skill 来源类型（冗余字典，用于下拉）
    values.append(("pokemon_skill_source", "原生技能", "原生技能", 0))
    values.append(("pokemon_skill_source", "技能石技能", "技能石技能", 1))

    _bulk_insert(
        pg_cur,
        """INSERT INTO sys_dict (dict_type, code, label, sort_order)
           VALUES %s
           ON CONFLICT (dict_type, code) DO UPDATE
           SET label = EXCLUDED.label""",
        values,
    )

    pg_cur.execute("SELECT id, dict_type, code FROM sys_dict")
    mapping = {(r["dict_type"], r["code"]): r["id"] for r in pg_cur.fetchall()}
    _done(len(values), t)
    return mapping


def migrate_attribute(my_cur, pg_cur) -> dict[str, int]:
    t = _step("迁移 attribute")
    by_name: dict[str, tuple[int, str]] = {}

    try:
        for r in mysql_fetch(my_cur, "SELECT attr_name, sort_order FROM attribute_axis"):
            if r["attr_name"]:
                by_name[r["attr_name"]] = (int(r["sort_order"]), "")
    except Exception:
        pass

    for r in mysql_fetch(my_cur, "SELECT DISTINCT attr_name, attr_image FROM pokemon_attribute WHERE attr_name != ''"):
        name = r["attr_name"]
        if not name:
            continue
        old = by_name.get(name, (9999, ""))
        image = old[1] or (r.get("attr_image") or "")
        by_name[name] = (old[0], image)

    for r in mysql_fetch(my_cur, "SELECT DISTINCT attr FROM skill WHERE attr != ''"):
        name = r["attr"]
        if name and name not in by_name:
            by_name[name] = (9999, "")

    values = [(n, s, i) for n, (s, i) in by_name.items()]
    _bulk_insert(
        pg_cur,
        """INSERT INTO attribute (name, sort_order, image)
           VALUES %s
           ON CONFLICT (name) DO UPDATE
           SET image = CASE
                 WHEN attribute.image = '' THEN EXCLUDED.image
                 ELSE attribute.image
               END""",
        values,
    )

    pg_cur.execute("SELECT id, name FROM attribute")
    mapping = {r["name"]: r["id"] for r in pg_cur.fetchall()}
    _done(len(values), t)
    return mapping


def migrate_trait(my_cur, pg_cur) -> dict[str, int]:
    t = _step("迁移 pokemon_trait")
    rows = mysql_fetch(
        my_cur,
        "SELECT DISTINCT trait_name, trait_desc FROM pokemon_detail WHERE trait_name != '' ORDER BY trait_name",
    )

    # 同一个 trait_name 在源数据中可能对应多条不同描述；批量 ON CONFLICT 时需先去重，
    # 否则会触发 “cannot affect row a second time”。
    merged: dict[str, str] = {}
    for r in rows:
        name = (r.get("trait_name") or "").strip()
        if not name:
            continue
        desc = (r.get("trait_desc") or "").strip()
        # 优先保留更长的描述，避免被空描述覆盖。
        if name not in merged or (desc and len(desc) > len(merged[name])):
            merged[name] = desc

    values = [(name, desc, i + 1) for i, (name, desc) in enumerate(merged.items())]
    _bulk_insert(
        pg_cur,
        """INSERT INTO pokemon_trait (name, description, sort_order)
           VALUES %s
           ON CONFLICT (name) DO UPDATE
           SET description = EXCLUDED.description""",
        values,
    )
    pg_cur.execute("SELECT id, name FROM pokemon_trait")
    mapping = {r["name"]: r["id"] for r in pg_cur.fetchall()}
    _done(len(values), t)
    return mapping


def migrate_evolution_chain(my_cur, pg_cur) -> None:
    t = _step("迁移 evolution_chain")
    rows = mysql_fetch(my_cur, "SELECT * FROM evolution_chain ORDER BY id")
    values = [
        (r["id"], r["chain_id"], r["sort_order"], r["pokemon_name"], r.get("evolution_condition", ""))
        for r in rows
    ]
    _bulk_insert(
        pg_cur,
        """INSERT INTO evolution_chain (id, chain_id, sort_order, pokemon_name, evolution_condition)
           VALUES %s
           ON CONFLICT DO NOTHING""",
        values,
    )
    _reset_seq(pg_cur, "evolution_chain")
    _done(len(values), t)


def migrate_pokemon(my_cur, pg_cur, trait_map: dict) -> dict[str, int]:
    t = _step("迁移 pokemon（合并旧 pokemon + pokemon_detail）")

    detail_rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_detail")
    detail_by_name = {r["pokemon_name"]: r for r in detail_rows}

    egg_rows = mysql_fetch(my_cur, "SELECT pokemon_id, group_name FROM pokemon_egg_group ORDER BY id")
    egg_group_by_pid: dict[int, str] = {}
    for r in egg_rows:
        if r["pokemon_id"] not in egg_group_by_pid and r.get("group_name"):
            egg_group_by_pid[r["pokemon_id"]] = r["group_name"]

    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon ORDER BY id")
    values = []
    name_id: dict[str, int] = {}
    for r in rows:
        d = detail_by_name.get(r["name"], {})
        egg_group = egg_group_by_pid.get(r["id"], "")
        trait_id = trait_map.get(d.get("trait_name", ""), None)
        if trait_id is None:
            # 没有特性时给一个兜底，避免 NOT NULL 失败
            trait_id = 1
        values.append(
            (
                r["id"], r["no"], r["name"], r.get("image", ""),
                r.get("type", ""), r.get("type_name", ""),
                r.get("form", ""), r.get("form_name", ""),
                egg_group, trait_id,
                r.get("detail_url", ""), r.get("image_lc", ""),
                d.get("chain_id"),
                d.get("hp", 0), d.get("atk", 0), d.get("matk", 0),
                d.get("def_val", 0), d.get("mdef", 0), d.get("spd", 0),
                int(d.get("hp", 0) or 0) + int(d.get("atk", 0) or 0) + int(d.get("matk", 0) or 0)
                + int(d.get("def_val", 0) or 0) + int(d.get("mdef", 0) or 0) + int(d.get("spd", 0) or 0),
                d.get("obtain_method", ""),
            )
        )
        name_id[r["name"]] = r["id"]

    _bulk_insert(
        pg_cur,
        """INSERT INTO pokemon
        (id, no, name, image, type, type_name, form, form_name, egg_group, trait_id, detail_url, image_lc,
         chain_id, hp, atk, matk, def_val, mdef, spd, total_race, obtain_method)
        VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    _reset_seq(pg_cur, "pokemon")
    _done(len(values), t)
    return name_id


def migrate_pokemon_attribute(my_cur, pg_cur, name_id: dict[str, int], attr_map: dict[str, int]) -> None:
    t = _step("迁移 pokemon_attribute")
    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_attribute ORDER BY id")
    values = []
    for r in rows:
        pid = name_id.get(r["pokemon_name"])
        aid = attr_map.get(r["attr_name"])
        if pid and aid:
            values.append((pid, aid))
    _bulk_insert(
        pg_cur,
        """INSERT INTO pokemon_attribute (pokemon_id, attr_id)
           VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    _done(len(values), t)


def migrate_skill(my_cur, pg_cur, attr_map: dict[str, int]) -> dict[str, int]:
    t = _step("迁移 skill")
    rows = mysql_fetch(my_cur, "SELECT * FROM skill ORDER BY id")
    values = []
    for r in rows:
        attr_id = attr_map.get(r.get("attr", "")) if r.get("attr") else None
        values.append(
            (
                r["id"], r["name"], attr_id, r.get("power", 0), r.get("type", ""),
                r.get("consume", 0), r.get("skill_desc"), r.get("icon", ""),
            )
        )
    _bulk_insert(
        pg_cur,
        """INSERT INTO skill (id, name, attr_id, power, type, consume, skill_desc, icon)
           VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    _reset_seq(pg_cur, "skill")
    _done(len(values), t)
    return {r["name"]: r["id"] for r in rows}


def migrate_pokemon_skill(my_cur, pg_cur, name_id: dict[str, int], skill_name_id: dict[str, int]) -> None:
    t = _step("迁移 pokemon_skill")
    rows = mysql_fetch(my_cur, "SELECT * FROM pokemon_skill ORDER BY id")
    values = []
    for r in rows:
        pid = name_id.get(r["pokemon_name"])
        sid = skill_name_id.get(r["skill_name"])
        if pid and sid:
            raw_type = r.get("type", 0)
            if isinstance(raw_type, str):
                skill_source = raw_type.strip() or "原生技能"
                if skill_source in {"原生", "原生技能"}:
                    skill_source = "原生技能"
                elif skill_source in {"学习", "学习技能", "技能石技能"}:
                    skill_source = "技能石技能"
                else:
                    skill_source = "技能石技能"
            else:
                skill_source = "原生技能" if int(raw_type or 0) == 0 else "技能石技能"
            values.append((pid, sid, skill_source, r.get("sort_order", 0)))
    _bulk_insert(
        pg_cur,
        """INSERT INTO pokemon_skill (pokemon_id, skill_id, type, sort_order)
           VALUES %s ON CONFLICT DO NOTHING""",
        values,
    )
    _done(len(values), t)


def migrate_egg_hatch_pet(my_cur, pg_cur, name_id: dict[str, int]) -> None:
    t = _step("迁移 egg_hatch_pet")
    rows = mysql_fetch(my_cur, "SELECT * FROM egg_hatch_pet ORDER BY id")
    values = []
    for r in rows:
        pid = name_id.get(r["pokemon_name"])
        if pid:
            values.append(
                (
                    pid, bool(r.get("is_leader_form", 0)), r.get("hatch_data", 0),
                    r.get("weight_low", 0), r.get("weight_high", 0),
                    r.get("height_low", 0), r.get("height_high", 0),
                )
            )
    _bulk_insert(
        pg_cur,
        """INSERT INTO egg_hatch_pet
           (pokemon_id, is_leader_form, hatch_data, weight_low, weight_high, height_low, height_high)
           VALUES %s
           ON CONFLICT (pokemon_id) DO UPDATE
           SET is_leader_form = EXCLUDED.is_leader_form,
               hatch_data = EXCLUDED.hatch_data,
               weight_low = EXCLUDED.weight_low,
               weight_high = EXCLUDED.weight_high,
               height_low = EXCLUDED.height_low,
               height_high = EXCLUDED.height_high""",
        values,
    )
    _done(len(values), t)


def migrate_skill_stone(my_cur, pg_cur, skill_name_id: dict[str, int]) -> None:
    t = _step("迁移 skill_stone")
    rows = mysql_fetch(my_cur, "SELECT * FROM skill_stone ORDER BY id")
    values = []
    for r in rows:
        sid = skill_name_id.get(r["skill_name"])
        if sid:
            values.append((sid, r.get("obtain_method", "")))
    _bulk_insert(
        pg_cur,
        """INSERT INTO skill_stone (skill_id, obtain_method)
           VALUES %s ON CONFLICT (skill_id) DO UPDATE
           SET obtain_method = EXCLUDED.obtain_method""",
        values,
    )
    _done(len(values), t)


def migrate_category(my_cur, pg_cur) -> None:
    t = _step("迁移 category")
    try:
        rows = mysql_fetch(my_cur, "SELECT * FROM category ORDER BY id")
    except Exception:
        _done(0, t)
        print("    [skip] MySQL 中 category 表不存在")
        return

    values = [
        (
            r["id"],
            r["category_id"],
            r.get("description", ""),
            r.get("type", ""),
            r.get("category_image_url", ""),
        )
        for r in rows
    ]
    _bulk_insert(
        pg_cur,
        """INSERT INTO category (id, category_id, description, type, category_image_url)
           VALUES %s
           ON CONFLICT (id) DO UPDATE
           SET category_id = EXCLUDED.category_id,
               description = EXCLUDED.description,
               type = EXCLUDED.type,
               category_image_url = EXCLUDED.category_image_url""",
        values,
    )
    _reset_seq(pg_cur, "category")
    _done(len(values), t)


def migrate_pet_map_point(my_cur, pg_cur) -> None:
    t = _step("迁移 pet_map_point")
    try:
        rows = mysql_fetch(my_cur, "SELECT * FROM pet_map_point ORDER BY id")
    except Exception:
        _done(0, t)
        print("    [skip] MySQL 中 pet_map_point 表不存在")
        return

    values = [
        (
            r["id"],
            r["source_id"],
            r["map_id"],
            r.get("title", ""),
            r["latitude"],
            r["longitude"],
            r["category_id"],
        )
        for r in rows
    ]
    _bulk_insert(
        pg_cur,
        """INSERT INTO pet_map_point (id, source_id, map_id, title, latitude, longitude, category_id)
           VALUES %s
           ON CONFLICT (id) DO UPDATE
           SET source_id = EXCLUDED.source_id,
               map_id = EXCLUDED.map_id,
               title = EXCLUDED.title,
               latitude = EXCLUDED.latitude,
               longitude = EXCLUDED.longitude,
               category_id = EXCLUDED.category_id""",
        values,
    )
    _reset_seq(pg_cur, "pet_map_point")
    _done(len(values), t)


def main() -> None:
    parser = argparse.ArgumentParser(description="MySQL -> PostgreSQL 迁移（wikiroco.sql）")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    args = parser.parse_args()

    total = time.time()
    print("=" * 60)
    print("  MySQL -> PostgreSQL 迁移（新字典模型）")
    print("=" * 60)

    apply_schema()

    my = mysql_conn()
    pg = pg_conn()
    pg.autocommit = False
    try:
        my_cur = my.cursor()
        pg_cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        sys_map = load_or_seed_sys_dict(my_cur, pg_cur)
        attr_map = migrate_attribute(my_cur, pg_cur)
        trait_map = migrate_trait(my_cur, pg_cur)

        # trait 兜底：若空库导致 id=1 不存在，补一个
        if 1 not in trait_map.values():
            pg_cur.execute(
                "INSERT INTO pokemon_trait (name, description, sort_order) VALUES (%s, %s, %s) "
                "ON CONFLICT (name) DO NOTHING",
                ("未知特性", "", 0),
            )
            pg_cur.execute("SELECT id, name FROM pokemon_trait")
            trait_map = {r["name"]: r["id"] for r in pg_cur.fetchall()}

        migrate_evolution_chain(my_cur, pg_cur)
        pokemon_name_id = migrate_pokemon(my_cur, pg_cur, trait_map)
        migrate_pokemon_attribute(my_cur, pg_cur, pokemon_name_id, attr_map)
        skill_name_id = migrate_skill(my_cur, pg_cur, attr_map)
        migrate_pokemon_skill(my_cur, pg_cur, pokemon_name_id, skill_name_id)
        migrate_egg_hatch_pet(my_cur, pg_cur, pokemon_name_id)
        migrate_skill_stone(my_cur, pg_cur, skill_name_id)
        migrate_category(my_cur, pg_cur)
        migrate_pet_map_point(my_cur, pg_cur)

        if args.dry_run:
            pg.rollback()
            print("\n[dry-run] 已回滚")
        else:
            pg.commit()
            print("\n[commit] 已提交")

        print(f"\n完成，总耗时 {time.time() - total:.2f}s")
    except Exception:
        pg.rollback()
        raise
    finally:
        my.close()
        pg.close()


if __name__ == "__main__":
    main()

