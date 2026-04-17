from psycopg import AsyncConnection

from db.connection import get_pool


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
    keyword: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[dict]]:
    pool = await get_pool()
    conditions: list[str] = []
    params: list[str] = []
    if dict_type:
        conditions.append("dict_type = %s")
        params.append(dict_type)
    if keyword:
        conditions.append("(code LIKE %s OR label LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
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
