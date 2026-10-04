import unittest
from pathlib import Path
from datetime import datetime, timezone

from omni_prod.account_tenant import ProjectRecord
from omni_prod.project_lifecycle import (
    MemoryProjectLifecycleRepository,
    ProjectLifecycleService,
    ProjectLifecycleError,
)


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryProjectLifecycleRepository()
        self.service = ProjectLifecycleService(self.repo, now_fn=lambda: datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc))
        self.owner = "usr_owner"
        self.other = "usr_other"
        self.project = self.service.create_project(owner_id=self.owner, title="Travel CRM")

    def test_rename_search_archive_unarchive_and_default_list_visibility(self):
        renamed = self.service.rename_project(owner_id=self.owner, project_id=self.project.id, title="Travel Operations CRM")
        self.assertEqual(renamed.title, "Travel Operations CRM")
        self.assertEqual([p.id for p in self.service.search_projects(owner_id=self.owner, query="operations")], [self.project.id])

        archived = self.service.archive_project(owner_id=self.owner, project_id=self.project.id)
        self.assertEqual(archived.state, "ARCHIVED")
        self.assertEqual(self.service.list_projects(owner_id=self.owner), ())
        self.assertEqual([p.id for p in self.service.search_projects(owner_id=self.owner, query="travel", include_archived=True)], [self.project.id])

        active = self.service.unarchive_project(owner_id=self.owner, project_id=self.project.id)
        self.assertEqual(active.state, "ACTIVE")
        self.assertEqual([p.id for p in self.service.list_projects(owner_id=self.owner)], [self.project.id])

    def test_delete_is_tombstone_idempotent_and_history_row_remains(self):
        first = self.service.delete_project(owner_id=self.owner, project_id=self.project.id, reason="user_request")
        second = self.service.delete_project(owner_id=self.owner, project_id=self.project.id, reason="duplicate_request")
        self.assertEqual(first.state, "DELETED")
        self.assertEqual(second.deleted_at, first.deleted_at)
        self.assertEqual(second.retention_until, first.retention_until)
        self.assertEqual(self.service.list_projects(owner_id=self.owner), ())
        state = self.service.project_state(owner_id=self.owner, project_id=self.project.id)
        self.assertEqual(state.state, "DELETED")
        self.assertIsNotNone(self.repo.raw(self.project.id), "soft delete must retain tombstone row")

    def test_owner_scope_is_enforced_for_every_lifecycle_operation(self):
        calls = (
            lambda: self.service.rename_project(owner_id=self.other, project_id=self.project.id, title="stolen"),
            lambda: self.service.archive_project(owner_id=self.other, project_id=self.project.id),
            lambda: self.service.unarchive_project(owner_id=self.other, project_id=self.project.id),
            lambda: self.service.delete_project(owner_id=self.other, project_id=self.project.id),
            lambda: self.service.project_state(owner_id=self.other, project_id=self.project.id),
            lambda: self.service.require_project(owner_id=self.other, project_id=self.project.id),
        )
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(PermissionError):
                    call()

    def test_deleted_project_cannot_be_renamed_archived_or_required(self):
        self.service.delete_project(owner_id=self.owner, project_id=self.project.id)
        for call in (
            lambda: self.service.rename_project(owner_id=self.owner, project_id=self.project.id, title="again"),
            lambda: self.service.archive_project(owner_id=self.owner, project_id=self.project.id),
            lambda: self.service.require_project(owner_id=self.owner, project_id=self.project.id),
        ):
            with self.assertRaises(ProjectLifecycleError):
                call()

    def test_project_id_reuse_is_rejected_even_after_delete(self):
        self.service.delete_project(owner_id=self.owner, project_id=self.project.id)
        duplicate = ProjectRecord(
            self.project.id,
            self.owner,
            "new object with reused id",
            self.project.created_at,
            self.project.updated_at,
        )
        with self.assertRaisesRegex(ValueError, "project id already exists"):
            self.repo.create(duplicate)


class ProjectLifecycleSchemaContractTests(unittest.TestCase):
    def test_migration_is_tombstone_only_and_never_hard_deletes_projects(self):
        migration = (Path(__file__).resolve().parents[1] / "infra/postgres/019_project_lifecycle.sql").read_text().lower()
        for column in ("archived_at", "deleted_at", "retention_until", "tombstone_reason"):
            self.assertIn(column, migration)
        self.assertNotIn("delete from creator_projects", migration)
        self.assertNotIn("on delete cascade", migration)


if __name__ == "__main__":
    unittest.main()
