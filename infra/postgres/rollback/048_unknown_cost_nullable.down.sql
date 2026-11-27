-- Rollback of 048_unknown_cost_nullable. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval (CLAUDE.md section 5: backup branch first).
-- An unknown cost becomes 0 again (the pre-048 meaning; the 'unpriced:' marker and the evidence still say it was
-- unknown) and NOT NULL is restored. Touches nothing else.
BEGIN;
UPDATE build_jobs SET ai_cost = 0 WHERE ai_cost IS NULL;
UPDATE build_jobs SET build_seconds = 0 WHERE build_seconds IS NULL;
UPDATE provider_usage_events SET estimated_cost_usd = 0 WHERE estimated_cost_usd IS NULL;
ALTER TABLE build_jobs ALTER COLUMN ai_cost SET NOT NULL;
ALTER TABLE build_jobs ALTER COLUMN build_seconds SET NOT NULL;
ALTER TABLE provider_usage_events ALTER COLUMN estimated_cost_usd SET NOT NULL;
DELETE FROM schema_migrations WHERE version = 48;
COMMIT;
