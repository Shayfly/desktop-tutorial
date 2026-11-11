-- PROBE ONLY (Michael 2026-11-11): proves that deployment-verify applies a PR's OWN migration to its preview
-- branch before verifying. This PR is never merged; its preview branch is deleted when it closes.
CREATE TABLE IF NOT EXISTS preview_migration_probe (id INTEGER PRIMARY KEY, note TEXT NOT NULL);
INSERT INTO preview_migration_probe (id, note) VALUES (1, 'applied by preview_db_prepare') ON CONFLICT DO NOTHING;
