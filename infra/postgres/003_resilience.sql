CREATE TABLE IF NOT EXISTS idempotency_keys (
    account_id          TEXT NOT NULL,
    idempotency_key     TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    resource_id         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ,
    PRIMARY KEY(account_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_expires
ON idempotency_keys(expires_at)
WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id       TEXT PRIMARY KEY,
    queue_name      TEXT NOT NULL,
    seen_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS account_limits (
    account_id      TEXT NOT NULL,
    metric          TEXT NOT NULL,
    maximum         NUMERIC(30, 6) NOT NULL CHECK (maximum >= 0),
    period          TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(account_id, metric, period)
);
