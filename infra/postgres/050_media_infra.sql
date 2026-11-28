-- 050: the media infrastructure (the owner, 2026-11-27, answer 6: warehouse item 137 is released for the INFRASTRUCTURE
-- only -- storage, tenant isolation, a rights record and a render queue; no provider and no spend).
-- Two tables, both additive; neither is read by anything that exists today, so the release that ships omni_prod/
-- asset_rights.py and omni_prod/media_queue.py may run before or after this migration is applied, and both modules say
-- "migration 050 not applied" out loud when the table is missing.
--   asset_rights      one row per generated asset: who made it, on what terms, may it be sold, and who owns it. The
--                     owner column can only say 'customer' (the owner's rule: what a customer generates is the customer's).
--                     A row is never updated and never deleted by the application: a rights record is evidence. A
--                     deletion of a customer's data is a migration of the owner's, which drops the trigger first.
--   media_render_jobs the render queue of a song, a clip or a sprite sheet: one row per job, claimed by a worker under a
--                     lease, with a bounded number of attempts and a total time budget. A killed worker's lease expires
--                     and the job returns to the queue (or ends 'dead' / 'failed'), never stays 'running' forever.
-- Rollback: infra/postgres/rollback/050_media_infra.down.sql (by hand, the owner's approval, CLAUDE.md section 5).
CREATE TABLE IF NOT EXISTS asset_rights (
    id               BIGSERIAL   PRIMARY KEY,
    account_id       TEXT        NOT NULL,
    project_id       TEXT        NOT NULL,
    build_id         TEXT,
    sha256           TEXT        NOT NULL,
    media_key        TEXT        NOT NULL,
    kind             TEXT        NOT NULL,
    mime             TEXT        NOT NULL,
    provider         TEXT        NOT NULL,
    model            TEXT        NOT NULL,
    provider_task_id TEXT,
    terms_url        TEXT        NOT NULL,
    terms_read_on    DATE        NOT NULL,
    commercial_use   BOOLEAN     NOT NULL,
    owner            TEXT        NOT NULL DEFAULT 'customer',
    restrictions     TEXT        NOT NULL DEFAULT '',
    prompt_sha256    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT asset_rights_one_per_asset UNIQUE (account_id, project_id, sha256),
    CONSTRAINT asset_rights_sha256_is_a_digest CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT asset_rights_prompt_is_a_digest CHECK (prompt_sha256 IS NULL OR prompt_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT asset_rights_key_is_the_tenants CHECK (starts_with(media_key, 'tenants/' || account_id || '/projects/' || project_id || '/media/')),
    CONSTRAINT asset_rights_owner_is_the_customer CHECK (owner = 'customer'),
    CONSTRAINT asset_rights_kind CHECK (kind IN ('image', 'sprite', 'audio', 'video', 'model')),
    CONSTRAINT asset_rights_terms_are_a_link CHECK (terms_url ~ '^https://[^ ]+$'),
    CONSTRAINT asset_rights_provider_named CHECK (btrim(provider) <> '' AND btrim(model) <> '')
);
CREATE INDEX IF NOT EXISTS asset_rights_by_terms_date ON asset_rights (terms_read_on);

CREATE OR REPLACE FUNCTION asset_rights_are_evidence() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'asset_rights is append-only: a rights record is evidence (% refused)', TG_OP;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS asset_rights_append_only ON asset_rights;
CREATE TRIGGER asset_rights_append_only BEFORE UPDATE OR DELETE ON asset_rights
    FOR EACH ROW EXECUTE FUNCTION asset_rights_are_evidence();

CREATE TABLE IF NOT EXISTS media_render_jobs (
    job_id           TEXT        PRIMARY KEY,
    account_id       TEXT        NOT NULL,
    project_id       TEXT        NOT NULL,
    build_id         TEXT        NOT NULL,
    kind             TEXT        NOT NULL,
    idempotency_key  TEXT        NOT NULL,
    payload          JSONB       NOT NULL,
    payload_sha256   TEXT        NOT NULL,
    status           TEXT        NOT NULL DEFAULT 'queued',
    attempts         INTEGER     NOT NULL DEFAULT 0,
    max_attempts     INTEGER     NOT NULL,
    budget_seconds   INTEGER     NOT NULL,
    lease_owner      TEXT,
    lease_expires_at TIMESTAMPTZ,
    result           JSONB,
    error_code       TEXT,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,
    CONSTRAINT media_render_jobs_one_per_request UNIQUE (account_id, idempotency_key),
    CONSTRAINT media_render_jobs_job_id CHECK (job_id ~ '^mrj_[0-9a-f]{32}$'),
    CONSTRAINT media_render_jobs_kind CHECK (kind ~ '^[a-z][a-z0-9_]{0,31}$'),
    CONSTRAINT media_render_jobs_status CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'dead')),
    CONSTRAINT media_render_jobs_attempts CHECK (max_attempts BETWEEN 1 AND 5 AND attempts BETWEEN 0 AND max_attempts),
    CONSTRAINT media_render_jobs_budget CHECK (budget_seconds BETWEEN 1 AND 7200),
    CONSTRAINT media_render_jobs_lease_iff_running CHECK ((status = 'running') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)),
    CONSTRAINT media_render_jobs_finished_iff_ended CHECK ((status IN ('succeeded', 'failed', 'dead')) = (finished_at IS NOT NULL)),
    CONSTRAINT media_render_jobs_failure_has_a_code CHECK (status NOT IN ('failed', 'dead') OR error_code IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS media_render_jobs_waiting ON media_render_jobs (created_at) WHERE status IN ('queued', 'running');
