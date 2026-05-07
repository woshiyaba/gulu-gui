from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import PG_CONFIG

_pool: AsyncConnectionPool | None = None


def _build_conninfo() -> str:
    """拼接 psycopg3 连接串。"""
    return (
        f"host={PG_CONFIG['host']} "
        f"port={PG_CONFIG['port']} "
        f"dbname={PG_CONFIG['dbname']} "
        f"user={PG_CONFIG['user']} "
        f"password={PG_CONFIG['password']}"
    )


async def get_pool() -> AsyncConnectionPool:
    """获取全局 PostgreSQL 异步连接池，首次调用时自动创建。"""
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=_build_conninfo(),
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
        )
        await _pool.open()
    return _pool


async def close_pool():
    """关闭连接池，在应用关闭时调用。"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
