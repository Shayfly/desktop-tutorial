-- Private previews (migration 032). Autonomous completion directive §4.
--
-- Real-server finding 2026-10-09: preview hostnames are published in
-- certificate-transparency logs (on-demand TLS), and internet scanners hit
-- them within minutes. An unguessable URL is not access control.
--
-- access_mode: PRIVATE (default; only holders of an owner token), SHARED
-- (owner tokens + share tokens the owner created), PUBLIC (anyone). Existing
-- rows become PRIVATE.
--
-- preview_access_tokens: random tokens, stored only as SHA-256; issued by the
-- API to the authenticated owner (short-lived) or as a share link; checked by
-- the preview router on the host; revocable; usage counted for audit.
-- preview_access_audit: issued / revoked / mode changes and refused requests
-- (aggregated per preview and minute), never the token itself.

ALTER TABLE project_previews ADD COLUMN IF NOT EXISTS access_mode TEXT NOT NULL DEFAULT 'PRIVATE'
    CHECK (access_mode IN ('PRIVATE', 'SHARED', 'PUBLIC'));

CREATE TABLE IF NOT EXISTS preview_access_tokens (
    token_hash   TEXT PRIMARY KEY,
    preview_id   TEXT NOT NULL REFERENCES project_previews(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN ('owner', 'share')),
    issued_to    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    uses         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_preview_access_tokens_preview ON preview_access_tokens (preview_id);

CREATE TABLE IF NOT EXISTS preview_access_audit (
    id         BIGSERIAL PRIMARY KEY,
    preview_id TEXT NOT NULL,
    at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event      TEXT NOT NULL CHECK (event IN ('issued', 'revoked', 'mode', 'denied')),
    detail     TEXT NOT NULL DEFAULT '' CHECK (length(detail) <= 300)
);

CREATE INDEX IF NOT EXISTS idx_preview_access_audit_preview ON preview_access_audit (preview_id, at);
