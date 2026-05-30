"""宠物对话 prompt 数据访问。

prompt 存于 pet_prompt 表（建表见 sql/pet_chat.sql，本模块不负责建表），
pet_id ↔ pokemon.id 一对一。列表读取时 LEFT JOIN pokemon 取宠物名称 / 图片。
"""

from db.connection import get_pool

# pet_prompt 自身字段
_COLUMNS = "id, pet_id, prompt, enabled, created_at, updated_at"
# 列表 / 详情统一带上宠物名称与图片
_JOINED_COLUMNS = (
    "pp.id, pp.pet_id, pp.prompt, pp.enabled, pp.created_at, pp.updated_at, "
    "COALESCE(p.name, '') AS pet_name, COALESCE(p.image, '') AS pet_image"
)


async def list_paginated(keyword: str = "", page: int = 1, page_size: int = 10) -> tuple[int, list[dict]]:
    pool = await get_pool()
    offset = (page - 1) * page_size
    where = ""
    params: list = []
    if keyword:
        where = "WHERE p.name ILIKE %s"
        params.append(f"%{keyword}%")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM pet_prompt pp
                LEFT JOIN pokemon p ON p.id = pp.pet_id
                {where}
                """,
                params,
            )
            total_row = await cur.fetchone() or {}
            total = int(total_row.get("cnt", 0))

            await cur.execute(
                f"""
                SELECT {_JOINED_COLUMNS}
                FROM pet_prompt pp
                LEFT JOIN pokemon p ON p.id = pp.pet_id
                {where}
                ORDER BY pp.updated_at DESC, pp.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            items = await cur.fetchall()
            return total, items


async def get_by_id(item_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT {_JOINED_COLUMNS}
                FROM pet_prompt pp
                LEFT JOIN pokemon p ON p.id = pp.pet_id
                WHERE pp.id = %s
                """,
                (item_id,),
            )
            return await cur.fetchone()


async def get_by_pet_id(pet_id: int) -> dict | None:
    """按宠物 id 查 prompt，用于校验唯一性（一只宠物只能有一条 prompt）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {_COLUMNS} FROM pet_prompt WHERE pet_id = %s",
                (pet_id,),
            )
            return await cur.fetchone()


async def get_pet(pet_id: int) -> dict | None:
    """查宠物（精灵）基本信息，用于校验 pet_id 是否存在。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name FROM pokemon WHERE id = %s",
                (pet_id,),
            )
            return await cur.fetchone()


async def create(payload: dict) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pet_prompt (pet_id, prompt, enabled)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (payload["pet_id"], payload["prompt"], payload["enabled"]),
            )
            row = await cur.fetchone()
        await conn.commit()
    return await get_by_id(row["id"])


async def update(item_id: int, payload: dict) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE pet_prompt
                SET pet_id = %s, prompt = %s, enabled = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (payload["pet_id"], payload["prompt"], payload["enabled"], item_id),
            )
            updated = cur.rowcount > 0
        await conn.commit()
    if not updated:
        return None
    return await get_by_id(item_id)


async def delete(item_id: int) -> bool:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM pet_prompt WHERE id = %s", (item_id,))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted
