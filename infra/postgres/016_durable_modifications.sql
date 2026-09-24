-- 016_durable_modifications.sql
-- M4A/M4B: durable natural-language product modification workflow.
-- Forward-only and idempotent, following 013-015's pattern: new tables plus
-- additive columns, nothing edited in place. Verified against
-- 001_control_plane.sql (project_versions), 011_creator_accounts.sql
-- (creator accounts / project keys) and 013_durable_async_builds.sql
-- (build_outbox / credit_reservations -- reused as-is for modification
-- billing, see the note on reservation_id below) before being written.

-- M4B: one immutable ProductSpec row per ProjectVersion id. version_id is the
-- primary key (not a surrogate id) precisely so there is exactly one spec per
-- version and no way to accidentally load "the latest spec" for a project
-- instead of the exact spec tied to the version being modified -- the
-- invariant M4B's directive names explicitly. No UPDATE path is used against
-- this table anywhere in this codebase (see spec_repository.py): a spec
-- "changing" always means a *new* version getting its own new row.
CREATE TABLE IF NOT EXISTS project_version_specs (
    version_id TEXT PRIMARY KEY REFERENCES project_versions(id),
    project_id TEXT NOT NULL,
    spec_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_version_specs_project
ON project_version_specs(project_id, created_at DESC);

-- M4A: the durable ModificationRequest.
--
-- promoted_version_id is set only by accept(), and records the *new*
-- project_versions row created when a candidate was promoted to current
-- (see modification_repository.py's accept() -- it commits the candidate's
-- stored repository as a brand-new version, the same append-only way every
-- other write path produces a new version -- nothing is edited in place).
--
-- Deliberately NOT present here: candidate_version_id / candidate_spec_
-- version_id as columns referencing project_versions. An unreviewed
-- candidate is intentionally never committed into project_versions (see
-- modification_candidates below) -- committing it early would make an
-- unreviewed build transiently "current" and would corrupt the very
-- concurrency scenario M4 requires (two candidates built against the same
-- source version N must both still show N as their logical base when
-- reviewed, which only holds if building a candidate never advances
-- `current`). The candidate becomes a real project_versions row for the
-- first time inside accept(), at which point its id is recorded here as
-- promoted_version_id.
CREATE TABLE IF NOT EXISTS modification_requests (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    source_version_id TEXT NOT NULL REFERENCES project_versions(id),
    source_spec_version_id TEXT NOT NULL REFERENCES project_versions(id),
    followup TEXT NOT NULL,
    -- Captured durably at creation time (mirrors build_requests.rights_evidence
    -- -- see job_repository.py / worker_tasks._rights_evidence_from_dicts),
    -- not read from in-memory API-process state when the worker runs: the
    -- worker is a separate process/host and must not depend on the API
    -- process's own memory for a compliance-relevant gate input.
    target_markets_json JSONB NOT NULL DEFAULT '["US", "EU", "IL"]'::jsonb,
    rights_evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL CHECK (status IN (
        'QUEUED', 'RUNNING', 'NEEDS_CLARIFICATION', 'READY_FOR_REVIEW',
        'ACCEPTED', 'REJECTED', 'FAILED', 'CONFLICT'
    )),
    classification TEXT CHECK (classification IN ('system_bug', 'missing_requirement', 'change_request', 'ambiguous')),
    classification_reason TEXT,
    billable BOOLEAN,
    promoted_version_id TEXT REFERENCES project_versions(id),
    repair_rounds INTEGER NOT NULL DEFAULT 0,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT,
    error_message TEXT,
    -- M4G: reuses credit_reservations(build_id) as a generic reservation key
    -- (see subscription_store.py's reserve/settle/release) -- that column is
    -- not foreign-keyed to build_jobs, so a modification_id is a valid key
    -- for it. reservation_id is stored here rather than assumed to equal
    -- `id` so a future reservation scheme change doesn't have to touch this
    -- table's primary key.
    reservation_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_modification_requests_project
ON modification_requests(project_id, created_at DESC);

-- Acceptance test U (concurrency): finding every other still-open
-- modification against the same source version once one of them is accepted.
CREATE INDEX IF NOT EXISTS idx_modification_requests_source_version
ON modification_requests(source_version_id, status);

-- M4C/M4D: the pending candidate produced by a READY_FOR_REVIEW completion --
-- a repository + spec pair that is NOT yet a project_versions row (see the
-- comment on modification_requests above for why). One row per modification,
-- written atomically with the READY_FOR_REVIEW status flip in complete();
-- read back by accept() to promote it, or by a review UI to show it. project_id
-- is denormalized here (rather than requiring a join back to
-- modification_requests) the same way project_version_specs denormalizes it
-- for project_versions in M4B above -- cheap, tenant-scoped reads.
CREATE TABLE IF NOT EXISTS modification_candidates (
    modification_id TEXT PRIMARY KEY REFERENCES modification_requests(id),
    project_id TEXT NOT NULL,
    repository_json JSONB NOT NULL,
    spec_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- M4A: transactional outbox for Redis enqueueing, identical shape and
-- purpose to build_outbox (013) -- a separate table because
-- modification_requests.id has no FK relationship to build_requests, and
-- reusing build_outbox would conflate two different queues' pending-dispatch
-- bookkeeping.
CREATE TABLE IF NOT EXISTS modification_outbox (
    id BIGSERIAL PRIMARY KEY,
    modification_id TEXT NOT NULL UNIQUE REFERENCES modification_requests(id),
    enqueued_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_modification_outbox_pending
ON modification_outbox(created_at)
WHERE enqueued_at IS NULL;
