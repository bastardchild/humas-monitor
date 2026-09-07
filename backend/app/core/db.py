import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(os.getenv("DATABASE_PATH", "/data/app.db" if os.path.exists("/data") else "./data/app.db"))
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = _connect()
    try:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql)
    finally:
        conn.close()

@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()

def get_db_dependency():
    """FastAPI dependency"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
