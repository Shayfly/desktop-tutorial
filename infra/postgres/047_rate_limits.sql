-- 047: rate-limit counters every API instance shares (the owner, 2026-11-26 08:56 UTC: rate limits on the platform API).
-- omni_prod/rate_limits.py holds the limits, their reasons and the only code that reads or writes this table.
-- One row per (limit, subject, window): an INSERT ... ON CONFLICT DO UPDATE adds one hit and returns the count, so every
-- Vercel instance sees the same count. The subject (an address, an e-mail, an account id) is stored only as an HMAC-SHA256
-- keyed from OMNI_SECRET_KEY, never as the address or the e-mail. A row is read for two windows (its own, then as the
-- previous window of the sliding estimate) and expires after them; omni_prod/rate_limits.py deletes expired rows in
-- bounded batches (expires_at index below).
-- 046 is the social sign-in migration of another branch (claude/practical-hopper-oi3qj2-social-login). The two touch
-- different tables and apply in either order; the second to merge lists both in omni_prod/schema_manifest.py.
-- A migration: runs with the owner's approval (2026-11-26; CLAUDE.md section 5). It must be applied to production BEFORE
-- the release that ships omni_prod/rate_limits.py: without this table the sign-in routes answer 503 (fail closed).
-- Rollback: infra/postgres/rollback/047_rate_limits.down.sql.
CREATE TABLE IF NOT EXISTS rate_limit_counters (
    bucket       TEXT        NOT NULL,
    key_hash     TEXT        NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    hits         INTEGER     NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (bucket, key_hash, window_start),
    CONSTRAINT rate_limit_counters_bucket_name CHECK (bucket ~ '^[a-z][a-z0-9_]{0,62}$'),
    CONSTRAINT rate_limit_counters_key_is_a_digest CHECK (key_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT rate_limit_counters_hits_positive CHECK (hits > 0),
    CONSTRAINT rate_limit_counters_expires_after_start CHECK (expires_at > window_start)
);
CREATE INDEX IF NOT EXISTS rate_limit_counters_expiry ON rate_limit_counters (expires_at);
