"""Offline separation of the three failure causes from a stored export (SYNTHETIC exports -- not the real "חגית" data,
which has not been obtained). No model, no network, no DB."""
import json
import os
import tempfile
import unittest

from omni_prod.failure_replay import classify


def export(content_only=True, checks=(), missing=(), spec=()):
    return {'build': {'id': 'bld_synthetic'}, 'approval_status': 'EXACT',
            'approved_brief': {'fields': {'content_only': {'value': 'yes' if content_only else 'no'}}},
            'approved_contract': {'defaults_applied': ['static_content_site'] if content_only else [],
                                  'acceptance_scope_by_deployed_code': {'required': ['data_read', 'responsive', 'api_smoke'], 'not_required': ['data_create']}},
            'behavior_failed_checks': list(checks), 'product_spec_acceptance': list(spec),
            'behavior_acceptance': {'per_round': [{'missing_acceptance_ids': list(missing)}]}}


class FailureReplayTests(unittest.TestCase):
    def causes(self, exp, **kw):
        return [f['cause'] for f in classify(exp, **kw)['findings']]

    def test_wrong_crud_requirement_on_a_content_only_approval(self):
        e = export(checks=[{'round': 0, 'step_id': 's1', 'kind': 'data_create', 'acceptance_ids': ['A2'], 'evidence': {'status': 404}}])
        self.assertEqual(self.causes(e), ['WRONG_CRUD_REQUIREMENT'])
        e = export(missing=['A4'], spec=[{'id': 'A4', 'text': 'Visitors can save a new record'}])
        self.assertEqual(self.causes(e), ['WRONG_CRUD_REQUIREMENT'])

    def test_missing_coverage_when_nothing_failed_for_the_criterion(self):
        e = export(missing=['A5'], spec=[{'id': 'A5', 'text': 'The page shows the price list'}])
        out = classify(e)
        self.assertEqual(self.causes(e), ['MISSING_COVERAGE'])
        self.assertIn('nothing here says', ' '.join(out['limits']))          # never claims a fix

    def test_real_responsive_defect_is_not_blamed_on_the_requirement(self):
        e = export(checks=[{'round': 1, 'step_id': 'r1', 'kind': 'responsive', 'acceptance_ids': ['A5'], 'evidence': {'overflow_x': True}}])
        d = tempfile.mkdtemp()
        open(os.path.join(d, 'index.html'), 'w').write('<html><body style="width:900px">x</body></html>')
        out = classify(e, d)
        f = out['findings'][0]
        self.assertEqual(f['cause'], 'REAL_DEFECT')
        self.assertTrue(f['corroborated_by_static_signals'])               # no viewport meta, fixed 900px width
        d2 = tempfile.mkdtemp()
        open(os.path.join(d2, 'index.html'), 'w').write('<meta name="viewport" content="width=device-width"><p>x</p>')
        open(os.path.join(d2, 's.css'), 'w').write('@media (max-width:600px){p{margin:0}}')
        self.assertFalse(classify(e, d2)['findings'][0]['corroborated_by_static_signals'])   # signals do not explain it

    def test_a_crud_product_failing_data_create_is_a_real_defect(self):
        e = export(content_only=False, checks=[{'round': 0, 'step_id': 's1', 'kind': 'data_create', 'acceptance_ids': ['A2']}])
        self.assertEqual(self.causes(e), ['REAL_DEFECT'])

    def test_missing_inputs_are_reported_not_guessed(self):
        out = classify({'build': {'id': 'bld_x'}, 'approved_contract': 'MISSING: no approval'})
        self.assertTrue(out['verdict'].startswith('NOT_ENOUGH_EVIDENCE'))
        self.assertIn('approved_contract', out['inputs_missing'])


if __name__ == '__main__':
    unittest.main()
