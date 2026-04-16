"""
初始化 /ops 维护平台所需表，并创建或重置 admin 账号。

执行：
    uv run python scripts/init_ops_tables.py

效果：
1. 在 PostgreSQL 中创建 ops_user / ops_audit_log
2. 创建或更新 admin 账号
3. 将 admin 密码重置为 123456
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.repositories.ops_repository import OPS_TABLES_SQL
from api.services.ops_service import hash_password
from db.connection import close_pool, get_pool


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"
ADMIN_NICKNAME = "系统管理员"
ADMIN_ROLE = "admin"


async def main() -> None:
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(OPS_TABLES_SQL)
                await cur.execute(
                    """
                    INSERT INTO ops_user (username, password_hash, nickname, role, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET password_hash = EXCLUDED.password_hash,
                        nickname = EXCLUDED.nickname,
                        role = EXCLUDED.role,
                        is_active = TRUE,
                        updated_at = NOW()
                    RETURNING id, username, nickname, role, is_active
                    """,
                    (
                        ADMIN_USERNAME,
                        hash_password(ADMIN_PASSWORD),
                        ADMIN_NICKNAME,
                        ADMIN_ROLE,
                    ),
                )
                user = await cur.fetchone()
            await conn.commit()

        print("[ops] 表初始化完成")
        print(f"[ops] admin 账号已就绪: username={user['username']} role={user['role']}")
        print(f"[ops] admin 密码已重置为: {ADMIN_PASSWORD}")
    finally:
        await close_pool()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
