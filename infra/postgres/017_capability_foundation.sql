-- 017_capability_foundation.sql
-- Durable M4.95 capability requirements, provider executions and usage evidence.

CREATE TABLE IF NOT EXISTS build_capability_requirements (
    build_id TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
    requirement_id TEXT NOT NULL,
    capability_key TEXT NOT NULL,
    purpose TEXT NOT NULL,
    required BOOLEAN NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 1),
    constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dependency_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (
        status IN ('PLANNED','QUOTED','RESERVED','QUEUED','RUNNING','GENERATED',
                   'VERIFIED','FAILED','CANCELLED','SKIPPED','NOT_CONFIGURED','BLOCKED')
    ),
    selected_provider TEXT,
    pricing_version TEXT,
    estimated_cost_usd NUMERIC(18,8),
    maximum_cost_usd NUMERIC(18,8),
    actual_cost_usd NUMERIC(18,8),
    artifact_key TEXT,
    verification_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
    CHECK (maximum_cost_usd IS NULL OR maximum_cost_usd >= COALESCE(estimated_cost_usd, 0)),
    CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
    PRIMARY KEY (build_id, requirement_id)
);

CREATE INDEX IF NOT EXISTS idx_build_capability_requirements_status
    ON build_capability_requirements(build_id, status);
CREATE INDEX IF NOT EXISTS idx_build_capability_requirements_key
    ON build_capability_requirements(capability_key, created_at DESC);

-- Execution state and lease ownership are deliberately separate. The row is
-- durably created in SUBMITTING before any external paid submit; lease fields
-- are nullable until a worker claims it. A restarted worker reuses the same
-- idempotency_key/provider_task_id instead of creating a second paid job.
CREATE TABLE IF NOT EXISTS provider_execution_attempts (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    pricing_version TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    provider_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'SUBMITTING' CHECK (
        status IN ('SUBMITTING','SUBMITTED','RUNNING','SUCCEEDED','FAILED','CANCELLED')
    ),
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    last_error_code TEXT,
    last_error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (build_id, requirement_id)
        REFERENCES build_capability_requirements(build_id, requirement_id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_execution_external_task
    ON provider_execution_attempts(provider, provider_task_id)
    WHERE provider_task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_provider_execution_resume
    ON provider_execution_attempts(status, lease_expires_at);

CREATE TABLE IF NOT EXISTS provider_usage_events (
    id BIGSERIAL PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    build_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    pricing_version TEXT NOT NULL,
    estimated_cost_usd NUMERIC(18,8) NOT NULL CHECK (estimated_cost_usd >= 0),
    maximum_cost_usd NUMERIC(18,8) NOT NULL CHECK (maximum_cost_usd >= estimated_cost_usd),
    actual_cost_usd NUMERIC(18,8),
    usage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
    FOREIGN KEY (build_id, requirement_id)
        REFERENCES build_capability_requirements(build_id, requirement_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_provider_usage_build
    ON provider_usage_events(build_id, requirement_id, provider);
