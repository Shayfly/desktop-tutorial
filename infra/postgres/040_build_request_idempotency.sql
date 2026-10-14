-- Caller-stable build request identity. The quote hash uses
-- quote-fingerprint/2 (including category=build); its version is persisted.
-- The deferred FK lets admission claim
-- the key before reserving credits, then attach it to the request/job created
-- by the same transaction. Raw request and quote payloads are not stored.
CREATE TABLE IF NOT EXISTS build_request_idempotency (
    account_id TEXT NOT NULL,
    internal_project_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL CHECK (idempotency_key ~ '^[A-Za-z0-9._:-]{8,160}$'),
    request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
    quote_fingerprint TEXT NOT NULL CHECK (quote_fingerprint ~ '^[0-9a-f]{64}$'),
    quote_fingerprint_version SMALLINT NOT NULL DEFAULT 2 CHECK (quote_fingerprint_version > 0),
    build_id TEXT NOT NULL UNIQUE
        REFERENCES build_requests(build_id) ON DELETE CASCADE
        DEFERRABLE INITIALLY DEFERRED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, internal_project_id, idempotency_key)
);
