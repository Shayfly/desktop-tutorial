CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    sequence        BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash   TEXT NOT NULL,
    event_hash      TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_resource
ON audit_events(resource_id, sequence DESC);

CREATE TABLE IF NOT EXISTS release_records (
    id              TEXT PRIMARY KEY,
    version         TEXT NOT NULL,
    package_sha256  TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    test_count      INTEGER NOT NULL CHECK (test_count >= 0),
    status          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
