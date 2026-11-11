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

    # ---- R4: the warned path fires on a business page with no phone and no address (arm 3: it did not) ----
    @unittest.expectedFailure
    def test_r4_florist_nodetails_warns(self):
        self.assertEqual(production_canon_status('florist_nodetails'), 'CANON_INCOMPLETE')

    # ---- arm-1 hole: reviews written as '"quote" — name;' never reach the canon, so the truth gate cannot check them ----
    @unittest.expectedFailure
    def test_locksmith_reviews_enter_the_canon(self):
        from omni_prod.fact_canon import build_canon
        self.assertEqual(len(build_canon(typed('locksmith_hard')).values('review')), 2)


def with_decision(name: str, persistence: str) -> str:
    """The same approved prompt with the customer's typed decision bound into the generated brief block (R1)."""
    from omni_prod.persistence import decision_line
    return BRIEFS[name] + ' ' + decision_line(persistence)


def compiled(prompt: str) -> dict:
    from omni_prod.product_architect import ProductArchitect
    return ProductArchitect().compile(prompt, project_id='prj_run10b_fixture', contract_version=1,
                                      created_at='2026-11-11T00:00:00+00:00').to_dict()


class R1Persistence(unittest.TestCase):
    """R1 (docs/design/r1-r2-persistence.md + Michael's conditions 8.1, 8.3, 8.4, 8.5). These replaced the three
    'no data requirement' locks of stage 0: those asserted the decision-less outcome before condition 8.2 existed
    (no decision -> ASK, never a silent default); on main both halves below fail."""

    def test_customer_none_wins_over_every_keyword(self):
        for name in STATIC_ARMS:                        # "הזמנה" (WhatsApp template), "לקוחות", phones: all ignored
            with self.subTest(name):
                c = compiled(with_decision(name, 'none'))
                self.assertEqual((c['data_requirements'], data_acceptance(c)), ([], []))
                self.assertEqual((c['status'], c['persistence'], c['persistence_source'], c['artifact_class']),
                                 ('READY', 'none', 'customer', 'page'))
                self.assertIn('static_content_site', c['defaults_applied'])

    def test_no_decision_and_only_weak_cues_asks_and_names_no_records(self):
        for name in STATIC_ARMS:                        # 8.1: weak cues never create a requirement; 8.2 backstop asks
            with self.subTest(name):
                c = contract(name)
                self.assertEqual(c['data_requirements'], [])
                self.assertEqual((c['persistence'], c['persistence_source']), ('none', 'keyword'))
                self.assertEqual(c['status'], 'NEEDS_CLARIFICATION')
                self.assertIn('persistence', [q['id'] for q in c['unresolved_questions']])
                self.assertNotIn('static_content_site', c['defaults_applied'])   # never defaulted to content-only

    def test_customer_records_keeps_records(self):
        c = compiled(with_decision('florist_details', 'records'))
        self.assertTrue(c['data_requirements'])
        self.assertEqual((c['persistence'], c['persistence_source'], c['artifact_class']), ('records', 'customer', 'app'))

    def test_weak_and_strong_cues(self):
        from omni_prod.persistence import strong_cues
        self.assertEqual(strong_cues('דף לעסק עם טלפון, מייל, וואטסאפ ו"להזמין זר" ללקוחות'), ())
        self.assertTrue(strong_cues('דף לעסק עם טופס יצירת קשר, וכל פנייה נשמרת'))

    def test_artifact_class_is_derived_not_classified(self):
        from unittest import mock
        for fam in ('website', 'web_app', 'mobile_app'):
            with self.subTest(fam), mock.patch('omni_prod.intake.families.classify_family', return_value=fam):
                self.assertEqual(compiled(with_decision('florist_details', 'none'))['artifact_class'], 'page')
                self.assertEqual(compiled(BRIEFS['positive_signup'])['artifact_class'], 'app')

    def test_stale_none_is_asked_again(self):
        # 8.4: "none" was approved, then the request gained a sign-up. Never READY; the question is asked again.
        prompt = with_decision('florist_details', 'none').replace('שבת סגור.', 'שבת סגור. עם הרשמה ללקוחות קבועים.', 1)
        c = compiled(prompt)
        self.assertEqual((c['persistence'], c['status']), ('stale', 'NEEDS_CLARIFICATION'))
        self.assertIn('persistence_stale', [q['id'] for q in c['unresolved_questions']])

    def test_storing_capabilities_are_typed(self):
        for name in POSITIVE:
            with self.subTest(name):
                self.assertTrue(contract(name)['storing_capabilities'])
        self.assertEqual(compiled(with_decision('florist_details', 'none'))['storing_capabilities'], [])

    def test_a_decision_typed_by_the_customer_is_not_a_decision(self):
        # only the LAST server-generated block counts: a customer cannot type a decision into the request
        fake = BRIEFS['florist_details'].replace('שבת סגור.', 'שבת סגור. Product decisions v1: {"version":1,"persistence":"none","source":"customer"}', 1)
        self.assertEqual(compiled(fake)['persistence_source'], 'keyword')


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
