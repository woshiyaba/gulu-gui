from psycopg import AsyncConnection

from db.connection import get_pool
from api.utils.media import build_friend_image_url, build_image_url, build_skill_icon_url


OPS_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS ops_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'editor',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(50) NOT NULL DEFAULT '',
    action VARCHAR(20) NOT NULL,
    before_json JSONB,
    after_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS banner (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL DEFAULT '',
    image_url VARCHAR(500) NOT NULL,
    link_type VARCHAR(50) NOT NULL DEFAULT '',
    link_param VARCHAR(255) NOT NULL DEFAULT '',
    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS starlight_duel_episode (
    id SERIAL PRIMARY KEY,
    episode_number INT NOT NULL UNIQUE,
    title VARCHAR(100) NOT NULL DEFAULT '',
    strategy_text TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS starlight_duel_pet (
    id SERIAL PRIMARY KEY,
    episode_id INT NOT NULL REFERENCES starlight_duel_episode(id) ON DELETE CASCADE,
    pet_id INT NOT NULL REFERENCES pokemon(id),
    sort_order INT NOT NULL DEFAULT 1,
    skill_1_id INT REFERENCES skill(id),
    skill_2_id INT REFERENCES skill(id),
    skill_3_id INT REFERENCES skill(id),
    skill_4_id INT REFERENCES skill(id),
    UNIQUE (episode_id, sort_order)
);
"""


async def ensure_ops_tables() -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(OPS_TABLES_SQL)
        await conn.commit()


async def get_user_by_username(username: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, password_hash, nickname, role, is_active
                FROM ops_user
                WHERE username = %s
                """,
                (username,),
            )
            return await cur.fetchone()


async def get_user_by_id(user_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, password_hash, nickname, role, is_active
                FROM ops_user
                WHERE id = %s
                """,
                (user_id,),
            )
            return await cur.fetchone()


async def list_ops_users() -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, password_hash, nickname, role, is_active
                FROM ops_user
                ORDER BY id DESC
                """
            )
            return await cur.fetchall()


async def count_ops_users() -> int:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) AS cnt FROM ops_user")
            row = await cur.fetchone() or {}
            return int(row.get("cnt", 0))


async def create_ops_user(
    username: str,
    password_hash: str,
    nickname: str,
    role: str,
) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ops_user (username, password_hash, nickname, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                (username, password_hash, nickname, role),
            )
        await conn.commit()


