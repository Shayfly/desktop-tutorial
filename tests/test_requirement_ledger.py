import json
import unittest
from unittest.mock import patch
from pathlib import Path

from omni_prod.requirement_ledger import (
    RequirementLedger,
    RequirementStatus,
    load_requirement_ledger,
    validate_plan_task_coverage,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "REQUIREMENT_LEDGER.json"
M495_PLAN = ROOT / "docs/superpowers/plans/2026-10-04-m495-capability-foundation-v2-plan.md"
M5_PLAN = ROOT / "docs/superpowers/plans/2026-10-04-m5-production-vertical-slice.md"


class RequirementLedgerTests(unittest.TestCase):
    def test_ledger_loads_and_dependencies_are_valid(self):
        ledger = load_requirement_ledger(LEDGER)
        self.assertGreaterEqual(len(ledger.all()), 35)
        ledger.validate(ROOT)

    def test_m495_and_m5_plan_tasks_are_all_ledgered(self):
        ledger = load_requirement_ledger(LEDGER)
        self.assertEqual(validate_plan_task_coverage(M495_PLAN, "M4.95", ledger), ())
        self.assertEqual(validate_plan_task_coverage(M5_PLAN, "M5", ledger), ())

    def test_verified_records_require_named_code_tests_evidence_and_commit(self):
        ledger = load_requirement_ledger(LEDGER)
        verified = {
            RequirementStatus.VERIFIED_LOCAL,
            RequirementStatus.VERIFIED_EXTERNAL,
        }
        for record in ledger.all():
            if record.status not in verified:
                continue
            self.assertTrue(record.implementation_paths, record.requirement_id)
            self.assertTrue(record.test_ids, record.requirement_id)
            self.assertTrue(record.evidence_refs, record.requirement_id)
            self.assertTrue(record.commit_sha, record.requirement_id)
            self.assertTrue(record.last_verified_at, record.requirement_id)

    def test_verified_implementation_and_test_files_exist(self):
        ledger = load_requirement_ledger(LEDGER)
        for record in ledger.all():
            if record.status not in {RequirementStatus.VERIFIED_LOCAL, RequirementStatus.VERIFIED_EXTERNAL}:
                continue
            for rel in record.implementation_paths:
                self.assertTrue((ROOT / rel).exists(), f"{record.requirement_id}: missing {rel}")
            for test_id in record.test_ids:
                test_path = test_id.split("::", 1)[0]
                self.assertTrue((ROOT / test_path).exists(), f"{record.requirement_id}: missing {test_path}")

    def test_m5_truth_is_exactly_1_2_3_10_11_verified_today(self):
        ledger = load_requirement_ledger(LEDGER)
        verified = {
            int(r.requirement_id.split("T", 1)[1])
            for r in ledger.all()
            if r.milestone == "M5" and r.status is RequirementStatus.VERIFIED_LOCAL
        }
        self.assertEqual(verified, {1, 2, 3, 10, 11})

    def test_truth_lock_fails_when_requirement_ledger_check_fails(self):
        from omni_prod.truth_lock import TruthDriftError, check_truth_files
        with patch("omni_prod.truth_lock.run_requirement_check", side_effect=ValueError("missing M5-T02")):
            with self.assertRaisesRegex(TruthDriftError, "requirement-ledger"):
                check_truth_files(ROOT)

    def test_media_domain_pack_is_versioned_and_not_claimed_complete(self):
        ledger = load_requirement_ledger(LEDGER)
        record = ledger.get("MEDIA-CREATOR-STUDIO")
        self.assertEqual(record.status, RequirementStatus.PARTIAL)
        self.assertIn("docs/product/148AI_MEDIA_CREATOR_DOMAIN_REQUIREMENTS_2026-10-04.md", record.source_specs)


if __name__ == "__main__":
    unittest.main()
