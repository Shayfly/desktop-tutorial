-- 042: live_core tables (#232 part B, #236).
-- Same DDL as live_core.postgres_store.SCHEMA, which stays as a fallback and stops
-- running once this version is recorded in schema_migrations. Every statement is
-- IF NOT EXISTS, so this is clean on a database where the fallback already ran.
-- Rollback: infra/postgres/rollback/042_live_core_tables.down.sql (not run by the runner).
CREATE TABLE IF NOT EXISTS live_users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    email_normalized TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    token_digest CHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS live_projects (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    active_version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_artifacts (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    sha256 CHAR(64) NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_versions (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    artifact_id UUID NOT NULL REFERENCES live_artifacts(id) ON DELETE RESTRICT,
    prompt TEXT NOT NULL,
    parent_version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_builds (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT NULL,
    version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_build_events (
    id UUID PRIMARY KEY,
    build_id UUID NOT NULL REFERENCES live_builds(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_live_projects_owner ON live_projects(owner_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_versions_project ON live_versions(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_live_versions_owner_project ON live_versions(owner_id, project_id);
CREATE INDEX IF NOT EXISTS idx_live_builds_owner_project ON live_builds(owner_id, project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_build_events_build ON live_build_events(build_id, created_at);
CREATE INDEX IF NOT EXISTS idx_live_artifacts_owner_project ON live_artifacts(owner_id, project_id);
