-- Additive only. Prepared for review; never applied to a live database by this change.
-- Watermarks serialize entitlement events per account. Event IDs survive worker
-- and API restarts. No card data, raw webhook payloads, or secret values are stored.
CREATE TABLE IF NOT EXISTS creator_billing_watermarks (
    account_id TEXT PRIMARY KEY,
    event_created BIGINT NOT NULL DEFAULT -1 CHECK (event_created >= -1),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority IN (0, 1)),
    source_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS creator_billing_events (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES creator_billing_watermarks(account_id),
    source_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_created BIGINT NOT NULL CHECK (event_created >= 0),
    priority INTEGER NOT NULL CHECK (priority IN (0, 1)),
    plan_code TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS creator_billing_events_account_created
    ON creator_billing_events(account_id, event_created);
CREATE INDEX IF NOT EXISTS creator_billing_events_source_order
    ON creator_billing_events(account_id, source_id, event_created DESC, priority DESC);
