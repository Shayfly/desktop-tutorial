-- M5 Task 9: durable submission journal for paid external media providers.
-- An INTENT row is written before a paid submit; the provider task id is
-- recorded right after. A crash between the two leaves an INTENT row, which
-- makes the adapter fail closed (or rely on provider-side idempotency) instead
-- of blindly paying for a duplicate job.

CREATE TABLE IF NOT EXISTS media_provider_submissions (
    idempotency_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('INTENT','SUBMITTED')),
    provider_task_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT media_provider_submissions_task CHECK ((state = 'SUBMITTED') = (provider_task_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_media_provider_submissions_intent
    ON media_provider_submissions(provider, created_at)
    WHERE state = 'INTENT';
