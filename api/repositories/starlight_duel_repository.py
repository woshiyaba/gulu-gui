from db.connection import get_pool
from api.utils.media import build_friend_image_url


_PET_JOIN_SQL = """
    SELECT
        sdp.id, sdp.pet_id, sdp.sort_order,
        sdp.skill_1_id, sdp.skill_2_id, sdp.skill_3_id, sdp.skill_4_id,
        p.name AS pet_name,
        p.image AS pet_image_raw,
        p.image_lc AS pet_image_lc,
        s1.name AS skill_1_name,
        s2.name AS skill_2_name,
        s3.name AS skill_3_name,
        s4.name AS skill_4_name
    FROM starlight_duel_pet sdp
    JOIN pokemon p ON p.id = sdp.pet_id
    LEFT JOIN skill s1 ON s1.id = sdp.skill_1_id
    LEFT JOIN skill s2 ON s2.id = sdp.skill_2_id
    LEFT JOIN skill s3 ON s3.id = sdp.skill_3_id
    LEFT JOIN skill s4 ON s4.id = sdp.skill_4_id
    WHERE sdp.episode_id = %s
    ORDER BY sdp.sort_order
"""


def _build_pet_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "pet_id": row["pet_id"],
        "pet_name": row.get("pet_name", ""),
        "pet_image": build_friend_image_url(row.get("pet_image_lc") or "", row.get("pet_image_raw") or ""),
        "sort_order": row["sort_order"],
        "skill_1_id": row.get("skill_1_id"),
        "skill_1_name": row.get("skill_1_name") or "",
        "skill_2_id": row.get("skill_2_id"),
        "skill_2_name": row.get("skill_2_name") or "",
        "skill_3_id": row.get("skill_3_id"),
        "skill_3_name": row.get("skill_3_name") or "",
        "skill_4_id": row.get("skill_4_id"),
        "skill_4_name": row.get("skill_4_name") or "",
    }


async def _fetch_pets(cur, episode_id: int) -> list[dict]:
    await cur.execute(_PET_JOIN_SQL, (episode_id,))
    rows = await cur.fetchall()
    return [_build_pet_row(row) for row in rows]


async def get_latest_active_episode() -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, episode_number, title, strategy_text, is_active
                FROM starlight_duel_episode
                WHERE is_active = TRUE
                ORDER BY episode_number DESC
                LIMIT 1
                """
            )
            episode = await cur.fetchone()
            if not episode:
                return None
            pets = await _fetch_pets(cur, episode["id"])
            return {**episode, "pets": pets}


async def get_episode_by_number(episode_number: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, episode_number, title, strategy_text, is_active
                FROM starlight_duel_episode
                WHERE episode_number = %s
                """,
                (episode_number,),
            )
            episode = await cur.fetchone()
            if not episode:
                return None
            pets = await _fetch_pets(cur, episode["id"])
            return {**episode, "pets": pets}


async def get_episode_by_id(episode_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, episode_number, title, strategy_text, is_active
                FROM starlight_duel_episode
                WHERE id = %s
                """,
                (episode_id,),
            )
            episode = await cur.fetchone()
            if not episode:
                return None
            pets = await _fetch_pets(cur, episode["id"])
            return {**episode, "pets": pets}


async def list_episodes_paginated(
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) AS cnt FROM starlight_duel_episode")
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                """
                SELECT id, episode_number, title, is_active
                FROM starlight_duel_episode
                ORDER BY episode_number DESC
                LIMIT %s OFFSET %s
                """,
                (page_size, offset),
            )
            items = await cur.fetchall()
            return total, items


async def create_episode(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO starlight_duel_episode (episode_number, title, strategy_text, is_active)
                VALUES (%s, %s, %s, %s)
                RETURNING id, episode_number, title, strategy_text, is_active
                """,
                (
                    payload["episode_number"],
                    payload["title"],
                    payload["strategy_text"],
                    payload["is_active"],
                ),
            )
            episode = await cur.fetchone()
            episode_id = episode["id"]

            for pet in payload.get("pets", []):
                if not pet.get("pet_id"):
                    continue
                await cur.execute(
                    """
                    INSERT INTO starlight_duel_pet (episode_id, pet_id, sort_order, skill_1_id, skill_2_id, skill_3_id, skill_4_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        episode_id,
                        pet["pet_id"],
                        pet.get("sort_order", 1),
                        pet.get("skill_1_id"),
                        pet.get("skill_2_id"),
                        pet.get("skill_3_id"),
                        pet.get("skill_4_id"),
                    ),
                )
        await conn.commit()
    return await get_episode_by_id(episode_id)


async def update_episode(episode_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE starlight_duel_episode
                SET episode_number = %s, title = %s, strategy_text = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (
                    payload["episode_number"],
                    payload["title"],
                    payload["strategy_text"],
                    payload["is_active"],
                    episode_id,
                ),
            )
            row = await cur.fetchone()
            if not row:
                await conn.rollback()
                return None

            await cur.execute("DELETE FROM starlight_duel_pet WHERE episode_id = %s", (episode_id,))

            for pet in payload.get("pets", []):
                if not pet.get("pet_id"):
                    continue
                await cur.execute(
                    """
                    INSERT INTO starlight_duel_pet (episode_id, pet_id, sort_order, skill_1_id, skill_2_id, skill_3_id, skill_4_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        episode_id,
                        pet["pet_id"],
                        pet.get("sort_order", 1),
                        pet.get("skill_1_id"),
                        pet.get("skill_2_id"),
                        pet.get("skill_3_id"),
                        pet.get("skill_4_id"),
                    ),
                )
        await conn.commit()
    return await get_episode_by_id(episode_id)


async def delete_episode(episode_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM starlight_duel_episode WHERE id = %s", (episode_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


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


async def search_skills(keyword: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, name
                FROM skill
                WHERE name LIKE %s
                ORDER BY name, id
                LIMIT %s
                """,
                (f"%{keyword}%", limit),
            )
            return await cur.fetchall()
