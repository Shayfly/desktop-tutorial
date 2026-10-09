-- Durable agent execution (migration 034). Autonomous completion directive §12.
--
-- agent_runs: one task graph per build or change.
-- agent_tasks: one row per agent task; state machine enforced by the runtime
--   (PENDING, READY, RUNNING, WAITING, BLOCKED, VERIFYING, REPAIRING,
--    SUCCEEDED, FAILED, CANCEL_REQUESTED, CANCELLED); survives restarts.
--   verified_by_task points at the independent verifier's task.
-- agent_handoffs: structured handoffs between agents (payload refs only).
-- agent_memory: per-project, per-agent facts (no secrets).
-- platform_check_results: results of real-server golden/post-deploy checks,
--   the evidence the capability auditor and the quality gate read.

CREATE TABLE IF NOT EXISTS agent_runs (
    id           TEXT PRIMARY KEY,
    subject_kind TEXT NOT NULL CHECK (subject_kind IN ('build', 'modification', 'check')),
    subject_id   TEXT NOT NULL,
    budget_usd   NUMERIC(12, 6),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    outcome      TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_subject ON agent_runs (subject_kind, subject_id);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    agent_key        TEXT NOT NULL,
    skill_keys       JSONB NOT NULL DEFAULT '[]'::jsonb,
    state            TEXT NOT NULL CHECK (state IN ('PENDING', 'READY', 'RUNNING', 'WAITING', 'BLOCKED', 'VERIFYING',
                                                     'REPAIRING', 'SUCCEEDED', 'FAILED', 'CANCEL_REQUESTED', 'CANCELLED')),
    depends_on       JSONB NOT NULL DEFAULT '[]'::jsonb,
    attempt          INTEGER NOT NULL DEFAULT 1,
    budget_usd       NUMERIC(12, 6),
    cost_usd         NUMERIC(12, 6) NOT NULL DEFAULT 0,
    verified_by_task TEXT,
    evidence         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_run ON agent_tasks (run_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON agent_tasks (agent_key, finished_at);

CREATE TABLE IF NOT EXISTS agent_handoffs (
    id         BIGSERIAL PRIMARY KEY,
    run_id     TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    from_task  TEXT NOT NULL,
    to_agent   TEXT NOT NULL,
    payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_memory (
    project_id TEXT NOT NULL,
    agent_key  TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, agent_key, key)
);

CREATE TABLE IF NOT EXISTS platform_check_results (
    id         BIGSERIAL PRIMARY KEY,
    check_key  TEXT NOT NULL,
    stage      TEXT NOT NULL,
    passed     BOOLEAN NOT NULL,
    detail     TEXT NOT NULL DEFAULT '' CHECK (length(detail) <= 2000),
    commit_sha TEXT,
    at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_platform_check_results_key ON platform_check_results (check_key, at DESC);
