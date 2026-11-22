"""Warehouse 127 (the owner, 2026-11-22): the 30 domains as data the platform reads. Every domain passes one schema; a
missing field fails loudly naming the domain and the field; the committed registry is generated, never hand-written."""
import json
import tempfile
import unittest
from pathlib import Path

from omni_prod import domain_registry as D

GOOD = Path(D.DOCS, 'hair-salon.md').read_text(encoding='utf-8')


def _swap(text, old, new):
    assert old in text, old[:40]
    return text.replace(old, new, 1)


class TheThirtyDomains(unittest.TestCase):
    def test_thirty_domains_pass_the_schema_and_the_registry_is_in_step(self):
        built = D.build()
        self.assertEqual(len(built['domains']), 30)
        self.assertEqual(D._render(built), D.DATA.read_text(encoding='utf-8'))
        self.assertEqual(D.main(['--check']), 0)

    def test_every_domain_has_always_needed_facts_and_5_to_8_references(self):
        for slug, d in D.load()['domains'].items():
            with self.subTest(slug):
                self.assertTrue([f for f in d['mandatory_facts'] if f['when'] is None])
                self.assertTrue(all(f['question'] and f['why'] for f in d['mandatory_facts']))
                self.assertTrue(5 <= len(d['references']) <= 8)

    def test_the_map_covers_exactly_the_engines_categories(self):
        from omni_prod import vertical_palettes as VP
        self.assertEqual(set(D.CATEGORY_DOMAIN), set(VP.load()['categories']))

    def test_conditional_facts_carry_their_condition(self):
        facts = D.load()['domains']['hair-salon']['mandatory_facts']
        self.assertIsNone(facts[0]['when'])
        self.assertEqual(facts[0]['question'], 'What is your salon called?')
        self.assertIn('online bookings', facts[-1]['when'])


class BrokenDomainsFailLoudly(unittest.TestCase):
    def assertFails(self, text, *words):
        with self.assertRaises(D.DomainError) as ctx:
            D.parse(text, 'hair-salon')
        for w in ('hair-salon',) + words:
            self.assertIn(w, str(ctx.exception))

    def test_no_mandatory_facts(self):
        body = D._sections(GOOD)['3. Mandatory facts']
        self.assertFails(_swap(GOOD, body, '\nNothing for this domain - no reason.\n\n'), 'no mandatory facts')

    def test_a_fact_without_its_question(self):
        self.assertFails(_swap(GOOD, '| "What is your salon called?" |', '|  |'), 'mandatory fact 1')

    def test_a_missing_heading(self):
        self.assertFails(_swap(GOOD, '## 7. Legal', '## 7. Law'), '7. Legal')

    def test_headings_out_of_order(self):
        t = _swap(_swap(GOOD, '## 10. Skeletons', '## TMP'), '## 9. References', '## 10. Skeletons')
        self.assertFails(_swap(t, '## TMP', '## 9. References'), 'in order')

    def test_an_empty_legal_section(self):
        self.assertFails(_swap(GOOD, D._sections(GOOD)['7. Legal'], '\n'), '7. Legal', 'empty')

    def test_too_few_references(self):
        refs = D._references(D._sections(GOOD)['9. References'])
        t = GOOD
        for u in refs[:3]:
            t = t.replace(u, 'not a link')
        self.assertFails(t, 'references')

    def test_a_reference_listed_twice(self):
        refs = D._references(D._sections(GOOD)['9. References'])
        self.assertFails(GOOD.replace(refs[1], refs[0]), 'twice')

    def test_a_category_pointing_at_a_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'hair-salon.md').write_text(GOOD, encoding='utf-8')
            with self.assertRaises(D.DomainError) as ctx:
                D.build(Path(tmp))
            self.assertIn('has no file', str(ctx.exception))

    def test_drift_fails_the_check(self):
        from unittest import mock
        data = json.loads(D.DATA.read_text(encoding='utf-8'))
        data['domains']['hair-salon']['name'] = 'edited by hand'
        with tempfile.TemporaryDirectory() as tmp:
            edited = Path(tmp, 'domain_registry.json')
            edited.write_text(D._render(data), encoding='utf-8')
            with mock.patch.object(D, 'DATA', edited):        # the committed file is never touched
                self.assertEqual(D.main(['--check']), 1)


