-- 018_identity_lifecycle.sql
-- M5 Task 2: durable creator identity/session lifecycle. Raw session, email
-- verification and password-reset tokens are never persisted.

ALTER TABLE creator_accounts
    ADD COLUMN IF NOT EXISTS account_status TEXT NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE creator_accounts
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS creator_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_creator_sessions_user_active
    ON creator_sessions(user_id, created_at DESC)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS creator_identity_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('EMAIL_VERIFY','PASSWORD_RESET')),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_creator_identity_tokens_lookup
    ON creator_identity_tokens(token_hash, purpose)
    WHERE consumed_at IS NULL;

CREATE TABLE IF NOT EXISTS creator_consents (
    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    version TEXT NOT NULL,
    source TEXT NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(user_id, consent_type, version)
);

CREATE TABLE IF NOT EXISTS creator_privacy_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
    request_type TEXT NOT NULL CHECK (request_type IN ('DATA_EXPORT','ACCOUNT_DELETION')),
    status TEXT NOT NULL CHECK (status IN ('REQUESTED','PROCESSING','COMPLETED','REJECTED')),
    requested_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_creator_privacy_requests_user
    ON creator_privacy_requests(user_id, requested_at DESC);
