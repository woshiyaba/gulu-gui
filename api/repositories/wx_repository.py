import json
from typing import Any

from db.connection import get_pool


WX_AUTH_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS "user" (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS social_member (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    openid VARCHAR(128) NOT NULL,
    session_key VARCHAR(255) NOT NULL DEFAULT '',
    unionid VARCHAR(128) NOT NULL DEFAULT '',
    errcode INT NOT NULL DEFAULT 0,
    errmsg VARCHAR(255) NOT NULL DEFAULT '',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (provider, openid)
);

CREATE TABLE IF NOT EXISTS social_bind (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    social_member_id BIGINT NOT NULL REFERENCES social_member(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, provider),
    UNIQUE (social_member_id)
);
"""


async def ensure_wx_auth_tables() -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(WX_AUTH_TABLES_SQL)
        await conn.commit()


async def bind_wx_session(session_data: dict[str, Any]) -> dict[str, Any]:
    provider = "wx_mini"
    openid = (session_data.get("openid") or "").strip()
    session_key = session_data.get("session_key") or ""
    unionid = session_data.get("unionid") or ""
    errcode = int(session_data.get("errcode") or 0)
    errmsg = session_data.get("errmsg") or ""
    raw_json = json.dumps(session_data, ensure_ascii=False)

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"{provider}:{openid}",))
            await cur.execute(
                """
                INSERT INTO social_member (provider, openid, session_key, unionid, errcode, errmsg, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (provider, openid) DO UPDATE
                SET session_key = EXCLUDED.session_key,
                    unionid = COALESCE(NULLIF(EXCLUDED.unionid, ''), social_member.unionid),
                    errcode = EXCLUDED.errcode,
                    errmsg = EXCLUDED.errmsg,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                RETURNING id, provider, openid, session_key, unionid
                """,
                (provider, openid, session_key, unionid, errcode, errmsg, raw_json),
            )
            social_member = await cur.fetchone()

            await cur.execute(
                """
                SELECT user_id
                FROM social_bind
                WHERE social_member_id = %s
                """,
                (social_member["id"],),
            )
            bind = await cur.fetchone()
            if bind:
                await cur.execute(
                    """
                    UPDATE "user"
                    SET last_login_at = NOW()
                    WHERE id = %s
                    """,
                    (bind["user_id"],),
                )
                await conn.commit()
                return {
                    "user_id": bind["user_id"],
                    "social_member_id": social_member["id"],
                    "openid": social_member["openid"],
                    "unionid": social_member["unionid"] or "",
                    "is_new_user": False,
                }

            await cur.execute('INSERT INTO "user" (last_login_at) VALUES (NOW()) RETURNING id')
            user = await cur.fetchone()
            await cur.execute(
                """
                INSERT INTO social_bind (user_id, social_member_id, provider)
                VALUES (%s, %s, %s)
                """,
                (user["id"], social_member["id"], provider),
            )
        await conn.commit()

    return {
        "user_id": user["id"],
        "social_member_id": social_member["id"],
        "openid": social_member["openid"],
        "unionid": social_member["unionid"] or "",
        "is_new_user": True,
    }
