import copy
import json
import unittest
from datetime import datetime, timezone

from omni_prod.a2 import approved_research as R
from omni_prod.reference_store import MemoryReferenceStore, card_sha256
from tests.reference_cards_fixture import card

NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)


def sample(n=5):
    store, grants = MemoryReferenceStore(), {}
    for i in range(1, n + 1):
        c = card(i)
        store.add_card(c, extraction_version='x1')
        grants[c['card_id']] = R.RightsGrant(card_sha256(c), f'license-{i}', True, 'owned')
    return store, grants


def prepare(store, grants):
    return R.prepare(store, category='butcher', grants=grants, now=NOW)


def response(p):
    return {'input_sha256': p['input_sha256'], 'recommendations': [
        {'reference_id': r['id'], 'strengths': ['air']} for r in p['model_request']['references'][:3]]}


class ApprovedResearch(unittest.TestCase):
    def test_model_receives_only_closed_structure_and_scores(self):
        s, g = sample(12)
        p = prepare(s, g)
        self.assertEqual(p['status'], 'READY_FOR_METERED_COMPARISON')
        self.assertEqual(p['model'], 'gemini-3.8-flash')
        self.assertEqual(len(p['model_request']['references']), 8)
        payload = json.dumps(p['model_request'], ensure_ascii=False)
        for forbidden in ('https://', 'license-', 'מרווח נדיב', 'references/', 'sha256'):
            self.assertNotIn(forbidden, payload)
        self.assertEqual(len(p['evidence']), 8)
        self.assertIn('source_url', p['evidence'][0])

    def test_rights_are_required_for_exact_card_revision(self):
        s, g = sample(3)
        cid = next(iter(g))
        for bad in (R.RightsGrant('0'*64, 'license', True, 'owned'),
                    R.RightsGrant(g[cid].card_sha256, 'license', False, 'owned'),
                    R.RightsGrant(g[cid].card_sha256, 'license', True, 'google_grounding'),
                    R.RightsGrant(g[cid].card_sha256, '', True, 'owned'), None):
            with self.subTest(bad=bad):
                g2 = dict(g); g2[cid] = bad
                p = prepare(s, g2)
                self.assertEqual(p['status'], 'INSUFFICIENT_APPROVED_REFERENCES')
                self.assertIsNone(p['model_request'])
        self.assertEqual(prepare(s, {})['eligible_count'], 0)

    def test_retired_stale_or_unapproved_cards_are_not_admitted(self):
        s, g = sample(3)
        s.retire(next(iter(g)), by='shai')
        self.assertEqual(prepare(s, g)['eligible_count'], 2)
        s, g = sample(3)
        self.assertEqual(R.prepare(s, category='butcher', grants=g,
                                  now=datetime(2027, 4, 1, tzinfo=timezone.utc))['eligible_count'], 0)

    def test_valid_comparison_is_not_build_approval_or_measured_cost(self):
        p = prepare(*sample())
        out = R.validate_comparison(p, response(p))
        self.assertEqual(out['status'], 'MODEL_RECOMMENDATIONS_VALIDATED')
        self.assertFalse(out['build_approval'])
        self.assertEqual(out['cost_state'], 'NOT_MEASURED_HERE')
        self.assertEqual(len(out['evidence']), 3)

    def test_unknown_duplicate_and_unmeasured_claims_fail(self):
        p = prepare(*sample())
        for modify in (
            lambda x: x['recommendations'][0].update(reference_id='invented'),
            lambda x: x['recommendations'][1].update(reference_id=x['recommendations'][0]['reference_id']),
            lambda x: x['recommendations'][0].update(strengths=['hierarchy']),
            lambda x: x['recommendations'][0].update(text='invented price'),
            lambda x: x.update(input_sha256='0'*64),
        ):
            r = response(p); modify(r)
            with self.assertRaises(R.ResearchEvidenceError):
                R.validate_comparison(p, r)

    def test_evidence_tampering_and_wrong_model_fail(self):
        p = prepare(*sample())
        r = response(p)
        p['evidence'][0]['source_url'] = 'https://wrong.example.org/'
        with self.assertRaises(R.ResearchEvidenceError):
            R.validate_comparison(p, r)
        p = prepare(*sample())
        r = response(p)
        p['model'] = 'other'
        with self.assertRaises(R.ResearchEvidenceError):
            R.validate_comparison(p, r)

    def test_tampered_input_and_insufficient_pool_fail(self):
        p = prepare(*sample())
        r = response(p)
        p['model_request']['references'][0]['measured_scores']['hierarchy'] = 2
        with self.assertRaises(R.ResearchEvidenceError):
            R.validate_comparison(p, r)
        with self.assertRaises(R.ResearchEvidenceError):
            R.validate_comparison(prepare(*sample(2)), r)


if __name__ == '__main__':
    unittest.main()
