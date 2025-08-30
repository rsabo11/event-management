import os
from dotenv import load_dotenv
load_dotenv()

DB = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "eventapp"),
    "password": os.getenv("DB_PASSWORD", "eventpw"),
    "database": os.getenv("DB_NAME", "eventdb"),
}

LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)