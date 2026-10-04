-- 019_project_lifecycle.sql
-- M5 Task 3: archive/delete are metadata state transitions. Project rows and
-- downstream versions/build/evidence are deliberately not hard-deleted here.

ALTER TABLE creator_projects ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE creator_projects ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE creator_projects ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ;
ALTER TABLE creator_projects ADD COLUMN IF NOT EXISTS tombstone_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_creator_projects_owner_active
    ON creator_projects(owner_id, updated_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_creator_projects_owner_archived
    ON creator_projects(owner_id, updated_at DESC)
    WHERE deleted_at IS NULL AND archived_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_creator_projects_retention
    ON creator_projects(retention_until)
    WHERE deleted_at IS NOT NULL;
