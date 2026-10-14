CREATE TABLE IF NOT EXISTS usage_events (
    id              BIGSERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    project_id      TEXT NOT NULL,
    kind            TEXT NOT NULL,
    quantity        NUMERIC(30, 6) NOT NULL CHECK (quantity >= 0),
    provider        TEXT,
    model           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_account_created
ON usage_events(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_project_created
ON usage_events(project_id, created_at DESC);
