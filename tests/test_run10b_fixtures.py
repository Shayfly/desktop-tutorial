"""Stage 0 of the run-10b triage (Michael 2026-11-11): lock the failures BEFORE fixing them.

The briefs are the exact approved contract prompts of frozen run frozen-2026-11-10b (tests/fixtures/run10b_briefs.json).
Two kinds of test:

  LockedFailures  the behaviour we WANT, marked @expectedFailure because the code still fails it. When a fix lands, the
                  test passes, unittest reports an UNEXPECTED SUCCESS, and the run fails until the marker is removed --
                  so no fix can land silently and no failure can disappear unnoticed. Each test names its triage item.
  Guards          behaviour that is right today and must stay right through R1-R7: the strict two-phone canon, the
                  native-app refusal, and Michael's two positive fixtures (products that DO need stored data must keep
                  it -- R2 must resolve, never over-block).

No model is called: every check is deterministic (classifier, contract compiler, fact canon).
"""
from __future__ import annotations

import json
import unittest
from functools import lru_cache
from pathlib import Path

FIXTURE = Path(__file__).parent / 'fixtures' / 'run10b_briefs.json'
BRIEFS: dict[str, str] = json.loads(FIXTURE.read_text(encoding='utf-8'))['briefs']
STATIC_ARMS = ('locksmith_hard', 'florist_details', 'florist_nodetails')
POSITIVE = ('positive_signup', 'positive_contact_form')


def typed(name: str) -> str:
    """What the customer typed (the approved prompt minus the brief 148AI wrote after ' --- ')."""
    return BRIEFS[name].split(' --- ')[0]


@lru_cache(maxsize=None)
def contract(name: str) -> dict:
    from omni_prod.product_architect import ProductArchitect
    return ProductArchitect().compile(BRIEFS[name], project_id='prj_run10b_fixture', contract_version=1,
                                      created_at='2026-11-11T00:00:00+00:00').to_dict()


def data_acceptance(c: dict) -> list[str]:
    return [a['requirement_id'] for a in c['acceptance']
            if a['requirement_id'] == 'platform-data' or a['requirement_id'].startswith('module-')]


def production_canon_status(name: str) -> str:
    """canon_view exactly as conversation/supervisor.py calls it today (family from is_website)."""
    from omni_prod.fact_canon import canon_view
    from omni_prod.intake.families import classify_family
    text = typed(name)
    return canon_view(text, family='website' if classify_family(text) == 'website' else 'app')['status']


class LockedFailures(unittest.TestCase):
    # ---- R3: "a page for my business / my shop" is a website ----
    @unittest.expectedFailure
    def test_r3_locksmith_is_a_website(self):
        from omni_prod.intake.families import classify_family
        self.assertEqual(classify_family(typed('locksmith_hard')), 'website')

    @unittest.expectedFailure
    def test_r3_florist_details_is_a_website(self):
        from omni_prod.intake.families import classify_family
        self.assertEqual(classify_family(typed('florist_details')), 'website')

    @unittest.expectedFailure
    def test_r3_florist_nodetails_is_a_website(self):
        from omni_prod.intake.families import classify_family
        self.assertEqual(classify_family(typed('florist_nodetails')), 'website')

    # ---- R1/R2: an approved static page carries no data requirement (today: customers/availability/bookings) ----
    @unittest.expectedFailure
    def test_r1_locksmith_contract_has_no_data_requirement(self):
        c = contract('locksmith_hard')
        self.assertEqual((c['data_requirements'], data_acceptance(c)), ([], []))

    @unittest.expectedFailure
    def test_r1_florist_details_contract_has_no_data_requirement(self):
        c = contract('florist_details')
        self.assertEqual((c['data_requirements'], data_acceptance(c)), ([], []))

    @unittest.expectedFailure
    def test_r1_florist_nodetails_contract_has_no_data_requirement(self):
        c = contract('florist_nodetails')
        self.assertEqual((c['data_requirements'], data_acceptance(c)), ([], []))

    # ---- R4: the warned path fires on a business page with no phone and no address (arm 3: it did not) ----
    @unittest.expectedFailure
    def test_r4_florist_nodetails_warns(self):
        self.assertEqual(production_canon_status('florist_nodetails'), 'CANON_INCOMPLETE')

    # ---- arm-1 hole: reviews written as '"quote" — name;' never reach the canon, so the truth gate cannot check them ----
    @unittest.expectedFailure
    def test_locksmith_reviews_enter_the_canon(self):
        from omni_prod.fact_canon import build_canon
        self.assertEqual(len(build_canon(typed('locksmith_hard')).values('review')), 2)


class Guards(unittest.TestCase):
    def test_locksmith_two_phones_are_two_facts(self):
        from omni_prod.fact_canon import build_canon
        self.assertEqual(build_canon(typed('locksmith_hard')).values('phone'), {'+972521234567', '+97289876543'})

    def test_r4_pair_details_present_is_quiet(self):
        # the other half of R4: a page WITH phone and address must not warn, before or after the fix
        self.assertEqual(production_canon_status('florist_details'), 'OK')

    def test_native_ios_is_refused(self):
        from omni_prod.intake.families import classify_family
        from omni_prod.planning.feasibility import EXECUTABLE
        fam = classify_family(BRIEFS['refusal_ios'])
        self.assertEqual(fam, 'mobile_app')
        self.assertNotIn(fam, EXECUTABLE)

    def test_positive_fixtures_keep_their_data(self):
        for name in POSITIVE:
            with self.subTest(name):
                c = contract(name)
                self.assertTrue(c['data_requirements'], f'{name}: a product that stores data lost its data requirement')
                self.assertIn('platform-data', data_acceptance(c))


if __name__ == '__main__':
    unittest.main()
