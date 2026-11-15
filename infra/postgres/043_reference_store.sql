-- 043: the shared reference store (Michael 2026-11-15, "מאגר דוגמאות משותף", decisions 1-7).
-- One store, two consumers: A2 (Gemini) writes, A1 reads. reference_cards EXTENDS the card of
-- docs/spec/reference_card.schema.json (#369) with the store's columns (decision 1: no second table of references).
-- Additive only: CREATE ... IF NOT EXISTS, nothing dropped, altered or rewritten; no existing table is referenced.
-- Rollback: infra/postgres/rollback/043_reference_store.down.sql (not run by the runner; by hand, owner's approval).
CREATE TABLE IF NOT EXISTS reference_cards (
    card_id TEXT PRIMARY KEY CHECK (card_id ~ '^ref_[0-9A-HJKMNP-TV-Z]{26}$'),
    category TEXT NOT NULL CHECK (category ~ '^[a-z][a-z0-9_]{1,40}$'),
    adjacency_rank SMALLINT NOT NULL DEFAULT 0 CHECK (adjacency_rank BETWEEN 0 AND 2),
    source_url TEXT NOT NULL CHECK (source_url ~ '^https://' AND length(source_url) <= 300),
    fetched_at TIMESTAMPTZ NOT NULL,
    extraction_version TEXT NOT NULL CHECK (extraction_version ~ '^x[0-9]+(\.[0-9]+)*$'),
    status TEXT NOT NULL CHECK (status IN ('fresh', 'stale', 'weak')),
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'needs_human')),
    reason_code TEXT NULL,
    decided_by TEXT NOT NULL CHECK (decided_by IN ('scout', 'michael', 'shai')),
    card JSONB NOT NULL,
    card_sha256 CHAR(64) NOT NULL CHECK (card_sha256 ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ NULL,
    retired_by TEXT NULL CHECK (retired_by IN ('shai')),
    CHECK (decision <> 'approved' OR decided_by IN ('michael', 'shai')),
    CHECK (decision <> 'rejected' OR reason_code IS NOT NULL),
    CHECK ((retired_at IS NULL) = (retired_by IS NULL)),
    UNIQUE (category, source_url, extraction_version)
);
CREATE TABLE IF NOT EXISTS reference_card_components (
    card_id TEXT NOT NULL REFERENCES reference_cards(card_id),
    component_key TEXT NOT NULL CHECK (component_key ~ '^[a-z][a-z0-9_]{1,40}$'),
    section_position SMALLINT NOT NULL CHECK (section_position BETWEEN 0 AND 30),
    prevalence_class TEXT NULL CHECK (prevalence_class IN ('default', 'option', 'rare')),
    PRIMARY KEY (card_id, component_key, section_position)
);
CREATE TABLE IF NOT EXISTS category_adjacency (
    category TEXT NOT NULL CHECK (category ~ '^[a-z][a-z0-9_]{1,40}$'),
    adjacent_category TEXT NOT NULL CHECK (adjacent_category ~ '^[a-z][a-z0-9_]{1,40}$'),
    rank SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 20),
    cross_vertical BOOLEAN NOT NULL DEFAULT false,
    CHECK (category <> adjacent_category),
    PRIMARY KEY (category, adjacent_category),
    UNIQUE (category, rank)
);
CREATE TABLE IF NOT EXISTS reference_offers (
    id BIGSERIAL PRIMARY KEY,
    brief_id TEXT NOT NULL,
    category TEXT NOT NULL,
    card_id TEXT NULL REFERENCES reference_cards(card_id),
    component_key TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS offer_rejections (
    id BIGSERIAL PRIMARY KEY,
    brief_id TEXT NOT NULL,
    category TEXT NOT NULL,
    component_key TEXT NULL,
    signal TEXT NOT NULL CHECK (signal IN ('disliked', 'asked_another')),
    scope TEXT NULL CHECK (scope IN ('layer', 'domain', 'all')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS offer_alerts (
    id BIGSERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    rejections INTEGER NOT NULL CHECK (rejections >= 0),
    offers INTEGER NOT NULL CHECK (offers >= 0),
    fired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS collect_queue (
    id BIGSERIAL PRIMARY KEY,
    category TEXT NOT NULL CHECK (category ~ '^[a-z][a-z0-9_]{1,40}$'),
    reason TEXT NOT NULL CHECK (reason IN ('domain_rejected', 'empty_category', 'stale_category', 'weak_category')),
    brief_id TEXT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_reference_cards_category ON reference_cards (category, decision, status);
CREATE INDEX IF NOT EXISTS idx_reference_offers_category ON reference_offers (category, created_at);
CREATE INDEX IF NOT EXISTS idx_offer_rejections_category ON offer_rejections (category, created_at);
CREATE INDEX IF NOT EXISTS idx_offer_rejections_brief ON offer_rejections (brief_id);
CREATE INDEX IF NOT EXISTS idx_collect_queue_open ON collect_queue (category) WHERE resolved_at IS NULL;
