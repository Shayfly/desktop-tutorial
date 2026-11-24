-- Rollback of 045 (by hand, the owner's approval; CLAUDE.md section 5: backup branch first).
DROP TRIGGER IF EXISTS corpus_pages_frozen ON corpus_pages;
DROP FUNCTION IF EXISTS corpus_pages_never_overwritten();
DROP TABLE IF EXISTS corpus_pages;
