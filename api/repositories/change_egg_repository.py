"""换蛋广场仓储 —— change_egg_listing / change_egg_match 读写。

建表语句见 sql/change_egg.sql，本模块在 ensure_change_egg_tables() 内
用 CREATE TABLE IF NOT EXISTS 自动建表，并负责挂单 CRUD 与双向匹配查询。
"""

from __future__ import annotations

from typing import Any

from db.connection import get_pool


CHANGE_EGG_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS change_egg_listing (
    id              BIGSERIAL    PRIMARY KEY,
    user_id         BIGINT       NOT NULL,
    game_id         VARCHAR(64)  NOT NULL DEFAULT '',
    own_pokemon_id  INT          NOT NULL,
    own_tag         VARCHAR(30)  NOT NULL DEFAULT '',
    want_pokemon_id INT          NOT NULL,
    want_tag        VARCHAR(30)  NOT NULL DEFAULT '',
    status          VARCHAR(16)  NOT NULL DEFAULT 'open',
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cel_want ON change_egg_listing (want_pokemon_id, want_tag, status);
CREATE INDEX IF NOT EXISTS idx_cel_own  ON change_egg_listing (own_pokemon_id, own_tag, status);
CREATE INDEX IF NOT EXISTS idx_cel_user ON change_egg_listing (user_id, status);

CREATE TABLE IF NOT EXISTS change_egg_match (
    id           BIGSERIAL  PRIMARY KEY,
    listing_a_id BIGINT     NOT NULL,
    listing_b_id BIGINT     NOT NULL,
    user_a_id    BIGINT     NOT NULL,
    user_b_id    BIGINT     NOT NULL,
    created_at   TIMESTAMP  NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_cem_pair UNIQUE (listing_a_id, listing_b_id)
);
"""

# 列表/详情查询统一带出 own/want 对应 pokemon 的名称与头像，便于前端展示。
_LISTING_SELECT = """
SELECT l.id, l.user_id, l.game_id,
       l.own_pokemon_id, l.own_tag,
       l.want_pokemon_id, l.want_tag,
       l.status, l.created_at, l.updated_at,
       po.name AS own_pokemon_name, po.avatar AS own_pokemon_avatar,
       pw.name AS want_pokemon_name, pw.avatar AS want_pokemon_avatar
FROM change_egg_listing l
LEFT JOIN pokemon po ON po.id = l.own_pokemon_id
LEFT JOIN pokemon pw ON pw.id = l.want_pokemon_id
"""


async def ensure_change_egg_tables() -> None:
    """确保换蛋相关表存在。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(CHANGE_EGG_TABLES_SQL)
        await conn.commit()


async def create_listing(
    user_id: int,
    game_id: str,
    own_pokemon_id: int,
    own_tag: str,
    want_pokemon_id: int,
    want_tag: str,
) -> dict[str, Any]:
    """新增一条换蛋挂单，返回（带 pokemon 展示信息的）完整记录。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO change_egg_listing
                    (user_id, game_id, own_pokemon_id, own_tag, want_pokemon_id, want_tag)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, game_id, own_pokemon_id, own_tag, want_pokemon_id, want_tag),
            )
            row = await cur.fetchone()
        await conn.commit()
    return await get_listing(row["id"])


async def get_listing(listing_id: int) -> dict[str, Any] | None:
    """按 id 查单条挂单。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LISTING_SELECT + " WHERE l.id = %s", (listing_id,))
            return await cur.fetchone()


async def list_user_listings(
    user_id: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """查某用户的挂单，可选按 status 过滤，最新在前。"""
    pool = await get_pool()
    where = "WHERE l.user_id = %s"
    params: list[Any] = [user_id]
    if status:
        where += " AND l.status = %s"
        params.append(status)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _LISTING_SELECT + f" {where} ORDER BY l.id DESC",
                params,
            )
            return await cur.fetchall()


