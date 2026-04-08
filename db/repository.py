import json
import pymysql
from db.connection import get_conn

# ── 批量大小 ────────────────────────────────────────────────
_BATCH = 200


# ── 通用工具 ────────────────────────────────────────────────

def _executemany(cur: pymysql.cursors.DictCursor, sql: str, rows: list) -> None:
    """分批执行，避免单次提交数据量过大。"""
    for i in range(0, len(rows), _BATCH):
        cur.executemany(sql, rows[i: i + _BATCH])


# ── pokemon ─────────────────────────────────────────────────

def upsert_pokemon(pokemon_list: list[dict]) -> None:
    """写入/更新精灵基础信息和属性。"""
    sql_pokemon = """
        INSERT INTO pokemon (no, name, image, type, type_name, form, form_name, detail_url)
        VALUES (%(no)s, %(name)s, %(image)s, %(type)s, %(type_name)s,
                %(form)s, %(form_name)s, %(detail_url)s)
        ON DUPLICATE KEY UPDATE
            name       = VALUES(name),
            image      = VALUES(image),
            type       = VALUES(type),
            type_name  = VALUES(type_name),
            form       = VALUES(form),
            form_name  = VALUES(form_name),
            detail_url = VALUES(detail_url)
    """

    rows_pokemon = [
        {
            "no":          p["no"],
            "name":        p["name"],
            "image":       p.get("image", ""),
            "type":        p.get("type", ""),
            "type_name":   p.get("typeName", ""),
            "form":        p.get("form", ""),
            "form_name":   p.get("formName", ""),
            "detail_url":  p.get("detailUrl", ""),
        }
        for p in pokemon_list
    ]

    # 属性行：每个精灵可有多个属性
    rows_attr = []
    for p in pokemon_list:
        attrs  = p.get("attributes", [])
        names  = p.get("attrNames", [])
        for img, name in zip(attrs, names):
            rows_attr.append({
                "pokemon_no": p["no"],
                "attr_name":  name,
                "attr_image": img,
            })

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _executemany(cur, sql_pokemon, rows_pokemon)

            # 属性先清后写，保证数据干净
            nos = [p["no"] for p in pokemon_list]
            if nos:
                placeholders = ",".join(["%s"] * len(nos))
                cur.execute(
                    f"DELETE FROM pokemon_attribute WHERE pokemon_no IN ({placeholders})",
                    nos,
                )
            if rows_attr:
                sql_attr = """
                    INSERT INTO pokemon_attribute (pokemon_no, attr_name, attr_image)
                    VALUES (%(pokemon_no)s, %(attr_name)s, %(attr_image)s)
                """
                _executemany(cur, sql_attr, rows_attr)

        conn.commit()
    finally:
        conn.close()


# ── skill ────────────────────────────────────────────────────

def upsert_skills(skills_dict: dict) -> None:
    """写入/更新技能库。"""
    sql = """
        INSERT INTO skill (name, attr, power, type, consume, skill_desc, icon)
        VALUES (%(name)s, %(attr)s, %(power)s, %(type)s, %(consume)s, %(skill_desc)s, %(icon)s)
        ON DUPLICATE KEY UPDATE
            attr       = VALUES(attr),
            power      = VALUES(power),
            type       = VALUES(type),
            consume    = VALUES(consume),
            skill_desc = VALUES(skill_desc),
            icon       = VALUES(icon)
    """
    rows = [
        {
            "name":       v.get("name", k),
            "attr":       v.get("attr", ""),
            "power":      v.get("power", 0),
            "type":       v.get("type", ""),
            "consume":    v.get("consume", 0),
            "skill_desc": v.get("desc", ""),
            "icon":       v.get("icon", ""),
        }
        for k, v in skills_dict.items()
    ]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _executemany(cur, sql, rows)
        conn.commit()
    finally:
        conn.close()


# ── pokemon_detail + pokemon_skill ──────────────────────────

def upsert_details(details_dict: dict) -> None:
    """写入/更新精灵详情（种族值、特性、克制）和技能关联。"""
    sql_detail = """
        INSERT INTO pokemon_detail
            (pokemon_name, hp, atk, matk, def_val, mdef, spd,
             trait_name, trait_desc,
             strong_against, weak_against, resist, resisted)
        VALUES
            (%(pokemon_name)s, %(hp)s, %(atk)s, %(matk)s, %(def_val)s,
             %(mdef)s, %(spd)s, %(trait_name)s, %(trait_desc)s,
             %(strong_against)s, %(weak_against)s, %(resist)s, %(resisted)s)
        ON DUPLICATE KEY UPDATE
            hp             = VALUES(hp),
            atk            = VALUES(atk),
            matk           = VALUES(matk),
            def_val        = VALUES(def_val),
            mdef           = VALUES(mdef),
            spd            = VALUES(spd),
            trait_name     = VALUES(trait_name),
            trait_desc     = VALUES(trait_desc),
            strong_against = VALUES(strong_against),
            weak_against   = VALUES(weak_against),
            resist         = VALUES(resist),
            resisted       = VALUES(resisted)
    """

    sql_skill_rel = """
        INSERT IGNORE INTO pokemon_skill (pokemon_name, skill_name, sort_order)
        VALUES (%(pokemon_name)s, %(skill_name)s, %(sort_order)s)
    """

    rows_detail = []
    rows_skill_rel = []

    for name, d in details_dict.items():
        stats    = d.get("stats", {})
        trait    = d.get("trait", {})
        restrain = d.get("restrain", {})

        rows_detail.append({
            "pokemon_name":   name,
            "hp":             stats.get("hp", 0),
            "atk":            stats.get("atk", 0),
            "matk":           stats.get("matk", 0),
            "def_val":        stats.get("def", 0),
            "mdef":           stats.get("mdef", 0),
            "spd":            stats.get("spd", 0),
            "trait_name":     trait.get("name", ""),
            "trait_desc":     trait.get("desc", ""),
            "strong_against": json.dumps(restrain.get("strongAgainst", []), ensure_ascii=False),
            "weak_against":   json.dumps(restrain.get("weakAgainst", []), ensure_ascii=False),
            "resist":         json.dumps(restrain.get("resist", []), ensure_ascii=False),
            "resisted":       json.dumps(restrain.get("resisted", []), ensure_ascii=False),
        })

        for idx, skill_name in enumerate(d.get("skills", [])):
            rows_skill_rel.append({
                "pokemon_name": name,
                "skill_name":   skill_name,
                "sort_order":   idx,
            })

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _executemany(cur, sql_detail, rows_detail)
            if rows_skill_rel:
                _executemany(cur, sql_skill_rel, rows_skill_rel)
        conn.commit()
    finally:
        conn.close()
