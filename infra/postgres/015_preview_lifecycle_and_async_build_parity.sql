-- 015_preview_lifecycle_and_async_build_parity.sql
-- M3 Revision 2 + M1 blocker resolution. Forward-only and idempotent: 014 may
-- already be applied in some environment, so it is extended here rather than
-- edited in place.

-- 1. NOT_PREVIEWABLE is a distinct terminal state (artifact cannot satisfy the
--    preview contract) -- not a runtime FAILED. 014 declared the status CHECK
--    inline on the column, which Postgres names project_previews_status_check.
ALTER TABLE project_previews DROP CONSTRAINT IF EXISTS project_previews_status_check;
ALTER TABLE project_previews ADD CONSTRAINT project_previews_status_check
    CHECK (status IN ('STARTING', 'RUNNING', 'STOPPED', 'FAILED', 'EXPIRED', 'NOT_PREVIEWABLE'));

-- 2. Distributed lifecycle: which host runs the container (stop tasks are
--    routed to that host's queue), the Docker-allocated host port (the
--    external router's upstream), and the bind-mounted source directory the
--    stop task must delete.
ALTER TABLE project_previews
    ADD COLUMN IF NOT EXISTS runtime_host TEXT,
    ADD COLUMN IF NOT EXISTS host_port INTEGER CHECK (host_port IS NULL OR (host_port BETWEEN 1 AND 65535)),
    ADD COLUMN IF NOT EXISTS workdir_path TEXT,
    ADD COLUMN IF NOT EXISTS stopped_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cleaned_at TIMESTAMPTZ;

-- 3. The async build worker runs branding/provenance decoration, which embeds
--    the user-facing project id. build_requests only stored the internal
--    tenant key; nullable so rows written before this migration still load.
ALTER TABLE build_requests
    ADD COLUMN IF NOT EXISTS public_project_id TEXT;

-- 4. Outbox relay: finds rows whose Redis enqueue never happened.
CREATE INDEX IF NOT EXISTS idx_build_outbox_pending
ON build_outbox(created_at)
WHERE enqueued_at IS NULL;
