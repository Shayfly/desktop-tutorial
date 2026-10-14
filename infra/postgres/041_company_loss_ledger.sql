BEGIN;

CREATE TABLE IF NOT EXISTS company_loss_events (
    id              BIGSERIAL    PRIMARY KEY,
    occurred_at     timestamptz  NOT NULL DEFAULT now(),
    source          text         NOT NULL,
    idempotency_key text         NOT NULL,
    build_id        text,
    reservation_id  text,
    account_id      text,
    project_id      text,
    lane            text,
    provider        text,
    model           text,
    quoted_usd      numeric(18,8) NOT NULL,
    actual_usd      numeric(18,8) NOT NULL,
    overrun_usd     numeric(18,8) NOT NULL,
    cause           text         NOT NULL,
    evidence        jsonb        NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT company_loss_events_overrun_positive CHECK (overrun_usd > 0),
    CONSTRAINT company_loss_events_cause_known CHECK (
        cause IN ('metered_overrun', 'budget_capped_shortfall', 'unreconciled_unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS company_loss_events_identity
    ON company_loss_events (source, idempotency_key);
CREATE INDEX IF NOT EXISTS company_loss_events_occurred_at
    ON company_loss_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS company_loss_events_build_id
    ON company_loss_events (build_id) WHERE build_id IS NOT NULL;

COMMIT;