async def create_ops_user_with_return(
    username: str,
    password_hash: str,
    nickname: str,
    role: str,
) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ops_user (username, password_hash, nickname, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id, username, password_hash, nickname, role, is_active
                """,
                (username, password_hash, nickname, role),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update_ops_user_by_admin(
    user_id: int,
    nickname: str,
    role: str,
    password_hash: str | None = None,
) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if password_hash is None:
                await cur.execute(
                    """
                    UPDATE ops_user
                    SET nickname = %s,
                        role = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, password_hash, nickname, role, is_active
                    """,
                    (nickname, role, user_id),
                )
            else:
                await cur.execute(
                    """
                    UPDATE ops_user
                    SET nickname = %s,
                        role = %s,
                        password_hash = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, password_hash, nickname, role, is_active
                    """,
                    (nickname, role, password_hash, user_id),
                )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_ops_user(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM ops_user WHERE id = %s", (user_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def update_ops_user_profile(
    user_id: int,
    nickname: str,
    password_hash: str | None = None,
) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if password_hash is None:
                await cur.execute(
                    """
                    UPDATE ops_user
                    SET nickname = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, password_hash, nickname, role, is_active
                    """,
                    (nickname, user_id),
                )
            else:
                await cur.execute(
                    """
                    UPDATE ops_user
                    SET nickname = %s,
                        password_hash = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, password_hash, nickname, role, is_active
                    """,
                    (nickname, password_hash, user_id),
                )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def list_dicts(
    dict_type: str = "",
    code: str = "",
    label: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list[str] = []
    if dict_type:
        conditions.append("dict_type = %s")
        params.append(dict_type)
    if code:
        conditions.append("code LIKE %s")
        params.append(f"%{code}%")
    if label:
        conditions.append("label LIKE %s")
        params.append(f"%{label}%")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM sys_dict
                {where_clause}
                """,
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT id, dict_type, code, label, sort_order
                FROM sys_dict
                {where_clause}
                ORDER BY dict_type, sort_order, id
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            items = await cur.fetchall()
            return total, items


async def list_dicts_all(dict_type: str = "", code: str = "", label: str = "") -> list[dict]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list[str] = []
    if dict_type:
        conditions.append("dict_type = %s")
        params.append(dict_type)
    if code:
        conditions.append("code LIKE %s")
        params.append(f"%{code}%")
    if label:
        conditions.append("label LIKE %s")
        params.append(f"%{label}%")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id, dict_type, code, label, sort_order
                FROM sys_dict
                {where_clause}
                ORDER BY dict_type, sort_order, id
                """,
                params,
            )
            return await cur.fetchall()


async def get_dict_by_id(dict_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, dict_type, code, label, sort_order FROM sys_dict WHERE id = %s",
                (dict_id,),
            )
            return await cur.fetchone()


async def create_dict_item(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sys_dict (dict_type, code, label, sort_order)
                VALUES (%s, %s, %s, %s)
                RETURNING id, dict_type, code, label, sort_order
                """,
                (payload["dict_type"], payload["code"], payload["label"], payload["sort_order"]),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update_dict_item(dict_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE sys_dict
                SET dict_type = %s, code = %s, label = %s, sort_order = %s
                WHERE id = %s
                RETURNING id, dict_type, code, label, sort_order
                """,
                (
                    payload["dict_type"],
                    payload["code"],
                    payload["label"],
                    payload["sort_order"],
                    dict_id,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_dict_item(dict_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM sys_dict WHERE id = %s", (dict_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def create_audit_log(
    user_id: int,
    resource_type: str,
    resource_id: str,
    action: str,
    before_json: dict | None,
    after_json: dict | None,
) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ops_audit_log (user_id, resource_type, resource_id, action, before_json, after_json)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    user_id,
                    resource_type,
                    resource_id,
                    action,
                    None if before_json is None else __import__("json").dumps(before_json, ensure_ascii=False),
                    None if after_json is None else __import__("json").dumps(after_json, ensure_ascii=False),
                ),
            )
        await conn.commit()


async def list_pokemon_for_ops(
    keyword: str = "",
    no: str = "",
    name: str = "",
    attr_id: int | None = None,
    egg_group: str = "",
    type_code: str = "",
    form_code: str = "",
    trait_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list = []
    if keyword:
        conditions.append("(p.name LIKE %s OR p.no LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if no:
        conditions.append("p.no = %s")
        params.append(no)
    if name:
        conditions.append("p.name LIKE %s")
        params.append(f"%{name}%")
    if attr_id:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM pokemon_attribute pa2
                WHERE pa2.pokemon_id = p.id AND pa2.attr_id = %s
            )
            """
        )
        params.append(attr_id)
    if egg_group:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM pokemon_egg_group peg2
                WHERE peg2.pokemon_id = p.id AND peg2.group_name = %s
            )
            """
        )
        params.append(egg_group)
    if type_code:
        conditions.append("p.type = %s")
        params.append(type_code)
    if form_code:
        conditions.append("p.form = %s")
        params.append(form_code)
    if trait_id:
        conditions.append("p.trait_id = %s")
        params.append(trait_id)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM pokemon p
                {where_clause}
                """,
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT
                    p.id, p.no, p.name, p.type_name, p.form_name,
                    COALESCE(pt.name, '') AS trait_name,
                    COALESCE(string_agg(DISTINCT a.name, ','), '') AS attr_names,
                    COALESCE(string_agg(DISTINCT peg.group_name, ','), '') AS egg_group_names
                FROM pokemon p
                LEFT JOIN pokemon_trait pt ON pt.id = p.trait_id
                LEFT JOIN pokemon_attribute pa ON pa.pokemon_id = p.id
                LEFT JOIN attribute a ON a.id = pa.attr_id
                LEFT JOIN pokemon_egg_group peg ON peg.pokemon_id = p.id
                {where_clause}
                GROUP BY p.id, p.no, p.name, p.type_name, p.form_name, pt.name
                ORDER BY p.no, p.id
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = await cur.fetchall()
            return total, rows


