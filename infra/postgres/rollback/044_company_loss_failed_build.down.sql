-- Rollback of 044_company_loss_failed_build. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval. It DELETES the loss rows of failed builds
-- (cause failed_build_refunded) -- their cost stays on credit_reservations.settled_provider_cost_usd -- and restores
-- the three-cause constraint. Touches nothing else.
BEGIN;
DELETE FROM company_loss_events WHERE cause = 'failed_build_refunded';
ALTER TABLE company_loss_events DROP CONSTRAINT IF EXISTS company_loss_events_cause_known;
ALTER TABLE company_loss_events ADD CONSTRAINT company_loss_events_cause_known CHECK (
    cause IN ('metered_overrun', 'budget_capped_shortfall', 'unreconciled_unknown'));
DELETE FROM schema_migrations WHERE version = 44;
COMMIT;
