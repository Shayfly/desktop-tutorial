CREATE TABLE IF NOT EXISTS build_jobs (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    version_id      TEXT,
    status          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    artifact_key    TEXT,
    error_code      TEXT,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_build_jobs_project_created
ON build_jobs(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS deployments (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    version_id      TEXT NOT NULL,
    build_id        TEXT NOT NULL,
    environment     TEXT NOT NULL,
    artifact_key    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retired_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_deployments_project_env
ON deployments(project_id, environment, created_at DESC);
