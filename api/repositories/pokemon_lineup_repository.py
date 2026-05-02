from db.connection import get_pool
from api.utils.media import build_friend_image_url, build_resonance_magic_icon_url, build_skill_icon_url
from api.utils.pokemon_mapper import to_attribute_item


_MEMBER_JOIN_SQL = """
    SELECT
        plm.id,
        plm.pokemon_id,
        plm.random_pk_dict_id,
        plm.sort_order,
        plm.bloodline_dict_id,
        plm.personality_id,
        plm.qual_1,
        plm.qual_2,
        plm.qual_3,
        plm.skill_1_id,
        plm.skill_2_id,
        plm.skill_3_id,
        plm.skill_4_id,
        plm.member_desc,
        p.name AS pokemon_name,
        p.image AS pokemon_image_raw,
        p.image_lc AS pokemon_image_lc,
        d.label AS bloodline_label,
        per.name AS personality_name_zh,
        s1.name AS skill_1_name,
        s1.icon AS skill_1_icon,
        s2.name AS skill_2_name,
        s2.icon AS skill_2_icon,
        s3.name AS skill_3_name,
        s3.icon AS skill_3_icon,
        s4.name AS skill_4_name,
        s4.icon AS skill_4_icon,
        dr.label AS random_pk_label
    FROM pokemon_lineup_member plm
    LEFT JOIN pokemon p ON p.id = plm.pokemon_id
    LEFT JOIN sys_dict d ON d.id = plm.bloodline_dict_id
    LEFT JOIN sys_dict dr ON dr.id = plm.random_pk_dict_id
    LEFT JOIN personality per ON per.id = plm.personality_id
    LEFT JOIN skill s1 ON s1.id = plm.skill_1_id
    LEFT JOIN skill s2 ON s2.id = plm.skill_2_id
    LEFT JOIN skill s3 ON s3.id = plm.skill_3_id
    LEFT JOIN skill s4 ON s4.id = plm.skill_4_id
    WHERE plm.lineup_id = %s
    ORDER BY plm.sort_order
"""


def _normalize_attr_token(s: str) -> str:
    s = (s or "").strip()
    if s.endswith("系"):
        return s[:-1].strip()
    return s


def _match_attribute_image_url(bloodline_label: str, attrs: list[dict]) -> str:
    if not bloodline_label or not attrs:
        return ""
    lb = bloodline_label.strip()
    ln = _normalize_attr_token(lb)
    for a in attrs:
        name = (a.get("attr_name") or "").strip()
        nn = _normalize_attr_token(name)
        img = (a.get("attr_image") or "").strip()
        if name == lb or nn == ln or lb in name or name in ln:
            return img
    return ""


async def _enrich_random_member_images(members: list[dict]) -> None:
    from api.repositories.pokemon_repository import list_attributes

    need = [
        m
        for m in members
        if m.get("pokemon_id") is None and (m.get("bloodline_label") or "").strip()
    ]
    if not need:
        return
    rows = await list_attributes()
    attrs = [to_attribute_item(r) for r in rows]
    for m in members:
        if m.get("pokemon_id") is not None:
            continue
        label = (m.get("bloodline_label") or "").strip()
        if not label:
            continue
        img = _match_attribute_image_url(label, attrs)
        if img:
            m["pokemon_image"] = img


def _build_member_row(row: dict) -> dict:
    pid = row.get("pokemon_id")
    random_pk_dict_id = row.get("random_pk_dict_id")
    if pid is not None:
        pokemon_name = row.get("pokemon_name") or ""
        pokemon_image = build_friend_image_url(row.get("pokemon_image_lc") or "", row.get("pokemon_image_raw") or "")
    else:
        pokemon_name = (row.get("random_pk_label") or "").strip()
        pokemon_image = ""
    return {
        "id": row["id"],
        "pokemon_id": pid,
        "random_pk_dict_id": random_pk_dict_id,
        "pokemon_name": pokemon_name,
        "pokemon_image": pokemon_image,
        "sort_order": row["sort_order"],
        "bloodline_dict_id": row.get("bloodline_dict_id"),
        "bloodline_label": row.get("bloodline_label") or "",
        "personality_id": row.get("personality_id"),
        "personality_name_zh": row.get("personality_name_zh") or "",
        "qual_1": row.get("qual_1") or "",
        "qual_2": row.get("qual_2") or "",
        "qual_3": row.get("qual_3") or "",
        "skill_1_id": row.get("skill_1_id"),
        "skill_1_name": row.get("skill_1_name") or "",
        "skill_1_image": build_skill_icon_url((row.get("skill_1_icon") or "").strip()),
        "skill_2_id": row.get("skill_2_id"),
        "skill_2_name": row.get("skill_2_name") or "",
        "skill_2_image": build_skill_icon_url((row.get("skill_2_icon") or "").strip()),
        "skill_3_id": row.get("skill_3_id"),
        "skill_3_name": row.get("skill_3_name") or "",
        "skill_3_image": build_skill_icon_url((row.get("skill_3_icon") or "").strip()),
        "skill_4_id": row.get("skill_4_id"),
        "skill_4_name": row.get("skill_4_name") or "",
        "skill_4_image": build_skill_icon_url((row.get("skill_4_icon") or "").strip()),
        "member_desc": row.get("member_desc") or "",
    }


