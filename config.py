from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "database": os.getenv("MYSQL_DATABASE", "zlkwg_gui"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "charset": "utf8mb4",
}

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "dbname": os.getenv("PG_DATABASE", "wikiroco"),
    "user": os.getenv("PG_USER", "wikiroco"),
    "password": os.getenv("PG_PASSWORD", ""),
}

BASE_URL = "https://rocom.game-walkthrough.com"

STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "https://wikiroco.com")
FRIEND_IMAGE_BASE_URL = f"{STATIC_BASE_URL}/images/friends/"
CATEGORY_ICON_BASE_URL = f"{STATIC_BASE_URL}/images/icon"
