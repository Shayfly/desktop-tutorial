-- 014_real_running_preview.sql
-- M3: durable metadata for the real running-preview lifecycle. Separate
-- table from build_jobs/project_versions -- a preview is a distinct runtime
-- lifecycle (create -> provision -> start -> health -> expose -> logs ->
-- stop/expire -> cleanup), not a build artifact.

CREATE TABLE IF NOT EXISTS project_previews (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('STARTING', 'RUNNING', 'STOPPED', 'FAILED', 'EXPIRED')),
    preview_url TEXT,
    internal_container_id TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_previews_project_created
ON project_previews(project_id, created_at DESC);

-- Used by mark_expired()'s sweep (status='RUNNING' AND expires_at < now()).
CREATE INDEX IF NOT EXISTS idx_project_previews_running_expiry
ON project_previews(expires_at)
WHERE status = 'RUNNING';
