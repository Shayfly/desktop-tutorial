"""Failure taxonomy + first_pass_yield (founder decision 2026-10-19: the business metric)."""
import unittest

from omni_prod.autonomous_core import AcceptanceFailure as F
from omni_prod.failure_taxonomy import failure_type, first_pass_yield, layer_of, records

try:   # the engine-level checks drive the real chain (needs fastapi, as in CI)
    from tests.test_verification_group import PostBuildChecksReachTheRepairerTogether as _Chain
except ImportError:  # pragma: no cover
    _Chain = None


class TaxonomyRecordTests(unittest.TestCase):
    def test_layer_and_type_are_stable_keys_without_product_data(self):
        self.assertEqual(layer_of('BROWSER'), 'browser')
        self.assertEqual(layer_of('A3'), 'sandbox')
        self.assertEqual(failure_type("the product misbehaves in a real browser: form 'addMatchForm': no request"),
                         'the_product_misbehaves_in_a_real_browser')
        self.assertEqual(failure_type('consistency (syntax): test_app.py:142 Python syntax error'), 'consistency_(syntax)')

    def test_records_mark_what_the_next_round_repaired(self):
        rows = records([(0, [F('CONSISTENCY', 'consistency (syntax): x')]),
                        (1, [F('BEHAVIOR', 'behavioural acceptance failed: 1'), F('BROWSER', 'the product misbehaves: y')]),
                        (2, [F('BROWSER', 'the product misbehaves: z')])])
        got = [(r['layer'], r['round_index'], r['was_repaired'], r['chain_depth']) for r in rows]
        self.assertEqual(got, [('consistency', 0, True, 1), ('behaviour', 1, True, 5), ('browser', 1, False, 6),
                               ('browser', 2, False, 6)])
        self.assertEqual(set(rows[0]), {'layer', 'failure_type', 'round_index', 'was_repaired', 'chain_depth'})

    def test_the_summary_line_is_not_a_failure_of_its_own(self):
        self.assertEqual(records([(0, [F('ALSO_FAILING', 'also failing in this round: BROWSER: x')])]), [])

    def test_first_pass_yield(self):
        self.assertIsNone(first_pass_yield([]))
        self.assertEqual(first_pass_yield([{'first_pass': True}, {'first_pass': False}, {'first_pass': False},
                                           {'first_pass': True}]), 0.5)


@unittest.skipIf(_Chain is None, 'needs the production chain (fastapi)')
class EngineRecordsTheTaxonomy(unittest.TestCase):
    def setUp(self):
        self.chain = _Chain()
        self.chain.setUp() if hasattr(self.chain, 'setUp') else None

    def test_every_group_failure_of_a_round_is_recorded_even_if_summarised(self):
        result, repairer, _ = self.chain.build({'behaviour_ok': False, 'browser_ok': False, 'ok_after_repair': True})
        engine = self.chain.engine
        r0 = [(r['layer'], r['was_repaired']) for r in engine.failure_taxonomy if r['round_index'] == 0]
        self.assertIn(('behaviour', True), r0)
        self.assertIn(('browser', True), r0)                 # summarised for the repairer, still recorded in full
        self.assertFalse(engine.first_pass)

    def test_a_build_whose_post_build_checks_pass_records_no_group_failure(self):
        self.chain.build({'ok_after_repair': True})
        engine = self.chain.engine
        group = [r for r in engine.failure_taxonomy if r['layer'] in ('preview', 'behaviour', 'browser', 'visual')]
        self.assertEqual(group, [])


if __name__ == '__main__':
    unittest.main()
