from db.connection import get_pool


async def list_active_banners() -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, title, image_url, link_type, link_param, sort_order, is_active
                FROM banner
                WHERE is_active = TRUE
                ORDER BY sort_order, id
                """
            )
            return await cur.fetchall()


async def list_banners_paginated(
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    offset = (page - 1) * page_size
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) AS cnt FROM banner")
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                """
                SELECT id, title, image_url, link_type, link_param, sort_order, is_active
                FROM banner
                ORDER BY sort_order, id
                LIMIT %s OFFSET %s
                """,
                (page_size, offset),
            )
            items = await cur.fetchall()
            return total, items


async def get_banner_by_id(banner_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, title, image_url, link_type, link_param, sort_order, is_active
                FROM banner
                WHERE id = %s
                """,
                (banner_id,),
            )
            return await cur.fetchone()


async def create_banner(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO banner (title, image_url, link_type, link_param, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, title, image_url, link_type, link_param, sort_order, is_active
                """,
                (
                    payload["title"],
                    payload["image_url"],
                    payload["link_type"],
                    payload["link_param"],
                    payload["sort_order"],
                    payload["is_active"],
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def update_banner(banner_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE banner
                SET title = %s, image_url = %s, link_type = %s, link_param = %s,
                    sort_order = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, title, image_url, link_type, link_param, sort_order, is_active
                """,
                (
                    payload["title"],
                    payload["image_url"],
                    payload["link_type"],
                    payload["link_param"],
                    payload["sort_order"],
                    payload["is_active"],
                    banner_id,
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_banner(banner_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM banner WHERE id = %s", (banner_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted
