-- Attempt Ledger (migration 027): one immutable row per provider call or
-- verification run inside a build. Source of truth for execution evidence and
-- measured cost (Operating Contract 29A). Rows are append-only; the only
-- later write is final_outcome when the build reaches a terminal state.
--
-- Cost truth (three layers, never merged):
--   authorized_cost_usd     maximum authorized before the call (budget gate)
--   expected_cost_usd       estimator output; NULL until an estimator exists
--   metered_cost_usd        usage measured by us x versioned catalog price
--   provider_reported_cost_usd  the provider's own figure, if it sent one
--   reconciled_cost_usd     matched to the provider invoice (later process)
-- NULL means "not known", never zero.

CREATE TABLE IF NOT EXISTS task_attempts (
    attempt_id                  TEXT PRIMARY KEY,
    build_id                    TEXT NOT NULL,
    tenant_id                   TEXT,
    project_id                  TEXT,
    task_id                     TEXT NOT NULL,
    task_type                   TEXT NOT NULL,
    attempt_seq                 INTEGER NOT NULL CHECK (attempt_seq >= 0),
    kind                        TEXT NOT NULL CHECK (kind IN ('provider_call', 'verification')),
    provider                    TEXT,
    model                       TEXT,
    model_version               TEXT,
    provider_request_id         TEXT,
    trace_id                    TEXT,
    policy_version              TEXT,
    routing_policy_version      TEXT,
    prompt_version              TEXT,
    price_catalog_version       TEXT,
    selection_reason            TEXT,
    selected_candidate          TEXT,
    candidate_set               JSONB,
    fallback_rank               INTEGER CHECK (fallback_rank IS NULL OR fallback_rank >= 0),
    reservation_id              TEXT,
    authorized_cost_usd         NUMERIC(14, 8) CHECK (authorized_cost_usd IS NULL OR authorized_cost_usd >= 0),
    expected_cost_usd           NUMERIC(14, 8) CHECK (expected_cost_usd IS NULL OR expected_cost_usd >= 0),
    metered_cost_usd            NUMERIC(14, 8) CHECK (metered_cost_usd IS NULL OR metered_cost_usd >= 0),
    provider_reported_cost_usd  NUMERIC(14, 8) CHECK (provider_reported_cost_usd IS NULL OR provider_reported_cost_usd >= 0),
    reconciled_cost_usd         NUMERIC(14, 8) CHECK (reconciled_cost_usd IS NULL OR reconciled_cost_usd >= 0),
    input_tokens                INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens               INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    cached_tokens               INTEGER CHECK (cached_tokens IS NULL OR cached_tokens >= 0),
    latency_ms                  INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    outcome                     TEXT NOT NULL CHECK (outcome IN ('ok', 'error', 'unknown')),
    verification_class          TEXT CHECK (verification_class IS NULL OR verification_class IN
                                    ('PASS', 'REPAIRABLE_FAIL', 'RETRYABLE_FAIL', 'ESCALATABLE_FAIL', 'FATAL_FAIL')),
    failure_reason              TEXT,
    final_outcome               TEXT,
    -- Data governance (Operating Contract 29J)
    data_sensitivity            TEXT NOT NULL DEFAULT 'tenant_private',
    training_eligible           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_attempts_build ON task_attempts(build_id, attempt_seq);
CREATE INDEX IF NOT EXISTS idx_task_attempts_model_task ON task_attempts(model, task_type, created_at);
CREATE INDEX IF NOT EXISTS idx_task_attempts_tenant ON task_attempts(tenant_id, created_at);