async def _fetch_members(cur, lineup_id: int) -> list[dict]:
    await cur.execute(_MEMBER_JOIN_SQL, (lineup_id,))
    rows = await cur.fetchall()
    members = [_build_member_row(row) for row in rows]
    await _enrich_random_member_images(members)
    return members


async def get_lineup_by_id(lineup_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    pl.id,
                    pl.title,
                    pl.lineup_desc,
                    pl.source_type,
                    pl.resonance_magic_id,
                    rm.name AS resonance_magic_name,
                    rm.icon AS resonance_magic_icon_raw,
                    pl.sort_order,
                    pl.is_active
                FROM pokemon_lineup pl
                LEFT JOIN resonance_magic rm ON rm.id = pl.resonance_magic_id
                WHERE pl.id = %s
                """,
                (lineup_id,),
            )
            lineup = await cur.fetchone()
            if not lineup:
                return None
            members = await _fetch_members(cur, lineup_id)
            return {
                **lineup,
                "resonance_magic_name": lineup.get("resonance_magic_name") or "",
                "resonance_magic_icon": build_resonance_magic_icon_url((lineup.get("resonance_magic_icon_raw") or "").strip()),
                "members": members,
            }


async def list_lineups_paginated(
    keyword: str = "",
    source_type: str = "",
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    conditions: list[str] = []
    params: list = []

    kw = (keyword or "").strip()
    if kw:
        conditions.append("title ILIKE %s")
        params.append(f"%{kw}%")
    st = (source_type or "").strip()
    if st:
        conditions.append("source_type = %s")
        params.append(st)
    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(is_active)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) AS cnt FROM pokemon_lineup {where_sql}", params)
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT
                    pl.id,
                    pl.title,
                    pl.source_type,
                    pl.resonance_magic_id,
                    rm.name AS resonance_magic_name,
                    rm.icon AS resonance_magic_icon_raw,
                    pl.sort_order,
                    pl.is_active,
                    COUNT(plm.id) AS member_count
                FROM pokemon_lineup pl
                LEFT JOIN resonance_magic rm ON rm.id = pl.resonance_magic_id
                LEFT JOIN pokemon_lineup_member plm ON plm.lineup_id = pl.id
                {where_sql}
                GROUP BY pl.id, rm.id, rm.name, rm.icon
                ORDER BY pl.sort_order DESC, pl.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = await cur.fetchall()
            items = [
                {
                    **row,
                    "resonance_magic_name": row.get("resonance_magic_name") or "",
                    "resonance_magic_icon": build_resonance_magic_icon_url((row.get("resonance_magic_icon_raw") or "").strip()),
                }
                for row in rows
            ]
            return total, items


async def create_lineup(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pokemon_lineup (title, lineup_desc, source_type, resonance_magic_id, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["title"],
                    payload["lineup_desc"],
                    payload["source_type"],
                    payload.get("resonance_magic_id"),
                    payload["sort_order"],
                    payload["is_active"],
                ),
            )
            lineup = await cur.fetchone()
            lineup_id = lineup["id"]

            for member in payload.get("members", []):
                await cur.execute(
                    """
                    INSERT INTO pokemon_lineup_member (
                        lineup_id, sort_order, pokemon_id, random_pk_dict_id, bloodline_dict_id, personality_id,
                        qual_1, qual_2, qual_3,
                        skill_1_id, skill_2_id, skill_3_id, skill_4_id, member_desc
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lineup_id,
                        member["sort_order"],
                        member.get("pokemon_id"),
                        member.get("random_pk_dict_id"),
                        member.get("bloodline_dict_id"),
                        member.get("personality_id"),
                        member.get("qual_1", ""),
                        member.get("qual_2", ""),
                        member.get("qual_3", ""),
                        member.get("skill_1_id"),
                        member.get("skill_2_id"),
                        member.get("skill_3_id"),
                        member.get("skill_4_id"),
                        member.get("member_desc", ""),
                    ),
                )
        await conn.commit()
    return await get_lineup_by_id(lineup_id)


