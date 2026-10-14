-- Discovery brief and server-bound build approval (migration 030).
-- Master directive 2026-10-09 §4-5.
--
-- project_briefs: every change to the discovery answers is a new immutable
-- revision. Writers use compare-and-set on the revision number (the UNIQUE
-- constraint makes a lost race fail instead of overwriting).
--
-- build_approvals: "approve and start building" binds the user, project,
-- brief revision + fingerprint, build contract + fingerprint and the budget
-- quote (budget revision) for a limited time. A build consumes exactly one
-- ACTIVE approval; a newer brief revision or a different quote makes it stale.

CREATE TABLE IF NOT EXISTS project_briefs (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
    revision     INTEGER NOT NULL CHECK (revision > 0),
    account_id   TEXT NOT NULL REFERENCES creator_accounts(id),
    mode         TEXT NOT NULL CHECK (mode IN ('guided', 'recommend')),
    complete     BOOLEAN NOT NULL,
    brief_json   JSONB NOT NULL,
    fingerprint  TEXT NOT NULL,
    request_key  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, revision)
);
-- A retried submission (same idempotency key) returns the revision it made.
CREATE UNIQUE INDEX IF NOT EXISTS uq_project_briefs_request_key
    ON project_briefs(project_id, request_key) WHERE request_key IS NOT NULL;

CREATE OR REPLACE FUNCTION reject_project_brief_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'project briefs are immutable; write a new revision';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_project_briefs_immutable ON project_briefs;
CREATE TRIGGER trg_project_briefs_immutable
BEFORE UPDATE ON project_briefs
FOR EACH ROW EXECUTE FUNCTION reject_project_brief_mutation();

CREATE TABLE IF NOT EXISTS build_approvals (
    id                    TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
    account_id            TEXT NOT NULL REFERENCES creator_accounts(id),
    brief_id              TEXT NOT NULL REFERENCES project_briefs(id),
    brief_revision        INTEGER NOT NULL,
    brief_fingerprint     TEXT NOT NULL,
    build_contract_id     TEXT NOT NULL REFERENCES m5_build_contracts(id),
    contract_fingerprint  TEXT NOT NULL,
    budget_fingerprint    TEXT NOT NULL,
    status                TEXT NOT NULL CHECK (status IN ('ACTIVE', 'USED', 'INVALIDATED', 'EXPIRED')),
    expires_at            TIMESTAMPTZ NOT NULL,
    used_by_build_id      TEXT,
    invalidated_reason    TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT build_approvals_used CHECK ((status = 'USED') = (used_by_build_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_build_approvals_project ON build_approvals(project_id, created_at DESC);