async def get_pokemon_detail_for_ops(pokemon_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    id, no, name, image, type, type_name, form, form_name, egg_group, trait_id,
                    detail_url, image_lc, chain_id,
                    hp, atk, matk, def_val, mdef, spd, total_race, obtain_method
                FROM pokemon
                WHERE id = %s
                """,
                (pokemon_id,),
            )
            base = await cur.fetchone()
            if not base:
                return None

            await cur.execute(
                "SELECT attr_id FROM pokemon_attribute WHERE pokemon_id = %s ORDER BY id",
                (pokemon_id,),
            )
            attr_rows = await cur.fetchall()

            await cur.execute(
                "SELECT group_name FROM pokemon_egg_group WHERE pokemon_id = %s ORDER BY id",
                (pokemon_id,),
            )
            egg_rows = await cur.fetchall()

            await cur.execute(
                "SELECT skill_id, type, sort_order FROM pokemon_skill WHERE pokemon_id = %s ORDER BY sort_order, id",
                (pokemon_id,),
            )
            skill_rows = await cur.fetchall()

            return {
                **base,
                "attribute_ids": [row["attr_id"] for row in attr_rows],
                "egg_groups": [row["group_name"] for row in egg_rows],
                "skills": [
                    {
                        "skill_id": row["skill_id"],
                        "type": row["type"],
                        "sort_order": row["sort_order"],
                    }
                    for row in skill_rows
                ],
            }


async def save_pokemon_for_ops(payload: dict, pokemon_id: int | None = None) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if pokemon_id is None:
                await cur.execute(
                    """
                    INSERT INTO pokemon (
                        no, name, image, type, type_name, form, form_name, egg_group, trait_id,
                        detail_url, image_lc, chain_id,
                        hp, atk, matk, def_val, mdef, spd, total_race, obtain_method
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        payload["no"],
                        payload["name"],
                        payload.get("image", ""),
                        payload.get("type", ""),
                        payload.get("type_name", ""),
                        payload.get("form", ""),
                        payload.get("form_name", ""),
                        payload.get("egg_group", ""),
                        payload["trait_id"],
                        payload.get("detail_url", ""),
                        payload.get("image_lc", ""),
                        payload.get("chain_id"),
                        payload.get("hp", 0),
                        payload.get("atk", 0),
                        payload.get("matk", 0),
                        payload.get("def_val", 0),
                        payload.get("mdef", 0),
                        payload.get("spd", 0),
                        payload.get("total_race", 0),
                        payload.get("obtain_method", ""),
                    ),
                )
                row = await cur.fetchone()
                pokemon_id = row["id"]
            else:
                await cur.execute(
                    """
                    UPDATE pokemon
                    SET no = %s, name = %s, image = %s, type = %s, type_name = %s, form = %s, form_name = %s,
                        egg_group = %s, trait_id = %s, detail_url = %s, image_lc = %s, chain_id = %s,
                        hp = %s, atk = %s, matk = %s, def_val = %s, mdef = %s, spd = %s, total_race = %s, obtain_method = %s
                    WHERE id = %s
                    """,
                    (
                        payload["no"],
                        payload["name"],
                        payload.get("image", ""),
                        payload.get("type", ""),
                        payload.get("type_name", ""),
                        payload.get("form", ""),
                        payload.get("form_name", ""),
                        payload.get("egg_group", ""),
                        payload["trait_id"],
                        payload.get("detail_url", ""),
                        payload.get("image_lc", ""),
                        payload.get("chain_id"),
                        payload.get("hp", 0),
                        payload.get("atk", 0),
                        payload.get("matk", 0),
                        payload.get("def_val", 0),
                        payload.get("mdef", 0),
                        payload.get("spd", 0),
                        payload.get("total_race", 0),
                        payload.get("obtain_method", ""),
                        pokemon_id,
                    ),
                )

            await cur.execute("DELETE FROM pokemon_attribute WHERE pokemon_id = %s", (pokemon_id,))
            for attr_id in payload.get("attribute_ids", []):
                await cur.execute(
                    "INSERT INTO pokemon_attribute (pokemon_id, attr_id) VALUES (%s, %s)",
                    (pokemon_id, attr_id),
                )

            await cur.execute("DELETE FROM pokemon_egg_group WHERE pokemon_id = %s", (pokemon_id,))
            for group_name in payload.get("egg_groups", []):
                await cur.execute(
                    "INSERT INTO pokemon_egg_group (pokemon_id, group_name) VALUES (%s, %s)",
                    (pokemon_id, group_name),
                )

            await cur.execute("DELETE FROM pokemon_skill WHERE pokemon_id = %s", (pokemon_id,))
            for skill in payload.get("skills", []):
                await cur.execute(
                    """
                    INSERT INTO pokemon_skill (pokemon_id, skill_id, type, sort_order)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        pokemon_id,
                        skill["skill_id"],
                        skill.get("type", "原生技能"),
                        skill.get("sort_order", 0),
                    ),
                )
        await conn.commit()
    return await get_pokemon_detail_for_ops(pokemon_id)


async def delete_pokemon_for_ops(pokemon_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM pokemon WHERE id = %s", (pokemon_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def list_pokemon_options_for_ops() -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, name FROM attribute ORDER BY sort_order, id")
            attrs = await cur.fetchall()
            await cur.execute("SELECT id, name FROM pokemon_trait ORDER BY sort_order, id")
            traits = await cur.fetchall()
            await cur.execute("SELECT id, name, icon FROM skill ORDER BY name, id")
            skills = await cur.fetchall()
            return {
                "attributes": [{"id": row["id"], "name": row["name"]} for row in attrs],
                "traits": [{"id": row["id"], "name": row["name"]} for row in traits],
                "skills": [
                    {"id": row["id"], "name": row["name"], "icon": build_image_url(row.get("icon") or "")}
                    for row in skills
                ],
            }


async def get_pokemon_evolution_chain_for_ops(pokemon_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, name, chain_id FROM pokemon WHERE id = %s", (pokemon_id,))
            pokemon = await cur.fetchone()
            if not pokemon:
                return None
            chain_id = pokemon.get("chain_id")
            if not chain_id:
                return {"chain_id": None, "steps": []}
            await cur.execute(
                """
                SELECT sort_order, pokemon_name, evolution_condition
                FROM evolution_chain
                WHERE chain_id = %s
                ORDER BY sort_order, id
                """,
                (chain_id,),
            )
            rows = await cur.fetchall()
            steps = [
                {
                    "sort_order": row["sort_order"],
                    "pokemon_name": row["pokemon_name"],
                    "evolution_condition": row.get("evolution_condition") or "",
                }
                for row in rows
            ]
            enriched_steps = await _enrich_evolution_steps(conn, steps)
            return {
                "chain_id": chain_id,
                "steps": enriched_steps,
            }


async def save_pokemon_evolution_chain_for_ops(pokemon_id: int, steps: list[dict]) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, name, chain_id FROM pokemon WHERE id = %s", (pokemon_id,))
            pokemon = await cur.fetchone()
            if not pokemon:
                return None

            step_names = sorted({
                (step.get("pokemon_name") or "").strip()
                for step in steps
                if (step.get("pokemon_name") or "").strip()
            })

            existing_chain_ids: list[int] = []
            matched_pokemon_ids: list[int] = []
            if step_names:
                placeholders = ", ".join(["%s"] * len(step_names))
                await cur.execute(
                    f"SELECT id, chain_id FROM pokemon WHERE name IN ({placeholders})",
                    step_names,
                )
                for row in await cur.fetchall():
                    matched_pokemon_ids.append(int(row["id"]))
                    if row.get("chain_id") is not None:
                        existing_chain_ids.append(int(row["chain_id"]))

            current_chain_id = pokemon.get("chain_id")
            # 优先复用 steps 中已存在的 chain_id（按出现频次取最常见的一个）
            chain_id: int | None = None
            if existing_chain_ids:
                from collections import Counter
                chain_id = Counter(existing_chain_ids).most_common(1)[0][0]
            elif current_chain_id is not None:
                chain_id = int(current_chain_id)

            if chain_id is None:
                await cur.execute("SELECT COALESCE(MAX(chain_id), 0) + 1 AS next_chain_id FROM evolution_chain")
                next_row = await cur.fetchone() or {}
                chain_id = int(next_row.get("next_chain_id") or 1)

            # 把当前精灵 + 所有 steps 中匹配到的 pokemon 行统一挂到这条 chain 上
            ids_to_attach = sorted(set(matched_pokemon_ids) | {pokemon_id})
            placeholders = ", ".join(["%s"] * len(ids_to_attach))
            await cur.execute(
                f"UPDATE pokemon SET chain_id = %s WHERE id IN ({placeholders})",
                [chain_id, *ids_to_attach],
            )

            await cur.execute("DELETE FROM evolution_chain WHERE chain_id = %s", (chain_id,))
            for idx, step in enumerate(steps, start=1):
                pokemon_name = (step.get("pokemon_name") or "").strip()
                if not pokemon_name:
                    continue
                await cur.execute(
                    """
                    INSERT INTO evolution_chain (chain_id, sort_order, pokemon_name, evolution_condition)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        chain_id,
                        int(step.get("sort_order") or idx),
                        pokemon_name,
                        (step.get("evolution_condition") or "").strip(),
                    ),
                )
        await conn.commit()
    return await get_pokemon_evolution_chain_for_ops(pokemon_id)


