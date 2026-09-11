"""
One-shot database initialisation script for the User Portal.

Run once before starting the application for the first time:

    python -m app.db.init_db

What this script does
---------------------
1. Creates the portal_users table (idempotent — safe to re-run).
2. Reads data/registered_users.json if it exists.
3. For each existing registered user, inserts a row with password_hash='NEEDS_RESET'.
   - These users cannot log in with their old SHA-256 password (the hash format is
     incompatible with bcrypt and cannot be migrated without the plaintext).
   - On login attempt the 'NEEDS_RESET' sentinel is detected and the user is directed
     to re-register.
   - Users whose username already exists in portal_users are skipped.

No existing data is deleted. The script is safe to re-run at any point.

Environment
-----------
Requires DATABASE_URL to be set in the environment or .env file.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from app.config import settings
from app.db.database import DatabaseConnectionError, get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)

# Sentinel value written for users imported from the legacy JSON file.
# AuthManager treats this as "password reset required".
_NEEDS_RESET = "NEEDS_RESET"

_SCHEMA_SQL = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


def init_schema() -> None:
    """Apply the schema.sql DDL to the connected database."""
    LOGGER.info("Applying portal_users schema …")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
    LOGGER.info("Schema applied successfully.")


def migrate_legacy_users() -> int:
    """
    Import usernames from the legacy registered_users.json into portal_users.

    Returns the number of users imported (skips those already present).
    """
    reg_file: Path = settings.data_dir / "registered_users.json"
    if not reg_file.exists():
        LOGGER.info("No legacy registered_users.json found — skipping migration.")
        return 0

    try:
        with open(reg_file, "r", encoding="utf-8") as fh:
            legacy: dict = json.load(fh)
    except Exception as exc:
        LOGGER.warning("Could not read registered_users.json: %s — skipping.", exc)
        return 0

    if not isinstance(legacy, dict) or not legacy:
        LOGGER.info("registered_users.json is empty — nothing to import.")
        return 0

    imported = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for username in legacy:
                username = username.strip()
                if not username:
                    continue
                try:
                    cur.execute(
                        """
                        INSERT INTO portal_users (username, password_hash)
                        VALUES (%s, %s)
                        ON CONFLICT (username) DO NOTHING
                        """,
                        (username, _NEEDS_RESET),
                    )
                    if cur.rowcount == 1:
                        imported += 1
                        LOGGER.info(
                            "Imported legacy user '%s' with NEEDS_RESET sentinel.", username
                        )
                    else:
                        LOGGER.info(
                            "User '%s' already exists in portal_users — skipped.", username
                        )
                except Exception as exc:
                    LOGGER.warning("Failed to import user '%s': %s", username, exc)

    LOGGER.info("Legacy migration complete. Imported %d user(s).", imported)
    return imported


def main() -> None:
    """Entry point: apply schema then migrate legacy users."""
    if not settings.database_url:
        LOGGER.error(
            "DATABASE_URL is not set. "
            "Configure it in your .env file before running init_db."
        )
        sys.exit(1)

    LOGGER.info("Connecting to PostgreSQL …")
    try:
        init_schema()
        migrate_legacy_users()
    except DatabaseConnectionError as exc:
        LOGGER.error("Database initialisation failed: %s", exc)
        sys.exit(1)

    LOGGER.info("Database initialisation complete.")


if __name__ == "__main__":
    main()
