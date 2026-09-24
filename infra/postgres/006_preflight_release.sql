ALTER TABLE release_records
ADD COLUMN IF NOT EXISTS preflight_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS production_checks (
    id              BIGSERIAL PRIMARY KEY,
    release_id      TEXT NOT NULL,
    check_name      TEXT NOT NULL,
    status          TEXT NOT NULL,
    details         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_production_checks_release
ON production_checks(release_id, created_at DESC);
