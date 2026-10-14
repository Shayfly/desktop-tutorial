-- Attempt Ledger counters (migration 028; founder decision 2026-10-07, section 9).
-- Per-attempt snapshot of the build's counters at the moment the attempt was
-- recorded, so every row is self-describing without re-aggregating the build:
--   retry_count       prior attempts of the same logical call (0 = first try)
--   repair_count      repair calls made in this build so far (incl. this one)
--   regenerate_count  code generations beyond the first in this build so far
--   escalation_count  escalated attempts in this build so far
--   fallback_count    attempts served by a non-first candidate so far
-- NULL means "not recorded" (rows written before this migration).

ALTER TABLE task_attempts
    ADD COLUMN IF NOT EXISTS retry_count      INTEGER CHECK (retry_count IS NULL OR retry_count >= 0),
    ADD COLUMN IF NOT EXISTS repair_count     INTEGER CHECK (repair_count IS NULL OR repair_count >= 0),
    ADD COLUMN IF NOT EXISTS regenerate_count INTEGER CHECK (regenerate_count IS NULL OR regenerate_count >= 0),
    ADD COLUMN IF NOT EXISTS escalation_count INTEGER CHECK (escalation_count IS NULL OR escalation_count >= 0),
    ADD COLUMN IF NOT EXISTS fallback_count   INTEGER CHECK (fallback_count IS NULL OR fallback_count >= 0);
