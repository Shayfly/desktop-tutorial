-- 013_durable_async_builds.sql
-- Idempotent schema additions for M1 Durable Async Builds
-- Verified against infra/postgres/001_control_plane.sql (build_jobs),
-- 010_international_product.sql (project_versions), 012_creator_subscriptions.sql
-- (creator_subscriptions) before being applied. Applied verbatim from the pasted
-- M1 Revision 2 patch -- schema-compatible with the existing tables.

CREATE TABLE IF NOT EXISTS credit_reservations (
    build_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    credits_reserved INTEGER NOT NULL CHECK (credits_reserved >= 0),
    estimated_provider_cost_usd NUMERIC(14,6) NOT NULL DEFAULT 0,
    actual_provider_cost_usd NUMERIC(14,6),
    settled_provider_cost_usd NUMERIC(14,6),
    status TEXT NOT NULL CHECK (status IN ('RESERVED', 'SETTLED', 'RELEASED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS build_requests (
    build_id TEXT PRIMARY KEY REFERENCES credit_reservations(build_id),
    user_id TEXT NOT NULL,
    internal_project_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    target_markets JSONB NOT NULL DEFAULT '[]'::jsonb,
    branding_visible BOOLEAN,
    white_label_name TEXT,
    rights_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enhance build_jobs with phase, explicit costs, and evidence
ALTER TABLE build_jobs
    ADD COLUMN IF NOT EXISTS phase TEXT NOT NULL DEFAULT 'QUEUED',
    ADD COLUMN IF NOT EXISTS message TEXT,
    ADD COLUMN IF NOT EXISTS result_version_id TEXT,
    ADD COLUMN IF NOT EXISTS actual_provider_cost_usd NUMERIC(14,6),
    ADD COLUMN IF NOT EXISTS estimated_provider_cost_usd NUMERIC(14,6),
    ADD COLUMN IF NOT EXISTS repair_rounds INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Ensure project_versions can store the artifact explicitly
ALTER TABLE project_versions
    ADD COLUMN IF NOT EXISTS artifact_key TEXT,
    ADD COLUMN IF NOT EXISTS file_count INTEGER NOT NULL DEFAULT 0;

-- Transactional Outbox for Redis Enqueueing
CREATE TABLE IF NOT EXISTS build_outbox (
    id BIGSERIAL PRIMARY KEY,
    build_id TEXT NOT NULL UNIQUE REFERENCES build_requests(build_id),
    enqueued_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
