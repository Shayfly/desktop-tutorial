-- Conversation attachments: images and annotated screenshots (migration 038).
-- Additive only; rollback = DROP TABLE conversation_attachments (no other table
-- references it; the stored objects live under attachments/<account>/<project>/).
--
-- One row per uploaded image. The bytes are in object storage (the same S3/R2
-- bucket as project artifacts), never in this table. Access is owner-only:
-- every read filters on BOTH project_id and account_id. A deleted attachment
-- keeps its row (audit) with deleted_at set; its object is removed.
-- analysis_state is honest: NOT_ANALYZED until a vision-capable route is
-- authorized and actually runs (no paid model is called by this migration's code).

CREATE TABLE IF NOT EXISTS conversation_attachments (
    id              TEXT PRIMARY KEY CHECK (id ~ '^att_[0-9a-f]{32}$'),
    project_id      TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('image', 'screenshot')),
    mime            TEXT NOT NULL CHECK (mime IN ('image/png', 'image/jpeg', 'image/webp')),
    size_bytes      INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 3145728),
    width           INTEGER NOT NULL CHECK (width > 0 AND width <= 8000),
    height          INTEGER NOT NULL CHECK (height > 0 AND height <= 8000),
    sha256          TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    storage_key     TEXT NOT NULL,
    annotation      JSONB NOT NULL DEFAULT '{}'::jsonb,
    analysis_state  TEXT NOT NULL DEFAULT 'NOT_ANALYZED'
                    CHECK (analysis_state IN ('NOT_ANALYZED', 'PENDING', 'ANALYZED', 'FAILED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS conversation_attachments_project
    ON conversation_attachments (project_id, account_id, created_at)
    WHERE deleted_at IS NULL;
