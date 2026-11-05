"""Database connections for local previews and the PostgreSQL test deployment."""
import os
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DatabaseError = (sqlite3.Error,)
if DATABASE_URL:
    import psycopg
    DatabaseError += (psycopg.Error,)


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, args=()):
        sql = sql.strip()
        if sql == "BEGIN IMMEDIATE" or sql.startswith("CREATE TABLE IF NOT EXISTS "):
            # Startup applies the schema. The surrounding transaction locks writes.
            return
        sql = sql.replace("json_extract(payload, '$.payment')", "(payload -> 'payment')")
        cursor = self.connection.execute(sql.replace("?", "%s"), args)
        return cursor


def initialize(local_path=None):
    if not DATABASE_URL:
        if local_path is not None:
            with closing(sqlite3.connect(local_path)) as db, db:
                db.executescript((Path(__file__).parent / 'sqlite/002_accounts.sql').read_text(encoding='utf-8'))
                if 'customer_id' not in {row[1] for row in db.execute('PRAGMA table_info(orders)')}:
                    db.execute('ALTER TABLE orders ADD COLUMN customer_id TEXT REFERENCES customers(id)')
                db.execute('CREATE INDEX IF NOT EXISTS orders_customer_created_idx ON orders(customer_id, created DESC)')
        return
    with psycopg.connect(DATABASE_URL, connect_timeout=5) as db:
        db.execute("SELECT pg_advisory_xact_lock(435312701)")
        db.execute("CREATE TABLE IF NOT EXISTS lusar_migrations (version text PRIMARY KEY)")
        for migration in sorted((Path(__file__).parent / 'postgres').glob('*.sql')):
            if not db.execute("SELECT 1 FROM lusar_migrations WHERE version = %s", (migration.name,)).fetchone():
                db.execute(migration.read_text(encoding="utf-8"), prepare=False)
                db.execute("INSERT INTO lusar_migrations (version) VALUES (%s)", (migration.name,))
        db.execute("SELECT 1 FROM orders LIMIT 1")


def available(local_path):
    return bool(DATABASE_URL) or local_path.is_file()


@contextmanager
def connect(local_path, *, write=False):
    if DATABASE_URL:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as db:
            db.adapters.register_loader("jsonb", psycopg.types.string.TextLoader)
            if write:
                db.execute("SELECT pg_advisory_xact_lock(435312701)")
            yield PostgresConnection(db)
        return
    from contextlib import closing
    with closing(sqlite3.connect(local_path)) as db, db:
        yield db
