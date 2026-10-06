-- Internal entitlements and reservation funding source (migration 029).
-- Founder decision 2026-10-07 (#24): internal QA funding is an explicit,
-- audited entitlement bound to an account id and an environment scope, never
-- an implicit email match, and its budget is separate from the customer plan.
--
-- Only INTERNAL_QA in the staging scope exists. Adding another entitlement or
-- scope (for example production) is a deliberate schema change, not a row.
-- Revocation keeps the row (audit trail); at most one active grant per
-- (account, entitlement, environment).

CREATE TABLE IF NOT EXISTS internal_entitlements (
    id              TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES creator_accounts(id),
    entitlement     TEXT NOT NULL CHECK (entitlement IN ('INTERNAL_QA')),
    environment     TEXT NOT NULL CHECK (environment IN ('staging')),
    reason          TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    granted_by      TEXT NOT NULL CHECK (length(trim(granted_by)) > 0),
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    revoked_by      TEXT,
    revoke_reason   TEXT,
    CONSTRAINT internal_entitlements_revocation CHECK ((revoked_at IS NULL) = (revoked_by IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_internal_entitlements_active
    ON internal_entitlements(account_id, entitlement, environment)
    WHERE revoked_at IS NULL;

-- Which budget funded a reservation. Customer-plan reservations move the
-- account's plan counters; internal QA reservations never do, and only they
-- count against the internal QA caps.
ALTER TABLE credit_reservations
    ADD COLUMN IF NOT EXISTS funding_source TEXT NOT NULL DEFAULT 'customer_plan'
        CHECK (funding_source IN ('customer_plan', 'internal_qa'));

CREATE INDEX IF NOT EXISTS idx_credit_reservations_internal_qa
    ON credit_reservations(created_at)
    WHERE funding_source = 'internal_qa';
