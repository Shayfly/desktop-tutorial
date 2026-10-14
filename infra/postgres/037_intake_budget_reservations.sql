-- Intake model budget reservations (Issue #12). Additive only.
--
-- Lifecycle of one paid intake model invocation:
--   QUOTE (code) -> RESERVE -> CLAIM -> EXECUTE -> METER/SETTLE -> RECONCILE
-- * RESERVE inserts the reservation, its budget scopes and the outbox row in
--   ONE transaction, after locking the scope anchor rows in sorted order and
--   checking every cap against settled + outstanding amounts.
-- * The worker CLAIMs (RESERVED -> CLAIMED, lease) and marks EXECUTING in a
--   committed write BEFORE contacting the provider; no transaction is open
--   during the provider call.
-- * SETTLE records the cost state: CONFIRMED / CONFIRMED_ZERO / ESTIMATED with
--   actual_usd, or UNKNOWN with actual_usd NULL -- an UNKNOWN reservation keeps
--   holding its full quoted amount until RECONCILE resolves it with evidence.
-- * An expired EXECUTING lease becomes UNKNOWN (never released, never
--   replayed). Only RESERVED/CLAIMED (provider certainly not contacted) can be
--   RELEASED automatically.
-- Amount counted against every scope of a reservation:
--   RELEASED -> 0; SETTLED -> actual_usd; anything else (incl. UNKNOWN) -> quoted_usd.
-- The rolling-24 h ("daily") scope counts settled reservations by reserved_at
-- within 24 h, and every unsettled reservation regardless of age.

-- Lock anchors: one row per budget scope. Financial transactions lock these
-- rows (never an aggregate) in ascending `scope` order.
CREATE TABLE IF NOT EXISTS intake_budget_scopes (
    scope       TEXT PRIMARY KEY CHECK (length(scope) <= 300),
    kind        TEXT NOT NULL CHECK (kind IN ('project', 'daily', 'campaign')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS intake_reservations (
    id                  TEXT PRIMARY KEY,
    idempotency_key     TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) <= 300),
    account_id          TEXT NOT NULL,
    project_id          TEXT NOT NULL,
    lane                TEXT NOT NULL CHECK (lane IN ('production', 'campaign')),
    campaign_id         TEXT,
    quoted_usd          NUMERIC(18, 8) NOT NULL CHECK (quoted_usd > 0),
    quote               JSONB NOT NULL,          -- envelope: routes, token bounds, prices, versions, caps snapshot
    state               TEXT NOT NULL CHECK (state IN
                            ('RESERVED', 'CLAIMED', 'EXECUTING', 'SETTLED', 'UNKNOWN', 'RELEASED')),
    cost_state          TEXT CHECK (cost_state IN ('CONFIRMED', 'CONFIRMED_ZERO', 'ESTIMATED', 'UNKNOWN')),
    actual_usd          NUMERIC(18, 8) CHECK (actual_usd IS NULL OR actual_usd >= 0),
    failure_reason      TEXT,
    claim_token         TEXT,
    claimed_by          TEXT,
    lease_expires_at    TIMESTAMPTZ,
    provider            TEXT,
    model               TEXT,
    provider_request_id TEXT,
    result              JSONB,                   -- validated-later raw interpretation (no secrets)
    reserved_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_at          TIMESTAMPTZ,
    executing_at        TIMESTAMPTZ,
    settled_at          TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT intake_res_lane_campaign CHECK ((lane = 'campaign') = (campaign_id IS NOT NULL)),
    CONSTRAINT intake_res_settled_cost CHECK (
        (state = 'SETTLED' AND cost_state IN ('CONFIRMED', 'CONFIRMED_ZERO', 'ESTIMATED') AND actual_usd IS NOT NULL)
        OR (state = 'UNKNOWN' AND cost_state = 'UNKNOWN' AND actual_usd IS NULL AND failure_reason IS NOT NULL)
        OR (state IN ('RESERVED', 'CLAIMED', 'EXECUTING', 'RELEASED') AND cost_state IS NULL AND actual_usd IS NULL)),
    CONSTRAINT intake_res_zero CHECK (cost_state <> 'CONFIRMED_ZERO' OR actual_usd = 0),
    CONSTRAINT intake_res_claim CHECK (state NOT IN ('CLAIMED', 'EXECUTING') OR
                                       (claim_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_intake_res_project ON intake_reservations(account_id, project_id, reserved_at DESC);
CREATE INDEX IF NOT EXISTS idx_intake_res_open ON intake_reservations(state, lease_expires_at)
    WHERE state IN ('RESERVED', 'CLAIMED', 'EXECUTING', 'UNKNOWN');

CREATE TABLE IF NOT EXISTS intake_reservation_scopes (
    reservation_id  TEXT NOT NULL REFERENCES intake_reservations(id),
    scope           TEXT NOT NULL REFERENCES intake_budget_scopes(scope),
    cap_usd         NUMERIC(18, 8) NOT NULL CHECK (cap_usd >= 0),   -- cap in force when reserved (audit)
    PRIMARY KEY (reservation_id, scope)
);
CREATE INDEX IF NOT EXISTS idx_intake_res_scopes_scope ON intake_reservation_scopes(scope, reservation_id);

-- Transactional outbox: written in the RESERVE transaction; relayed to RQ with
-- job id = reservation id (duplicate delivery is harmless: CLAIM is atomic).
CREATE TABLE IF NOT EXISTS intake_outbox (
    id              BIGSERIAL PRIMARY KEY,
    reservation_id  TEXT NOT NULL UNIQUE REFERENCES intake_reservations(id),
    payload         JSONB NOT NULL,
    enqueued_at     TIMESTAMPTZ,
    deliveries      INTEGER NOT NULL DEFAULT 0 CHECK (deliveries >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intake_outbox_pending ON intake_outbox(id) WHERE enqueued_at IS NULL;

-- Append-only audit of every state change.
CREATE TABLE IF NOT EXISTS intake_reservation_events (
    id              BIGSERIAL PRIMARY KEY,
    reservation_id  TEXT NOT NULL REFERENCES intake_reservations(id),
    from_state      TEXT,
    to_state        TEXT NOT NULL,
    detail          JSONB NOT NULL DEFAULT '{}'::jsonb,
    at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intake_res_events ON intake_reservation_events(reservation_id, id);

-- Conversation messages may now carry an UNKNOWN cost (NULL) and point at
-- their reservation. Existing rows keep their values.
ALTER TABLE intake_messages ADD COLUMN IF NOT EXISTS reservation_id TEXT;
ALTER TABLE intake_messages ADD COLUMN IF NOT EXISTS cost_state TEXT;
ALTER TABLE intake_messages ALTER COLUMN cost_usd DROP NOT NULL;
