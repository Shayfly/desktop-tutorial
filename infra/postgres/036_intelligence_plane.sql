-- Wave A intelligence control plane (migration 036). Additive only; rollback =
-- DROP TABLE provider_health, intake_messages, execution_plans (no other table
-- references them).
--
-- provider_health: durable circuit breaker per model route (route name only;
--   never keys or request content). Read by every gateway before routing.
-- intake_messages: the customer's free-text intake conversation per project,
--   bound to the brief revision it produced. The brief (project_briefs) stays
--   the source of truth; these rows are the audit trail of how it changed.
-- execution_plans: the Chief Architect's validated plan + task DAG for one
--   brief revision (immutable; identified by its content fingerprint).

CREATE TABLE IF NOT EXISTS provider_health (
    route       TEXT PRIMARY KEY,
    state       TEXT NOT NULL CHECK (state IN ('HEALTHY', 'DEGRADED', 'RATE_LIMITED', 'CREDIT_EXHAUSTED', 'AUTH_INVALID',
                                               'UNAVAILABLE', 'RETIRED', 'UNKNOWN')),
    detail      TEXT NOT NULL DEFAULT '' CHECK (length(detail) <= 300),
    since       TIMESTAMPTZ,
    open_until  TIMESTAMPTZ,
    recheck_at  TIMESTAMPTZ,
    failures    INTEGER NOT NULL DEFAULT 0,
    reset_by    TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intake_messages (
    id              BIGSERIAL PRIMARY KEY,
    project_id      TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('customer', 'assistant')),
    content         TEXT NOT NULL CHECK (length(content) <= 8000),
    brief_revision  INTEGER,
    interpretation  JSONB NOT NULL DEFAULT '{}'::jsonb,
    interpreter     TEXT NOT NULL DEFAULT 'deterministic',
    cost_usd        NUMERIC(12, 6) NOT NULL DEFAULT 0,
    request_key     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_intake_messages_project ON intake_messages (project_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_messages_request
    ON intake_messages (project_id, request_key, role) WHERE request_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS execution_plans (
    id                TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL,
    brief_revision    INTEGER NOT NULL,
    brief_fingerprint TEXT NOT NULL,
    plan_schema       TEXT NOT NULL,
    fingerprint       TEXT NOT NULL,
    plan              JSONB NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_execution_plans_project ON execution_plans (project_id, brief_revision);
