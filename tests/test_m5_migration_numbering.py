"""M5 remediation: migration numbers are unique and never collide with numbers
the M5 plan reserves for not-yet-built tasks."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from omni_prod.migrations import discover_migrations

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-10-04-m5-production-vertical-slice.md"


class MigrationNumberingTests(unittest.TestCase):
    def test_no_duplicate_versions(self):
        migrations = discover_migrations(ROOT / "infra/postgres")  # raises on duplicates
        versions = [m.version for m in migrations]
        self.assertEqual(len(versions), len(set(versions)))

    def test_media_journal_is_026(self):
        names = {m.version: m.name for m in discover_migrations(ROOT / "infra/postgres")}
        self.assertEqual(names.get(26), "media_provider_submissions")
        self.assertNotIn(22, names, "022 is reserved for Task 12 production deployments")

    def test_plan_reserved_numbers_are_not_taken_by_other_files(self):
        reserved = {}
        for number, name in re.findall(r"infra/postgres/(\d{3})_([a-z0-9_]+)\.sql", PLAN.read_text(encoding="utf-8")):
            reserved[int(number)] = name
        existing = {m.version: m.name for m in discover_migrations(ROOT / "infra/postgres")}
        for number, name in reserved.items():
            if number in existing:
                self.assertEqual(existing[number], name, f"migration {number:03d} collides with the M5 plan")

    def test_no_code_or_test_references_old_number(self):
        for path in list((ROOT / "omni_prod").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
            if path.name == Path(__file__).name:
                continue
            self.assertNotIn("022_media_provider", path.read_text(encoding="utf-8", errors="ignore"), str(path))


if __name__ == "__main__":
    unittest.main()
