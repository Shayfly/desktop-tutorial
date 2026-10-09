-- Stop a build and show what it is doing; preview data durability (migration 031).
-- Master directive 2026-10-09 §10 (task states, cancel) and §12 (the user
-- always sees what is happening).
--
-- cancel_requested_at: set by the owner's "stop" on a RUNNING build. The
-- worker checks it before every model call and every sandbox run, stops
-- there, settles only what was really used and writes CANCELLED. A QUEUED
-- build is cancelled directly by the API (the worker's QUEUED -> RUNNING
-- claim then fails, so it never starts).
--
-- build_events: an append-only, human-readable log of the build's steps
-- (phase changes, model calls by task, test runs and their result). It is
-- what the workspace shows as the live log. Messages never contain secrets
-- or generated code; they are short sentences written by the worker.

ALTER TABLE build_jobs ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMPTZ;
ALTER TABLE build_jobs ADD COLUMN IF NOT EXISTS cancel_requested_by TEXT;

CREATE TABLE IF NOT EXISTS build_events (
    seq        BIGSERIAL PRIMARY KEY,
    build_id   TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
    at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kind       TEXT NOT NULL CHECK (kind IN ('phase', 'model', 'check', 'repair', 'cancel', 'info')),
    message    TEXT NOT NULL CHECK (length(message) <= 600)
);

CREATE INDEX IF NOT EXISTS idx_build_events_build_seq ON build_events (build_id, seq);

-- Directive §13: whether a preview's product data survives a restart and a
-- new version ('persistent', one directory per project on the preview host)
-- or lives only in the container's tmpfs ('temporary'). NULL = before 031.
ALTER TABLE project_previews ADD COLUMN IF NOT EXISTS data_storage TEXT
    CHECK (data_storage IS NULL OR data_storage IN ('persistent', 'temporary'));
