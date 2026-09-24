ALTER TABLE build_jobs
    ADD COLUMN IF NOT EXISTS attempt INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS repair_rounds INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ai_cost NUMERIC(18,6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS build_seconds INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS deployment_events (
    id              BIGSERIAL PRIMARY KEY,
    deployment_id   TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    traffic_percent INTEGER,
    error_rate      NUMERIC(10,6),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployment_events_deployment_created
ON deployment_events(deployment_id, created_at DESC);