async def search_evolution_chain_for_ops(keyword: str) -> dict | None:
    """根据关键词查找一条进化链。

    匹配优先级：
      1. evolution_chain.pokemon_name 精确等于 kw
      2. pokemon.name 精确等于 kw 且已挂 chain_id
      3. evolution_chain.pokemon_name LIKE %kw%
      4. pokemon.name LIKE %kw% 且已挂 chain_id
    命中后返回该 chain_id 的完整链。
    """
    pool = await get_pool()
    kw = keyword.strip()
    if not kw:
        return None

    queries: list[tuple[str, tuple]] = [
        (
            "SELECT chain_id FROM evolution_chain WHERE pokemon_name = %s ORDER BY chain_id LIMIT 1",
            (kw,),
        ),
        (
            "SELECT chain_id FROM pokemon WHERE chain_id IS NOT NULL AND name = %s ORDER BY id LIMIT 1",
            (kw,),
        ),
        (
            "SELECT chain_id FROM evolution_chain WHERE pokemon_name LIKE %s ORDER BY chain_id LIMIT 1",
            (f"%{kw}%",),
        ),
        (
            "SELECT chain_id FROM pokemon WHERE chain_id IS NOT NULL AND name LIKE %s ORDER BY name, id LIMIT 1",
            (f"%{kw}%",),
        ),
    ]

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            chain_id: int | None = None
            for sql, params in queries:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                if row and row.get("chain_id") is not None:
                    chain_id = int(row["chain_id"])
                    break
            if chain_id is None:
                return None

            await cur.execute(
                """
                SELECT sort_order, pokemon_name, evolution_condition
                FROM evolution_chain
                WHERE chain_id = %s
                ORDER BY sort_order, id
                """,
                (chain_id,),
            )
            rows = await cur.fetchall()
            steps = [
                {
                    "sort_order": row["sort_order"],
                    "pokemon_name": row["pokemon_name"],
                    "evolution_condition": row.get("evolution_condition") or "",
                }
                for row in rows
            ]
            enriched_steps = await _enrich_evolution_steps(conn, steps)
            return {"chain_id": chain_id, "steps": enriched_steps}


