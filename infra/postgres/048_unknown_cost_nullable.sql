-- 048: an unknown cost is stored as unknown (NULL), never as 0. The owner, 2026-11-26 ~16:50 UTC: "לא ידועה במיגרציה".
-- (046 and 047 are taken on other branches: social login, rate limits.)
--   build_jobs.ai_cost                     NULL when a build had a model call whose price is missing (the known part
--                                          stays in evidence_json.economics_settlement.cost_record.llm_known_usd)
--   build_jobs.build_seconds               NULL for a build that never started
--   provider_usage_events.estimated_cost_usd  NULL for an image whose provider has no price (pricing_version keeps
--                                          its 'unpriced:' marker)
-- The defaults stay (0) for the writers that do not pass a value. DROP NOT NULL is idempotent: safe to run twice.
-- The CHECK (estimated_cost_usd >= 0) and CHECK (maximum_cost_usd >= estimated_cost_usd) pass for NULL.
-- Rollback: infra/postgres/rollback/048_unknown_cost_nullable.down.sql (by hand, the owner's approval).
ALTER TABLE build_jobs ALTER COLUMN ai_cost DROP NOT NULL;
ALTER TABLE build_jobs ALTER COLUMN build_seconds DROP NOT NULL;
ALTER TABLE provider_usage_events ALTER COLUMN estimated_cost_usd DROP NOT NULL;
