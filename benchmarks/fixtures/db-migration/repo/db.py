import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def apply_migrations(conn):
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def new_connection():
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    return conn


def seed(conn):
    conn.execute("INSERT INTO users (id, email, name) VALUES (1, 'a@example.com', 'Alice')")
    conn.commit()
