-- 045: the frozen reference corpus (the owner, 2026-11-17; DECISIONS 2-4): 32 categories x 5 Israeli business sites,
-- 20% held out. Read by the calibration of the gates; never written by a build.
-- Never overwritten: a row is inserted once (UNIQUE url -- a second collection run cannot duplicate a page) and its
-- captured content is never updated (the trigger below refuses an UPDATE of url, category, city, fetched_at or
-- html_sha256 once set).
-- Acceptance at insert (decided 2026-11-17): Hebrew on the page AND an Israeli phone or an Israeli address; at least 3
-- pages on the site; loads in under 5 s; not a template builder (no Wix); not a chain of more than 10 branches.
-- A migration: runs with the owner's approval (2026-11-17, "decide everything yourself"; CLAUDE.md section 5).
-- Rollback: infra/postgres/rollback/045_corpus_pages.down.sql.
CREATE TABLE IF NOT EXISTS corpus_pages (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    category TEXT NOT NULL,
    city TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    html_path TEXT,
    html_sha256 TEXT,
    shot_390 TEXT,
    shot_1440 TEXT,
    holdout BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT corpus_pages_url_unique UNIQUE (url),
    CONSTRAINT corpus_pages_url_https CHECK (url ~ '^https?://')
);
CREATE INDEX IF NOT EXISTS corpus_pages_category ON corpus_pages (category, holdout);

CREATE OR REPLACE FUNCTION corpus_pages_never_overwritten() RETURNS trigger AS $$
BEGIN
    IF NEW.url <> OLD.url OR NEW.category <> OLD.category OR NEW.city <> OLD.city OR NEW.fetched_at <> OLD.fetched_at
       OR (OLD.html_sha256 IS NOT NULL AND NEW.html_sha256 IS DISTINCT FROM OLD.html_sha256) THEN
        RAISE EXCEPTION 'corpus_pages % is frozen: its captured content is never overwritten', OLD.url;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS corpus_pages_frozen ON corpus_pages;
CREATE TRIGGER corpus_pages_frozen BEFORE UPDATE ON corpus_pages FOR EACH ROW EXECUTE FUNCTION corpus_pages_never_overwritten();
