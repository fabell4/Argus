"""Shared SQLite connection helper for API route modules."""

from __future__ import annotations

import sqlite3

from src import config

_DB_UNAVAILABLE = "Database unavailable."
_API_SQLITE_TIMEOUT = 10


def get_conn() -> sqlite3.Connection:
    """Return a configured read-only SQLite connection for API routes.

    Raises :class:`sqlite3.OperationalError` if the database cannot be opened.
    Use ``contextlib.closing(get_conn())`` in a ``with`` statement to ensure
    the connection is closed after use.
    """
    conn = sqlite3.connect(
        config.SQLITE_PATH, check_same_thread=False, timeout=_API_SQLITE_TIMEOUT
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