async def list_open_listings(
    limit: int = 20,
    offset: int = 0,
    pokemon_id: int | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """广场分页浏览所有 open 挂单，可选按 own_pokemon_id / own_tag 过滤。"""
    pool = await get_pool()
    where = "WHERE l.status = 'open'"
    params: list[Any] = []
    if pokemon_id is not None:
        where += " AND l.own_pokemon_id = %s"
        params.append(pokemon_id)
    if tag:
        where += " AND l.own_tag = %s"
        params.append(tag)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _LISTING_SELECT + f" {where} ORDER BY l.id DESC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            )
            return await cur.fetchall()


async def list_all_open_listings() -> list[dict[str, Any]]:
    """返回所有 open 挂单（定时任务全量扫描用，仅取匹配所需字段）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, game_id, own_pokemon_id, own_tag,
                       want_pokemon_id, want_tag, status
                FROM change_egg_listing
                WHERE status = 'open'
                ORDER BY id ASC
                """
            )
            return await cur.fetchall()


async def close_listing(listing_id: int, user_id: int) -> dict[str, Any] | None:
    """主动关闭正在匹配（open）的挂单（校验归属）：status open → closed。

    返回被关闭的挂单；不存在、无权限或不处于 open 状态时返回 None。
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE change_egg_listing
                SET status = 'closed', updated_at = NOW()
                WHERE id = %s AND user_id = %s AND status = 'open'
                RETURNING id
                """,
                (listing_id, user_id),
            )
            row = await cur.fetchone()
        await conn.commit()
    if not row:
        return None
    return await get_listing(listing_id)


async def delete_listing(listing_id: int, user_id: int) -> bool:
    """彻底删除自己的挂单（校验归属）。删除成功返回 True；不存在或无权限返回 False。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM change_egg_listing WHERE id = %s AND user_id = %s RETURNING id",
                (listing_id, user_id),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row is not None


async def find_reciprocal_matches(listing: dict[str, Any]) -> list[dict[str, Any]]:
    """找出与 listing 双向吻合的其它 open 挂单：
    对方拥有 == 我需求(pokemon_id+tag) 且 对方需求 == 我拥有(pokemon_id+tag)。
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, game_id, own_pokemon_id, own_tag,
                       want_pokemon_id, want_tag, status
                FROM change_egg_listing
                WHERE status = 'open'
                  AND user_id <> %s
                  AND own_pokemon_id = %s AND own_tag = %s
                  AND want_pokemon_id = %s AND want_tag = %s
                ORDER BY id ASC
                """,
                (
                    listing["user_id"],
                    listing["want_pokemon_id"],
                    listing["want_tag"],
                    listing["own_pokemon_id"],
                    listing["own_tag"],
                ),
            )
            return await cur.fetchall()


async def record_match(
    listing_a_id: int,
    listing_b_id: int,
    user_a_id: int,
    user_b_id: int,
) -> bool:
    """记录一对命中（自动归一化 a<b）。新插入返回 True；已存在（重复）返回 False。"""
    # 归一化，保证 (a, b) 与 (b, a) 视为同一对
    if listing_a_id > listing_b_id:
        listing_a_id, listing_b_id = listing_b_id, listing_a_id
        user_a_id, user_b_id = user_b_id, user_a_id

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO change_egg_match (listing_a_id, listing_b_id, user_a_id, user_b_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (listing_a_id, listing_b_id) DO NOTHING
                RETURNING id
                """,
                (listing_a_id, listing_b_id, user_a_id, user_b_id),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row is not None


async def mark_listings_matched(listing_ids: list[int]) -> None:
    """把指定挂单标记为 matched。"""
    if not listing_ids:
        return
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE change_egg_listing
                SET status = 'matched', updated_at = NOW()
                WHERE id = ANY(%s) AND status = 'open'
                """,
                (listing_ids,),
            )
        await conn.commit()


async def list_egg_tags() -> list[dict[str, Any]]:
    """从 sys_dict 读取换蛋 tag 选项（dict_type='egg_exchange_tag'）。"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT code, label, sort_order
                FROM sys_dict
                WHERE dict_type = 'egg_exchange_tag'
                ORDER BY sort_order, id
                """
            )
            return await cur.fetchall()
