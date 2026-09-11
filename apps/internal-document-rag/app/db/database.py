"""
PostgreSQL connection management for the User Portal.

Uses psycopg2 (synchronous) — appropriate for the existing FastAPI sync handlers.

All credentials come from the DATABASE_URL environment variable via Settings.
The URL is NEVER hardcoded here.

Usage
-----
    from app.db.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            rows = cur.fetchall()
        conn.commit()

Connection errors raise DatabaseConnectionError — callers must handle this
rather than silently falling back to another storage backend.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from app.config import settings

LOGGER = logging.getLogger(__name__)


class DatabaseConnectionError(RuntimeError):
    """Raised when a PostgreSQL connection cannot be established."""


def _sanitize_log_message(msg: str) -> str:
    """Strip passwords from connection strings and URLs before logging."""
    import re

    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:****@", str(msg))


@contextmanager
def get_connection() -> Generator[PgConnection, None, None]:
    """
    Context manager that yields an open psycopg2 connection.

    The connection is committed on clean exit and rolled back on exception.
    Always closed when the context exits.

    Raises:
        DatabaseConnectionError: If DATABASE_URL is not configured or the
            connection cannot be established.
    """
    url = settings.database_url
    if not url:
        raise DatabaseConnectionError(
            "DATABASE_URL is not configured. "
            "Set DATABASE_URL in your environment or .env file to enable "
            "PostgreSQL-backed User Portal authentication."
        )

    conn: PgConnection | None = None
    try:
        conn = psycopg2.connect(url)
        yield conn
        conn.commit()
    except psycopg2.OperationalError as exc:
        clean_exc = _sanitize_log_message(str(exc))
        LOGGER.error("AUTH | POSTGRES_CONNECTION_FAILED | reason=%s", clean_exc)
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise DatabaseConnectionError(
            f"Cannot connect to PostgreSQL: {clean_exc}"
        ) from exc
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def check_connection() -> bool:
    """
    Perform a lightweight connectivity check.

    Returns True if the connection succeeds, False otherwise.
    Does NOT raise — intended for startup health checks.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except (DatabaseConnectionError, Exception) as exc:
        LOGGER.warning("PostgreSQL connectivity check failed: %s", exc)
        return False
