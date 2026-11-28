-- Rollback of 050_media_infra. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval (CLAUDE.md section 5: backup branch first, then a
-- dry count of both tables). It DELETES the rights records and the render queue: asset_rights is EVIDENCE of who made
-- an asset and on what terms. Export it first; roll back the code that reads the tables (omni_prod/asset_rights.py,
-- omni_prod/media_queue.py) BEFORE this runs.
BEGIN;
DROP INDEX IF EXISTS media_render_jobs_waiting;
DROP TABLE IF EXISTS media_render_jobs;
DROP TRIGGER IF EXISTS asset_rights_append_only ON asset_rights;
DROP FUNCTION IF EXISTS asset_rights_are_evidence();
DROP INDEX IF EXISTS asset_rights_by_terms_date;
DROP TABLE IF EXISTS asset_rights;
DELETE FROM schema_migrations WHERE version = 50;
COMMIT;