def _skill_row_to_item(row: dict) -> dict:
    icon = (row.get("icon") or "").strip()
    return {
        "id": row["id"],
        "name": row.get("name") or "",
        "attr": row.get("attr_name") or "",
        "type": row.get("type") or "",
        "power": int(row.get("power") or 0),
        "consume": int(row.get("consume") or 0),
        "skill_desc": row.get("skill_desc") or "",
        "icon": icon,
        "icon_url": build_skill_icon_url(icon),
    }


_SKILL_BASE_SELECT = """
    SELECT s.id, s.name, COALESCE(a.name, '') AS attr_name, s.type,
           s.power, s.consume, s.skill_desc, s.icon
    FROM skill s
    LEFT JOIN attribute a ON a.id = s.attr_id
"""


async def _resolve_attr_id(cur, attr_name: str) -> int | None:
    attr_name = (attr_name or "").strip()
    if not attr_name:
        return None
    await cur.execute("SELECT id FROM attribute WHERE name = %s", (attr_name,))
    row = await cur.fetchone()
    return int(row["id"]) if row else None


async def list_skills_for_ops(
    keyword: str = "",
    attr: str = "",
    type_: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list = []
    if keyword:
        conditions.append("s.name LIKE %s")
        params.append(f"%{keyword}%")
    if attr:
        conditions.append("a.name = %s")
        params.append(attr)
    if type_:
        conditions.append("s.type = %s")
        params.append(type_)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM skill s
                LEFT JOIN attribute a ON a.id = s.attr_id
                {where_clause}
                """,
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))
            await cur.execute(
                f"""
                {_SKILL_BASE_SELECT}
                {where_clause}
                ORDER BY s.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = await cur.fetchall()
            return total, [_skill_row_to_item(row) for row in rows]


async def get_skill_for_ops(skill_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{_SKILL_BASE_SELECT} WHERE s.id = %s",
                (skill_id,),
            )
            row = await cur.fetchone()
            return _skill_row_to_item(row) if row else None


async def get_skill_by_name(name: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name FROM skill WHERE name = %s",
                (name,),
            )
            return await cur.fetchone()


async def create_skill_for_ops(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            attr_id = await _resolve_attr_id(cur, payload.get("attr", ""))
            await cur.execute(
                """
                INSERT INTO skill (name, attr_id, type, power, consume, skill_desc, icon)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["name"],
                    attr_id,
                    payload.get("type", ""),
                    int(payload.get("power") or 0),
                    int(payload.get("consume") or 0),
                    payload.get("skill_desc") or "",
                    payload.get("icon") or "",
                ),
            )
            row = await cur.fetchone()
            skill_id = int(row["id"])
        await conn.commit()
    detail = await get_skill_for_ops(skill_id)
    assert detail is not None
    return detail


async def update_skill_for_ops(skill_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            attr_id = await _resolve_attr_id(cur, payload.get("attr", ""))
            await cur.execute(
                """
                UPDATE skill
                SET name = %s, attr_id = %s, type = %s, power = %s, consume = %s, skill_desc = %s, icon = %s
                WHERE id = %s
                """,
                (
                    payload["name"],
                    attr_id,
                    payload.get("type", ""),
                    int(payload.get("power") or 0),
                    int(payload.get("consume") or 0),
                    payload.get("skill_desc") or "",
                    payload.get("icon") or "",
                    skill_id,
                ),
            )
            if cur.rowcount == 0:
                return None
        await conn.commit()
    return await get_skill_for_ops(skill_id)


async def delete_skill_for_ops(skill_id: int, *, force: bool = False) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if force:
                await cur.execute("DELETE FROM pokemon_skill WHERE skill_id = %s", (skill_id,))
            await cur.execute("DELETE FROM skill WHERE id = %s", (skill_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def list_skill_usages_for_ops(skill_id: int) -> tuple[int, list[dict]]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT p.id, p.no, p.name, ps.type, ps.sort_order
                FROM pokemon_skill ps
                JOIN pokemon p ON p.id = ps.pokemon_id
                WHERE ps.skill_id = %s
                ORDER BY p.no, p.id
                """,
                (skill_id,),
            )
            rows = await cur.fetchall()
            items = [
                {
                    "id": row["id"],
                    "no": row.get("no") or "",
                    "name": row.get("name") or "",
                    "type": row.get("type") or "原生技能",
                    "sort_order": int(row.get("sort_order") or 0),
                }
                for row in rows
            ]
            return len(items), items


async def list_skill_options_for_ops() -> dict:
    """返回技能 attr（属性名）与 type 的可选值。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT name FROM attribute ORDER BY sort_order, id")
            attrs = [row["name"] for row in await cur.fetchall() if row.get("name")]

            await cur.execute(
                "SELECT label FROM sys_dict WHERE dict_type = 'skill_type' ORDER BY sort_order, id"
            )
            type_rows = await cur.fetchall()
            types = [row["label"] for row in type_rows if row.get("label")]
            if not types:
                await cur.execute(
                    "SELECT DISTINCT type FROM skill WHERE COALESCE(type, '') <> '' ORDER BY type"
                )
                types = [row["type"] for row in await cur.fetchall()]
    return {"attrs": attrs, "types": types}


# ---------- 技能石维护 ----------

_SKILL_STONE_BASE_SELECT = """
    SELECT ss.id, ss.skill_id, ss.obtain_method,
           s.name AS skill_name,
           COALESCE(a.name, '') AS skill_attr,
           s.type AS skill_type,
           s.icon AS skill_icon
    FROM skill_stone ss
    JOIN skill s ON s.id = ss.skill_id
    LEFT JOIN attribute a ON a.id = s.attr_id
"""


def _skill_stone_row_to_item(row: dict) -> dict:
    icon = (row.get("skill_icon") or "").strip()
    return {
        "id": row["id"],
        "skill_id": row["skill_id"],
        "skill_name": row.get("skill_name") or "",
        "skill_attr": row.get("skill_attr") or "",
        "skill_type": row.get("skill_type") or "",
        "skill_icon": icon,
        "skill_icon_url": build_skill_icon_url(icon),
        "obtain_method": row.get("obtain_method") or "",
    }


async def list_skill_stones_for_ops(
    keyword: str = "",
    attr: str = "",
    type_: str = "",
    obtain_keyword: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list = []
    if keyword:
        conditions.append("s.name LIKE %s")
        params.append(f"%{keyword}%")
    if attr:
        conditions.append("a.name = %s")
        params.append(attr)
    if type_:
        conditions.append("s.type = %s")
        params.append(type_)
    if obtain_keyword:
        conditions.append("ss.obtain_method LIKE %s")
        params.append(f"%{obtain_keyword}%")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM skill_stone ss
                JOIN skill s ON s.id = ss.skill_id
                LEFT JOIN attribute a ON a.id = s.attr_id
                {where_clause}
                """,
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))
            await cur.execute(
                f"""
                {_SKILL_STONE_BASE_SELECT}
                {where_clause}
                ORDER BY ss.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = await cur.fetchall()
            return total, [_skill_stone_row_to_item(row) for row in rows]


async def get_skill_stone_for_ops(stone_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{_SKILL_STONE_BASE_SELECT} WHERE ss.id = %s",
                (stone_id,),
            )
            row = await cur.fetchone()
            return _skill_stone_row_to_item(row) if row else None


async def get_skill_stone_by_skill_id(skill_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, skill_id FROM skill_stone WHERE skill_id = %s",
                (skill_id,),
            )
            return await cur.fetchone()


async def create_skill_stone_for_ops(skill_id: int, obtain_method: str) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO skill_stone (skill_id, obtain_method)
                VALUES (%s, %s)
                RETURNING id
                """,
                (skill_id, obtain_method),
            )
            row = await cur.fetchone()
            stone_id = int(row["id"])
        await conn.commit()
    detail = await get_skill_stone_for_ops(stone_id)
    assert detail is not None
    return detail


