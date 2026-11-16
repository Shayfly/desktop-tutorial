"""The first five skills as units (owner 2026-11-16; plan part B section 4): every unit has its five parts, its probe
passes every ok fixture and fails every broken fixture with the code the fixture names, and every code it can emit is
declared. Units, fixtures and expected codes are read from the unit directories -- a new unit is checked by adding it."""
from __future__ import annotations

import unittest

from omni_prod import skill_units as U

EXPECTED = {'a11y_contrast': 'skill.a11y.contrast', 'a11y_focus': 'skill.a11y.focus', 'a11y_labels': 'skill.a11y.labels',
            'a11y_heading_order': 'skill.a11y.heading_order', 'a11y_alt_text': 'skill.a11y.alt_text'}


class EveryUnitIsComplete(unittest.TestCase):
    def test_the_five_accessibility_units_exist(self):
        self.assertTrue(set(EXPECTED) <= set(U.units()))

    def test_each_unit_has_its_five_parts(self):
        for unit in U.units():
            with self.subTest(unit):
                m = U.manifest(unit)
                self.assertEqual(m['name'], EXPECTED.get(unit, m['name']))
                self.assertEqual((m['kind'], m['cost_usd']), ('probe', 0))
                self.assertIs(m['reads_source'], m['gate'] == 'G6')       # only the secrets units read every file
                self.assertTrue(U.failure_codes(unit))
                self.assertTrue(U.fixtures(unit, 'ok'))
                self.assertTrue(U.fixtures(unit, 'broken'))
                for name, _, expected in U.fixtures(unit, 'broken'):
                    self.assertTrue(expected.get('code') and expected.get('what_is_broken'), (unit, name))


class EveryProbeSeparatesOkFromBroken(unittest.TestCase):
    def test_ok_fixtures_pass(self):
        for unit in U.units():
            for name, html, _ in U.fixtures(unit, 'ok'):
                with self.subTest(unit=unit, fixture=name):
                    self.assertEqual(U.run(unit, html), {'status': 'pass'})

    def test_broken_fixtures_fail_with_their_code(self):
        for unit in U.units():
            for name, html, expected in U.fixtures(unit, 'broken'):
                with self.subTest(unit=unit, fixture=name):
                    r = U.run(unit, html)
                    self.assertEqual((r['status'], r['code']), ('fail', expected['code']))
                    self.assertTrue(r['findings'])

    def test_an_undeclared_code_raises(self):
        import importlib
        mod = importlib.import_module('omni_prod.skill_units.a11y_alt_text.probe')
        real = mod.probe
        try:
            mod.probe = lambda html: {'status': 'fail', 'code': 'SOMETHING_ELSE', 'findings': [1]}
            with self.assertRaises(ValueError):
                U.run('a11y_alt_text', '<img>')
        finally:
            mod.probe = real


class TheContrastNumbersAreReal(unittest.TestCase):
    def test_the_measured_ratio_is_reported(self):
        r = U.run('a11y_contrast', '<p style="color:#999999;background:#ffffff">x</p>')
        self.assertEqual(r['findings'][0]['ratio'], 2.85)


if __name__ == '__main__':
    unittest.main()
