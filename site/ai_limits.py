"""Atomic, restart-safe AI attempt quotas. Never store photos or Telegram IDs."""
import time
from pathlib import Path

import order_storage

DATABASE = None


class Unavailable(Exception):
    pass


def configure(path):
    global DATABASE
    DATABASE = Path(path)


def reserve(scope, limit, *, interval=0):
    """Charge an attempt before provider access; failed attempts remain charged."""
    if DATABASE is None:
        raise Unavailable("Persistent AI quotas are not configured")
    try:
        with order_storage.connect(DATABASE, write=True) as db:
            if order_storage.DATABASE_URL:
                now = float(db.execute("SELECT EXTRACT(EPOCH FROM clock_timestamp())").fetchone()[0])
            else:
                db.execute("BEGIN IMMEDIATE")
                now = time.time()
            db.execute("DELETE FROM ai_attempts WHERE attempted_at <= ?", (now - 3600,))
            count, latest = db.execute(
                "SELECT COUNT(*), MAX(attempted_at) FROM ai_attempts WHERE scope = ?", (scope,)
            ).fetchone()
            if count >= limit or (latest is not None and now - latest < interval):
                return False
            db.execute("INSERT INTO ai_attempts (scope, attempted_at) VALUES (?, ?)", (scope, now))
            return True
    except order_storage.DatabaseError:
        # Do not fall back to an empty in-memory budget after a database failure.
        raise Unavailable("AI quota storage is unavailable") from None
