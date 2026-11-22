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
