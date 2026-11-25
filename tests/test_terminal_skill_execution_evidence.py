"""Keep completed QA probe counts in the worker's terminal build evidence."""

import unittest
from unittest.mock import patch

from omni_prod import product_review
from omni_prod.build_control import BuildCancelled
from omni_prod.build_state import BuildStatus
from tests.test_gate_mutations_20261110 import GOOD_PAGE, REQUEST
from tests.test_m3_preview_logic import BuildHarness
from tests.test_skills_runtime_and_review import _Inner, _spec


class TerminalSkillEvidence(unittest.TestCase):
    def harness(self):
        harness = BuildHarness()
        harness.jobs.request['prompt'] = REQUEST
        review = product_review.ProductReviewExecutor(_Inner(), max_reviews=6)
        harness.engine.executor = review
        return harness, review

    def assert_recorded_rounds(self, harness, review, expected):
        evidence = harness.final['evidence_json']
        self.assertNotIn('product_review', evidence)
        self.assertEqual(evidence['billing'], 'released')
        rounds = evidence['product_review_skill_execution']
        self.assertEqual([item['round'] for item in rounds], expected)
        self.assertEqual(rounds, [{'round': r['round'], 'skill_execution': r['skill_execution']}
                                  for r in review.reviews])
        self.assertTrue(all(r['skill_execution'] for r in rounds))
        harness.workspace.commit.assert_not_called()

    def test_gate_escalation_preserves_the_three_completed_rounds(self):
        harness, review = self.harness()
        repository = {'index.html': GOOD_PAGE.replace(' dir="rtl"', '')}

        def repeat_quarantine(_prompt):
            def history(probe):
                return 'bld_fixture' if probe == '_rtl_for_hebrew' else None

            with patch.object(product_review, '_QUARANTINE_HISTORY', history):
                for _ in range(3):
                    review.execute(repository=repository, spec=_spec())
            self.fail('the third identical review must escalate')

        harness.engine.build.side_effect = repeat_quarantine
        self.assertEqual(harness.run(), 'cancelled')
        self.assertEqual(harness.final['target'], BuildStatus.CANCELLED)
        self.assertEqual(harness.final['error_code'], 'gate_escalation')
        self.assert_recorded_rounds(harness, review, [1, 2, 3])
        self.assertGreater(len(review.reviews[-1]['findings']), 0)
        checks = [check for skill in review.reviews[-1]['skill_execution'] for check in skill['checks']]
        probe = next(check for check in checks if check['probe'] == '_rtl_for_hebrew')
        self.assertEqual((probe['status'], probe['findings'], probe['blocking']), ('FINDINGS', 1, 1))

    def test_failure_after_review_preserves_only_the_completed_round_counts(self):
        harness, review = self.harness()

        def fail_after_review(_prompt):
            review.execute(repository={'index.html': GOOD_PAGE}, spec=_spec())
            raise RuntimeError('synthetic failure after QA')

        harness.engine.build.side_effect = fail_after_review
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure after QA'):
            harness.run()
        self.assertEqual(harness.final['target'], BuildStatus.FAILED)
        self.assert_recorded_rounds(harness, review, [1])

    def test_cancellation_before_review_has_no_skill_execution_claim(self):
        harness, review = self.harness()
        harness.engine.build.side_effect = BuildCancelled('synthetic stop before QA')
        self.assertEqual(harness.run(), 'cancelled')
        self.assertEqual(review.reviews, [])
        self.assertNotIn('product_review_skill_execution', harness.final['evidence_json'])
