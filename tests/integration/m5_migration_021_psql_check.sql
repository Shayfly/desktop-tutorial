-- M5 Task 7 local evidence script for migration 021 (run with psql -v ON_ERROR_STOP=1).
-- Applies the migration twice (idempotency) and proves the database itself
-- rejects plaintext secrets and binding ownership changes.
\set ON_ERROR_STOP 1
\i infra/postgres/021_generated_app_bindings.sql
\i infra/postgres/021_generated_app_bindings.sql

INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, project_id,
    environment, kind, status, resource_name, provisioner, secret_references)
VALUES ('ib_ok', 'key_ok', 'managed_web_saas_v1', 'usr_1', 'prj_1', 'preview', 'database', 'LIVE',
        'ga_x_prev_database', 'managed_web_saas',
        '{"database_url": "vault:secret/data/148ai/generated-apps/x/preview/database/database_url"}');

\set ON_ERROR_STOP 0
\echo EXPECT_REJECT plaintext secret
INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, project_id,
    environment, kind, status, resource_name, provisioner, secret_references)
VALUES ('ib_bad', 'key_bad', 'managed_web_saas_v1', 'usr_1', 'prj_1', 'preview', 'auth_session', 'LIVE',
        'r', 'p', '{"session_signing_secret": "hunter2-plaintext"}');
\echo EXPECT_REJECT dsn with password
INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, project_id,
    environment, kind, status, resource_name, provisioner, secret_references)
VALUES ('ib_bad2', 'key_bad2', 'managed_web_saas_v1', 'usr_1', 'prj_1', 'preview', 'auth_session', 'LIVE',
        'r', 'p', '{"database_url": "postgresql://u:pw@h/db"}');
\echo EXPECT_REJECT ownership change
UPDATE generated_app_bindings SET tenant_id = 'intruder' WHERE binding_id = 'ib_ok';
\echo EXPECT_REJECT duplicate scope
INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, project_id,
    environment, kind, status, resource_name, provisioner, secret_references)
VALUES ('ib_dup', 'key_dup', 'managed_web_saas_v1', 'usr_2', 'prj_1', 'preview', 'database', 'LIVE',
        'r', 'p', '{"database_url": "vault:secret/data/x"}');
\echo EXPECT_REJECT revoked without timestamp
UPDATE generated_app_bindings SET status = 'REVOKED' WHERE binding_id = 'ib_ok';
\set ON_ERROR_STOP 1
\echo EXPECT_ACCEPT status update keeps ownership
UPDATE generated_app_bindings SET status = 'REVOKED', revoked_at = now() WHERE binding_id = 'ib_ok';
SELECT binding_id, tenant_id, status, revoked_at IS NOT NULL AS revoked FROM generated_app_bindings;
