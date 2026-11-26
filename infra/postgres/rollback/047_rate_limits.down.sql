-- Rollback of 047_rate_limits. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval (CLAUDE.md section 5: backup branch first). It
-- DELETES the rate-limit counters -- counters only, no customer data. Roll back the code that reads the table FIRST:
-- while omni_prod/rate_limits.py runs without it, the sign-in routes answer 503 (they fail closed by design).
BEGIN;
DROP INDEX IF EXISTS rate_limit_counters_expiry;
DROP TABLE IF EXISTS rate_limit_counters;
DELETE FROM schema_migrations WHERE version = 47;
COMMIT;
