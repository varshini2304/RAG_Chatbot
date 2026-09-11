-- =============================================================================
-- portal_users — User Portal authentication table
-- =============================================================================
-- Apply with:
--     python -m app.db.init_db
-- Or directly:
--     psql $DATABASE_URL -f app/db/schema.sql
--
-- This script is IDEMPOTENT — safe to run multiple times.
-- =============================================================================

CREATE TABLE IF NOT EXISTS portal_users (
    id            SERIAL       PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,   -- bcrypt hash produced by passlib
                                           -- sentinel 'NEEDS_RESET' means user
                                           -- was imported from legacy JSON and
                                           -- must re-register with a new password
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_users_username
    ON portal_users (username);

-- Column notes:
--   username      : max 64 chars — matches UserRegisterRequest.max_length=64
--   password_hash : bcrypt produces 60-char strings; TEXT gives future flexibility
--   created_at    : used by analytics_repository for registration event tracking
