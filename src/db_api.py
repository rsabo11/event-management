import pymysql
from .config import DB

def get_connection():
    return pymysql.connect(
        host=DB["host"], port=DB["port"],
        user=DB["user"], password=DB["password"],
        database=DB["database"], cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )