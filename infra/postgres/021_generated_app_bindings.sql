-- M5 Task 7: durable generated-app infrastructure bindings.
-- One row per (profile, project, environment, kind). Rows hold secret
-- REFERENCES (env:/vault:) only; the database rejects anything else.
-- Ownership (tenant/project/environment/kind/profile) is immutable once written.

CREATE TABLE IF NOT EXISTS generated_app_bindings (
    binding_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    profile_key TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('preview','production')),
    kind TEXT NOT NULL CHECK (kind IN ('database','auth_session','object_storage','scheduled_http','outbound')),
    status TEXT NOT NULL CHECK (status IN ('LIVE','NOT_CONFIGURED','BLOCKED','REVOKED')),
    resource_name TEXT NOT NULL,
    provisioner TEXT NOT NULL,
    secret_references JSONB NOT NULL DEFAULT '{}'::jsonb,
    public_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    status_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT generated_app_bindings_idempotency UNIQUE (idempotency_key),
    CONSTRAINT generated_app_bindings_scope UNIQUE (profile_key, project_id, environment, kind),
    CONSTRAINT generated_app_bindings_refs_object CHECK (jsonb_typeof(secret_references) = 'object'),
    -- every secret_references value must be an env: or vault: reference, never a value
    CONSTRAINT generated_app_bindings_refs_only CHECK (
        NOT jsonb_path_exists(secret_references, '$.* ? (!(@ like_regex "^(env|vault):[A-Za-z0-9_./-]+$"))')
    ),
    CONSTRAINT generated_app_bindings_revoked_at CHECK ((status = 'REVOKED') = (revoked_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_generated_app_bindings_project_env
    ON generated_app_bindings(project_id, environment);

CREATE OR REPLACE FUNCTION reject_generated_app_binding_ownership_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.project_id IS DISTINCT FROM OLD.project_id
       OR NEW.environment IS DISTINCT FROM OLD.environment
       OR NEW.kind IS DISTINCT FROM OLD.kind
       OR NEW.profile_key IS DISTINCT FROM OLD.profile_key
       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
        RAISE EXCEPTION 'cannot change binding ownership of generated app binding %', OLD.binding_id;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generated_app_bindings_ownership ON generated_app_bindings;
CREATE TRIGGER trg_generated_app_bindings_ownership
BEFORE UPDATE ON generated_app_bindings
FOR EACH ROW EXECUTE FUNCTION reject_generated_app_binding_ownership_change();
