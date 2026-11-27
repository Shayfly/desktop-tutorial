-- 049: direction sketches (S6.3; the owner, 2026-11-26: "the first sketch in each project is on us, up to $0.10; further
-- sketches come out of the customer's balance"; 1א 2א 3א 4א, inbox/003). One row per sketch shown to a customer: what it
-- was made from (brief revision and fingerprint), the two fingerprints that decide when a new one is offered, who paid
-- for its words, the model call that wrote them (a pointer to intake_reservations, never an amount) and the three
-- timestamps S5.2 measures. The page itself is not stored: it is rendered again from the brief by the same functions.
-- No amount lives here. The money of a model call is in intake_reservations / intake_reservation_events (037); the
-- credits of a further sketch are in credit_reservations (013), keyed by the sketch id.
-- A migration: runs with the owner's approval only (CLAUDE.md section 5: backup branch, dry count, one
-- transaction, separate verification). It is additive (one table, three indexes) and nothing reads it before the code
-- that ships with it; the release that carries omni_prod/direction_sketch/store.py needs it applied first.
-- Rollback: infra/postgres/rollback/049_direction_sketches.down.sql.
CREATE TABLE IF NOT EXISTS direction_sketches (
    id                TEXT        PRIMARY KEY,
    project_id        TEXT        NOT NULL,
    account_id        TEXT        NOT NULL,
    brief_revision    INTEGER     NOT NULL,
    brief_fingerprint TEXT        NOT NULL,
    direction_fp      TEXT        NOT NULL,
    copy_fp           TEXT        NOT NULL,
    seq               INTEGER     NOT NULL DEFAULT 0,
    funding           TEXT        NOT NULL,
    copy_state        TEXT        NOT NULL,
    copy_reason       TEXT,
    copy              JSONB,
    copy_from         TEXT,
    reservation_id    TEXT,
    credits           INTEGER     NOT NULL DEFAULT 0,
    record            JSONB       NOT NULL,
    offered_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    copy_ready_at     TIMESTAMPTZ,
    CONSTRAINT direction_sketches_id CHECK (id ~ '^skt_[0-9a-f]{24}$'),
    CONSTRAINT direction_sketches_funding CHECK (funding IN ('none', 'company_first', 'owner', 'customer')),
    CONSTRAINT direction_sketches_copy_state CHECK (copy_state IN ('none', 'pending', 'written', 'failed')),
    CONSTRAINT direction_sketches_credits CHECK (credits >= 0 AND (credits = 0 OR funding = 'customer')),
    CONSTRAINT direction_sketches_written CHECK ((copy_state = 'written') = (copy IS NOT NULL OR copy_from IS NOT NULL)),
    CONSTRAINT direction_sketches_idempotent UNIQUE (project_id, direction_fp, copy_fp, seq)
);
-- One free sketch per project: two tabs cannot both take it, and a second sketch of a project cannot be free. A failed
-- call leaves the predicate (copy_state 'failed'), so the slot is free again; the attempts are bounded in code.
CREATE UNIQUE INDEX IF NOT EXISTS direction_sketches_one_free ON direction_sketches (project_id)
    WHERE funding = 'company_first' AND copy_state IN ('pending', 'written');
CREATE INDEX IF NOT EXISTS direction_sketches_project_time ON direction_sketches (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS direction_sketches_reservation ON direction_sketches (reservation_id) WHERE reservation_id IS NOT NULL;
