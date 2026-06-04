"""精灵相册数据访问。

照片存于 pet_album 表，按"用户 × 宠物"组织，精选优先展示。
建表语句见 sql/pet_album.sql（不随应用自动执行，需手动建表）。
"""

from db.connection import get_pool


async def create_photo(user_id: int, pet_id: int, image_url: str, is_featured: bool) -> dict | None:
    """新增一张相册照片，返回完整记录。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pet_album (user_id, pet_id, image_url, is_featured)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, pet_id, image_url, is_featured, created_at, updated_at
                """,
                (user_id, pet_id, image_url, is_featured),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def list_photos(user_id: int, pet_id: int) -> list[dict]:
    """查询某用户某宠物的所有照片，精选优先、再按时间倒序。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, pet_id, image_url, is_featured, created_at, updated_at
                FROM pet_album
                WHERE user_id = %s AND pet_id = %s
                ORDER BY is_featured DESC, created_at DESC, id DESC
                """,
                (user_id, pet_id),
            )
            return await cur.fetchall()


async def get_photo(photo_id: int) -> dict | None:
    """按 id 查询单张照片。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, pet_id, image_url, is_featured, created_at, updated_at
                FROM pet_album
                WHERE id = %s
                """,
                (photo_id,),
            )
            return await cur.fetchone()


async def set_featured(photo_id: int, is_featured: bool) -> dict | None:
    """设置 / 取消精选，返回更新后的记录；不存在时返回 None。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE pet_album
                SET is_featured = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, user_id, pet_id, image_url, is_featured, created_at, updated_at
                """,
                (is_featured, photo_id),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def delete_photo(photo_id: int) -> dict | None:
    """删除一张照片，返回被删除的记录（含 image_url，供调用方清理 OSS）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM pet_album
                WHERE id = %s
                RETURNING id, user_id, pet_id, image_url, is_featured, created_at, updated_at
                """,
                (photo_id,),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row
