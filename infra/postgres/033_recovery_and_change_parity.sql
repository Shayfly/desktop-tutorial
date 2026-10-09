-- Crash recovery and change (modification) parity (migration 033).
-- Autonomous completion directive §5.
--
-- heartbeat_at: written by the worker at every step boundary (before each
-- model call and each sandbox run). A RUNNING job whose heartbeat is older
-- than the recovery limit lost its worker (crash, OOM, host restart); the
-- janitor puts it back in the queue once (recovery_attempts) and fails it
-- after that, releasing its reservation. A stop request on such a job ends
-- it CANCELLED instead.
--
-- Changes get the same stop flag, heartbeat and live log as builds:
-- build_events now carries both kinds (job_kind); the foreign key to
-- build_jobs is dropped so a change's id can be logged (ownership is checked
-- by the API through the owning table).

ALTER TABLE build_jobs ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;
ALTER TABLE build_jobs ADD COLUMN IF NOT EXISTS recovery_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE modification_requests ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMPTZ;
ALTER TABLE modification_requests ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;
ALTER TABLE modification_requests ADD COLUMN IF NOT EXISTS recovery_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE modification_requests DROP CONSTRAINT IF EXISTS modification_requests_status_check;
ALTER TABLE modification_requests ADD CONSTRAINT modification_requests_status_check CHECK (status IN (
    'QUEUED', 'RUNNING', 'NEEDS_CLARIFICATION', 'READY_FOR_REVIEW',
    'ACCEPTED', 'REJECTED', 'FAILED', 'CONFLICT', 'CANCELLED'
));

ALTER TABLE build_events DROP CONSTRAINT IF EXISTS build_events_build_id_fkey;
ALTER TABLE build_events ADD COLUMN IF NOT EXISTS job_kind TEXT NOT NULL DEFAULT 'build'
    CHECK (job_kind IN ('build', 'modification'));
