from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.truth_lock import (
    TruthDriftError, canonical_truth_snapshot, render_truth_files,
    write_truth_files, check_truth_files,
)


class MachineTruthLockTests(unittest.TestCase):
    def test_canonical_snapshot_has_complete_cross_registry_coverage(self):
        snapshot=canonical_truth_snapshot()
        self.assertEqual(snapshot['registry_report']['uncovered_capabilities'], [])
        self.assertEqual(snapshot['registry_report']['unknown_agent_skills'], [])
        self.assertEqual(snapshot['capability_count'], len(CapabilityRegistry().all()))
        self.assertGreater(snapshot['skill_count'], 80)
        self.assertGreaterEqual(snapshot['agent_count'], 26)
        self.assertEqual(len(snapshot['sha256']), 64)

    def test_generated_truth_files_are_deterministic_and_drift_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_truth_files(root)
            check_truth_files(root)
            (root/'CAPABILITY_MATRIX.md').write_text('drift\n')
            with self.assertRaises(TruthDriftError):
                check_truth_files(root)

    def test_rendered_registries_are_machine_readable_and_have_same_fingerprint(self):
        files=render_truth_files()
        machine=json.loads(files['M4_95_MACHINE_TRUTH.json'])
        skills=json.loads(files['MASTER_SKILLS_REGISTRY.json'])
        agents=json.loads(files['MASTER_AGENTS_REGISTRY.json'])
        self.assertEqual(machine['sha256'], skills['truth_sha256'])
        self.assertEqual(machine['sha256'], agents['truth_sha256'])
        self.assertIn('media.3d.mesh.generate', files['CAPABILITY_MATRIX.md'])


    def test_cost_and_mission_truth_rules_are_explicit(self):
        cost=Path('COST_MODEL.md').read_text()
        self.assertIn('UNKNOWN_NOT_APPROVED', cost)
        self.assertIn('UNKNOWN is never zero', cost)
        self.assertIn('estimate is never actual', cost)
        self.assertIn('actual_cost_usd', cost)
        self.assertIn('maximum_cost_usd', cost)
        mission=Path('PRODUCT_MISSION_AND_ACCEPTANCE.md').read_text().lower()
        for phrase in ('3d','multiplayer','agent','automation','voice','music','video'):
            self.assertIn(phrase, mission)
        self.assertIn('not_implemented', mission)
        self.assertIn('partial', mission)



if __name__=='__main__': unittest.main()
