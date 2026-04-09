import aiomysql
from config import DB_CONFIG

_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    """获取全局连接池，首次调用时自动创建。"""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            db=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            charset=DB_CONFIG["charset"],
            cursorclass=aiomysql.DictCursor,
            autocommit=False,
            minsize=2,
            maxsize=10,
        )
    return _pool


async def close_pool():
    """关闭连接池，在应用关闭时调用。"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
