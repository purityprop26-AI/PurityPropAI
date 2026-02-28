-- ============================================================
-- Migration 004: Auth v2 — user_profiles + otp_records
-- Run ONCE against Supabase PostgreSQL
-- Safe to re-run (IF NOT EXISTS guards)
-- ============================================================

-- Enable pgcrypto for gen_random_uuid() (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── user_profiles ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    name            VARCHAR(255),
    password_hash   TEXT,                               -- NULL for OAuth users
    provider        VARCHAR(50)  NOT NULL DEFAULT 'email',  -- email | google
    picture         TEXT,
    is_verified     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT user_profiles_email_unique UNIQUE (email),
    CONSTRAINT user_profiles_provider_check CHECK (provider IN ('email', 'google'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_email    ON user_profiles (email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_provider ON user_profiles (provider);

-- Auto-update updated_at via trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ── otp_records ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS otp_records (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    otp_hash    CHAR(64)    NOT NULL,            -- SHA-256 hex digest (64 chars)
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INTEGER     NOT NULL DEFAULT 0,
    is_used     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT otp_records_attempts_non_negative CHECK (attempts >= 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_otp_records_user_id    ON otp_records (user_id);
CREATE INDEX IF NOT EXISTS idx_otp_records_expires_at ON otp_records (expires_at);
CREATE INDEX IF NOT EXISTS idx_otp_records_active
    ON otp_records (user_id, expires_at)
    WHERE is_used = FALSE;    -- Partial index — only un-used OTPs

-- Auto-delete expired OTP records (keeps table lean)
-- Run via pg_cron (Supabase supports this) or a periodic backend job
-- SELECT cron.schedule('cleanup-expired-otps', '*/15 * * * *',
--   'DELETE FROM otp_records WHERE expires_at < NOW()');

-- ── Row Level Security (Supabase) ───────────────────────────────────────
-- Disable direct client access — all access must go through backend service role
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_records   ENABLE ROW LEVEL SECURITY;

-- Deny all by default (backend uses service role which bypasses RLS)
DROP POLICY IF EXISTS "deny_all_user_profiles" ON user_profiles;
CREATE POLICY "deny_all_user_profiles" ON user_profiles
    FOR ALL TO anon, authenticated USING (FALSE);

DROP POLICY IF EXISTS "deny_all_otp_records" ON otp_records;
CREATE POLICY "deny_all_otp_records" ON otp_records
    FOR ALL TO anon, authenticated USING (FALSE);

-- Verification
SELECT COUNT(*) as user_profiles_count FROM user_profiles;
SELECT COUNT(*) as otp_records_count   FROM otp_records;