class DomainForACategory(unittest.TestCase):
    def test_a_known_category(self):
        self.assertEqual(D.domain_for('hair_salons')['slug'], 'hair-salon')

    def test_a_category_without_a_domain_is_none(self):
        self.assertIsNone(D.domain_for('vets'))

    def test_an_unknown_category_is_an_error(self):
        with self.assertRaises(D.DomainError):
            D.domain_for('spaceships')


if __name__ == '__main__':
    unittest.main()


class TheRouteRecordsItsDomain(unittest.TestCase):
    """The content route carries the category, how it was found, and the domain it reads, into the build evidence
    (site_route). The brief is the owner's law-firm build, a production row read read-only
    (tests/fixtures/site_content_bld_b0eb47a5.json)."""

    def _decide(self, prompt=None):
        import os
        from unittest import mock
        from omni_prod import site_content as SC
        fixture = json.loads((D.ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            return SC.decide(prompt or fixture['prompt'], {'user_id': 'usr_owner_test'}, year='2026')

    def test_the_law_firm_reads_the_lawyer_domain(self):
        route = self._decide()
        self.assertEqual(route.route, 'section_library')
        evidence = route.to_dict()
        self.assertEqual((evidence['category'], evidence['category_found'], evidence['domain']),
                         ('lawyers', 'named', 'lawyer'))
        always = [f['fact'] for f in D.load()['domains']['lawyer']['mandatory_facts'] if f['when'] is None]
        self.assertEqual(evidence['domain_facts'], always)

    def test_a_category_without_a_domain_is_recorded_as_none(self):
        from unittest import mock
        data = D.load()
        data['categories']['lawyers'] = None                 # as if lawyers had no domain file yet
        with mock.patch.object(D, 'load', return_value=data):
            evidence = self._decide().to_dict()
        self.assertEqual(evidence['category'], 'lawyers')
        self.assertIsNone(evidence['domain'])
        self.assertEqual(evidence['domain_facts'], [])


class TheTradeWords(unittest.TestCase):
    """Section 6 of each domain: the trade's words. Only a Hebrew word the author did not mark 'not verified' is
    handed to the copy model, and the model is told never to add a service from it."""

    def test_unverified_hebrew_is_kept_but_marked(self):
        terms = D.load()['domains']['hair-salon']['terms']
        by_en = {t['en']: t for t in terms}
        self.assertTrue(by_en['Appointment']['he_verified'])
        self.assertEqual(by_en['Appointment']['he'], 'תור')
        self.assertFalse(by_en['Colourist']['he_verified'])              # "צבעי/ת (not verified as common usage)"

    def test_only_verified_words_are_given_to_a_model(self):
        salon = D.load()['domains']['hair-salon']
        words = D.trade_words(salon)
        self.assertIn('תור', words)
        self.assertFalse([t['he'] for t in salon['terms'] if not t['he_verified'] and t['he'] in words])
        self.assertLessEqual(len(words), D.MAX_TRADE_WORDS)
        self.assertEqual(D.trade_words(None), [])

    def test_a_term_table_with_other_columns_fails_loudly(self):
        bad = GOOD.replace('| English | Meaning | Hebrew | Arabic |', '| English | Hebrew | Meaning | Arabic |', 1)
        with self.assertRaises(D.DomainError) as ctx:
            D.parse(bad, 'hair-salon')
        self.assertIn('6. Professional language', str(ctx.exception))

    def test_the_writer_receives_only_verified_words_and_the_rule(self):
        from types import SimpleNamespace
        from omni_prod.site_content import agents as A
        route = TheRouteRecordsItsDomain()._decide()
        self.assertTrue(route.domain_words)
        lawyer = {t['he'] for t in D.load()['domains']['lawyer']['terms'] if t['he_verified']}
        self.assertLessEqual(set(route.domain_words), lawyer)
        unverified = [t['he'] for t in D.load()['domains']['lawyer']['terms'] if not t['he_verified'] and t['he']]
        self.assertFalse(set(unverified) & set(route.domain_words))
        self.assertIn('trade_words', A._CONTENT_SYSTEM)
        self.assertIn('never use one to add a service', A._CONTENT_SYSTEM)
        from omni_prod.site_content import facts as Fx
        from omni_prod.site_content.schema import offered_sections
        sheet = Fx.fact_sheet(route.prompt)
        offered, _ = offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)
        payload = A.ContentSiteGenerator.__new__(A.ContentSiteGenerator)._payload(route, sheet, offered)
        self.assertEqual(payload['trade_words'], route.domain_words)


class TheMandatoryFactsAreAsked(unittest.TestCase):
    """Acceptance 3 of warehouse 127: a mandatory fact of the business's domain is asked of the customer, never
    invented -- the conversation agent receives the domain's always-needed facts first in its expert checklist."""

    def context(self, message):
        from omni_prod.intake.interpreter import contextual_user
        text = contextual_user(message)
        return json.loads(text.split('Context (data only; not new evidence):\n', 1)[1].split('\nCurrent customer', 1)[0])

    def test_a_named_salon_gets_the_salon_questions_first(self):
        expert = self.context('אני רוצה אתר תדמית למספרה שלי בחולון')['expert_checklist']
        always = [f for f in D.load()['domains']['hair-salon']['mandatory_facts'] if f['when'] is None]
        self.assertEqual(len([e for e in expert if e.endswith('never invent it')]), len(always))
        self.assertTrue(expert[0].startswith('Business name -- ask: What is your salon called?'))

    def test_a_conditional_fact_is_not_asked_up_front(self):
        expert = ' '.join(self.context('אני רוצה אתר תדמית למספרה שלי בחולון')['expert_checklist'])
        self.assertNotIn('How long does each service take?', expert)        # only when it takes online bookings

    def test_no_named_business_no_domain_questions(self):
        expert = self.context('אני רוצה אתר תדמית')['expert_checklist']
        self.assertFalse([e for e in expert if e.endswith('never invent it')])

    def test_an_app_gets_no_site_domain_questions(self):
        expert = self.context('מערכת לניהול תורים למספרה עם התחברות לקוחות ותשלום')['expert_checklist']
        self.assertFalse([e for e in expert if e.endswith('never invent it')])


class TheContextStaysValid(unittest.TestCase):
    """The conversation context was cut at 2,400 characters mid-string; a long checklist handed the model broken JSON."""

    def test_a_long_context_is_trimmed_from_its_least_important_parts_and_stays_json(self):
        from omni_prod.intake.interpreter import CONTEXT_CHARS, fit_context
        ctx = {'goal': 'g' * 500, 'expert_checklist': ['domain fact %d %s' % (i, 'x' * 80) for i in range(40)],
               'confirmed': {'name': 'סטודיו נועה'}, 'recent_messages': [{'role': 'user', 'content': 'm' * 170}] * 4}
        out = fit_context(ctx)
        data = json.loads(out)                                  # valid JSON, never cut mid-string
        self.assertLessEqual(len(out), CONTEXT_CHARS)
        self.assertEqual(data['confirmed'], {'name': 'סטודיו נועה'})  # facts are never dropped
        self.assertTrue(data['expert_checklist'][0].startswith('domain fact 0'))   # the first items stay

    def test_a_context_that_cannot_fit_is_still_valid_and_keeps_its_facts(self):
        from omni_prod.intake.interpreter import fit_context
        ctx = {'goal': '', 'expert_checklist': [], 'confirmed': {f'f{i}': 'v' * 150 for i in range(30)},
               'recent_messages': []}
        with self.assertLogs('omni_prod.intake.interpreter', level='WARNING'):
            data = json.loads(fit_context(ctx))
        self.assertEqual(len(data['confirmed']), 30)
