import pymysql
from config import DB_CONFIG


def get_conn() -> pymysql.connections.Connection:
    """获取一个 pymysql 连接，调用方负责关闭。"""
    return pymysql.connect(
        **DB_CONFIG,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
