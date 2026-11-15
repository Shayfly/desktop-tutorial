-- 044: a failed build's provider cost is a company loss (warehouse 103, released by the owner 2026-11-15).
-- The customer is refunded in full (subscription_store.release_failed, DELIVERY-001); the provider was paid. Until now
-- that cost stayed only on the reservation (settled_provider_cost_usd) and never reached company_loss_events, the one
-- durable answer to "how much did we lose, and on what". This widens the closed set of causes by one value.
-- No row is read, changed or deleted; the CHECK constraint is dropped and recreated with the fourth cause. Older code
-- keeps writing the three causes it knows (rollback tolerance, test_migration_rollback_tolerance).
-- A migration: runs only with the owner's explicit approval, given on the PR before merge (CLAUDE.md section 5).
-- Rollback: infra/postgres/rollback/044_company_loss_failed_build.down.sql (by hand, owner's approval).
ALTER TABLE company_loss_events DROP CONSTRAINT IF EXISTS company_loss_events_cause_known;
ALTER TABLE company_loss_events ADD CONSTRAINT company_loss_events_cause_known CHECK (
    cause IN ('metered_overrun', 'budget_capped_shortfall', 'unreconciled_unknown', 'failed_build_refunded'));