async def update_lineup(lineup_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE pokemon_lineup
                SET title = %s, lineup_desc = %s, source_type = %s, resonance_magic_id = %s, sort_order = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (
                    payload["title"],
                    payload["lineup_desc"],
                    payload["source_type"],
                    payload.get("resonance_magic_id"),
                    payload["sort_order"],
                    payload["is_active"],
                    lineup_id,
                ),
            )
            row = await cur.fetchone()
            if not row:
                await conn.rollback()
                return None

            await cur.execute("DELETE FROM pokemon_lineup_member WHERE lineup_id = %s", (lineup_id,))

            for member in payload.get("members", []):
                await cur.execute(
                    """
                    INSERT INTO pokemon_lineup_member (
                        lineup_id, sort_order, pokemon_id, random_pk_dict_id, bloodline_dict_id, personality_id,
                        qual_1, qual_2, qual_3,
                        skill_1_id, skill_2_id, skill_3_id, skill_4_id, member_desc
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lineup_id,
                        member["sort_order"],
                        member.get("pokemon_id"),
                        member.get("random_pk_dict_id"),
                        member.get("bloodline_dict_id"),
                        member.get("personality_id"),
                        member.get("qual_1", ""),
                        member.get("qual_2", ""),
                        member.get("qual_3", ""),
                        member.get("skill_1_id"),
                        member.get("skill_2_id"),
                        member.get("skill_3_id"),
                        member.get("skill_4_id"),
                        member.get("member_desc", ""),
                    ),
                )
        await conn.commit()
    return await get_lineup_by_id(lineup_id)


async def delete_lineup(lineup_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM pokemon_lineup WHERE id = %s", (lineup_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def list_active_lineups(source_type: str = "", ids: list[int] | None = None) -> list[dict]:
    pool = await get_pool()
    conditions = ["pl.is_active = TRUE"]
    params: list = []

    st = (source_type or "").strip()
    if st:
        conditions.append("pl.source_type = %s")
        params.append(st)

    if ids:
        placeholders = ", ".join(["%s"] * len(ids))
        conditions.append(f"pl.id IN ({placeholders})")
        params.extend(ids)

    where_sql = " AND ".join(conditions)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT pl.id, pl.title, pl.lineup_desc, pl.source_type, pl.sort_order, pl.is_active
                     , pl.resonance_magic_id, rm.name AS resonance_magic_name, rm.icon AS resonance_magic_icon_raw
                FROM pokemon_lineup pl
                LEFT JOIN resonance_magic rm ON rm.id = pl.resonance_magic_id
                WHERE {where_sql}
                ORDER BY pl.sort_order DESC, pl.id DESC
                """,
                params,
            )
            lineups = await cur.fetchall()

            result = []
            for lineup in lineups:
                members = await _fetch_members(cur, lineup["id"])
                result.append(
                    {
                        **lineup,
                        "resonance_magic_name": lineup.get("resonance_magic_name") or "",
                        "resonance_magic_icon": build_resonance_magic_icon_url((lineup.get("resonance_magic_icon_raw") or "").strip()),
                        "members": members,
                    }
                )
            return result


async def search_pokemon(keyword: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, name, image, image_lc
                FROM pokemon
                WHERE name LIKE %s
                ORDER BY name, id
                LIMIT %s
                """,
                (f"%{keyword}%", limit),
            )
            rows = await cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "image": build_friend_image_url(row.get("image_lc") or "", row.get("image") or ""),
                }
                for row in rows
            ]


async def search_skills(
    keyword: str,
    pokemon_id: int,
    exclude_skill_ids: list[int] | None = None,
) -> list[dict]:
    pool = await get_pool()
    params: list = [pokemon_id]
    conditions = ["ps.pokemon_id = %s"]

    kw = (keyword or "").strip()
    if kw:
        conditions.append("s.name LIKE %s")
        params.append(f"%{kw}%")

    cleaned_excludes = [int(sid) for sid in (exclude_skill_ids or []) if sid]
    if cleaned_excludes:
        placeholders = ", ".join(["%s"] * len(cleaned_excludes))
        conditions.append(f"s.id NOT IN ({placeholders})")
        params.extend(cleaned_excludes)

    where_sql = " AND ".join(conditions)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT s.id, s.name, s.icon
                FROM skill s
                JOIN pokemon_skill ps ON ps.skill_id = s.id
                WHERE {where_sql}
                ORDER BY ps.sort_order, s.name, s.id
                """,
                params,
            )
            rows = await cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "image": build_skill_icon_url((row.get("icon") or "").strip()),
                }
                for row in rows
            ]
