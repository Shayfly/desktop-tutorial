-- Rollback of 042_live_core_tables. NOT discovered by the migration runner
-- (it reads infra/postgres/*.sql only, not subdirectories). Run by hand, inside one
-- transaction, only with the owner's approval: it DELETES every live_* row.
-- Touches nothing outside live_*; investor_app tables are not referenced.
BEGIN;
DROP INDEX IF EXISTS idx_live_artifacts_owner_project;
DROP INDEX IF EXISTS idx_live_build_events_build;
DROP INDEX IF EXISTS idx_live_builds_owner_project;
DROP INDEX IF EXISTS idx_live_versions_owner_project;
DROP INDEX IF EXISTS idx_live_versions_project;
DROP INDEX IF EXISTS idx_live_projects_owner;
DROP TABLE IF EXISTS live_build_events;
DROP TABLE IF EXISTS live_builds;
DROP TABLE IF EXISTS live_versions;
DROP TABLE IF EXISTS live_artifacts;
DROP TABLE IF EXISTS live_projects;
DROP TABLE IF EXISTS live_sessions;
DROP TABLE IF EXISTS live_users;
DELETE FROM schema_migrations WHERE version = 42;
COMMIT;
