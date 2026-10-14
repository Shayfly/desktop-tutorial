# M5 Task 7 — local Postgres evidence (2026-10-04)

Scope: LOCAL ONLY. Disposable PostgreSQL 16.15 started in the implementer sandbox; no staging, Vault, S3 or scheduler was available. This is evidence for migration 021 and the binding repository SQL, not for LIVE generated-app infrastructure.

Command: `psql -d m5_t7 -f tests/integration/m5_migration_021_psql_check.sql`

```
INSERT 0 1
EXPECT_REJECT plaintext secret
psql:tests/integration/m5_migration_021_psql_check.sql:19: ERROR:  new row for relation "generated_app_bindings" violates check constraint "generated_app_bindings_refs_only"
EXPECT_REJECT dsn with password
psql:tests/integration/m5_migration_021_psql_check.sql:24: ERROR:  new row for relation "generated_app_bindings" violates check constraint "generated_app_bindings_refs_only"
EXPECT_REJECT ownership change
psql:tests/integration/m5_migration_021_psql_check.sql:26: ERROR:  cannot change binding ownership of generated app binding ib_ok
EXPECT_REJECT duplicate scope
psql:tests/integration/m5_migration_021_psql_check.sql:31: ERROR:  duplicate key value violates unique constraint "generated_app_bindings_scope"
EXPECT_REJECT revoked without timestamp
psql:tests/integration/m5_migration_021_psql_check.sql:33: ERROR:  new row for relation "generated_app_bindings" violates check constraint "generated_app_bindings_revoked_at"

EXPECT_ACCEPT status update keeps ownership
UPDATE 1
 ib_ok      | usr_1     | REVOKED | t
```

Results: migration applies twice (idempotent); plaintext secret and credential-bearing DSN rejected by CHECK generated_app_bindings_refs_only; ownership change rejected by trigger; duplicate (profile, project, environment, kind) rejected; REVOKED without revoked_at rejected; status update preserving ownership accepted.

The exact INSERT ... ON CONFLICT (idempotency_key) DO UPDATE and SELECT statements emitted by PostgresInfrastructureBindingRepository were rendered with literal parameters and executed against the same database (insert, revoke-upsert, list_for, get_by_idempotency_key): all succeeded and returned the revoked row with references only.

Not verified here: psycopg driver path (psycopg not installable in this sandbox), real Vault/S3/scheduler provisioning (tests/integration/test_m5_managed_web_saas_live.py SKIPs without M5_GENAPP_LIVE=1 and OMNI_GENAPP_* configuration).