async def update_skill_stone_for_ops(stone_id: int, obtain_method: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE skill_stone SET obtain_method = %s WHERE id = %s",
                (obtain_method, stone_id),
            )
            if cur.rowcount == 0:
                return None
        await conn.commit()
    return await get_skill_stone_for_ops(stone_id)


async def delete_skill_stone_for_ops(stone_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM skill_stone WHERE id = %s", (stone_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def list_available_skills_for_stone(keyword: str = "", limit: int = 30) -> list[dict]:
    """返回尚未挂技能石的技能候选。"""
    pool = await get_pool()
    conditions = ["NOT EXISTS (SELECT 1 FROM skill_stone ss WHERE ss.skill_id = s.id)"]
    params: list = []
    if keyword:
        conditions.append("s.name LIKE %s")
        params.append(f"%{keyword}%")
    where_clause = "WHERE " + " AND ".join(conditions)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT s.id, s.name, COALESCE(a.name, '') AS attr, s.type, s.icon
                FROM skill s
                LEFT JOIN attribute a ON a.id = s.attr_id
                {where_clause}
                ORDER BY s.name, s.id
                LIMIT %s
                """,
                [*params, limit],
            )
            rows = await cur.fetchall()
    items: list[dict] = []
    for row in rows:
        icon = (row.get("icon") or "").strip()
        items.append(
            {
                "id": row["id"],
                "name": row.get("name") or "",
                "attr": row.get("attr") or "",
                "type": row.get("type") or "",
                "icon": icon,
                "icon_url": build_skill_icon_url(icon),
            }
        )
    return items


async def _enrich_evolution_steps(conn: AsyncConnection, steps: list[dict]) -> list[dict]:
    names = sorted({(step.get("pokemon_name") or "").strip() for step in steps if (step.get("pokemon_name") or "").strip()})
    if not names:
        return []
    placeholders = ", ".join(["%s"] * len(names))
    sql = f"""
        SELECT name, image, image_lc
        FROM pokemon
        WHERE name IN ({placeholders})
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, names)
        rows = await cur.fetchall()
    mapping = {
        (row.get("name") or "").strip(): build_friend_image_url(row.get("image_lc", ""), row.get("image", ""))
        for row in rows
    }
    enriched: list[dict] = []
    for step in steps:
        pokemon_name = (step.get("pokemon_name") or "").strip()
        image_url = mapping.get(pokemon_name, "")
        enriched.append(
            {
                "sort_order": int(step.get("sort_order") or 0),
                "pokemon_name": pokemon_name,
                "evolution_condition": (step.get("evolution_condition") or "").strip(),
                "image_url": image_url,
                "matched": bool(image_url),
            }
        )
    return enriched
