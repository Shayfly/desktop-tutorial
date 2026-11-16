"""Owner 2026-11-16, build track item 2: the Hebrew gate -- grammar, gender agreement, translationese (3 skills).

"A gate that has not been shown to fail does not go in": each unit's broken fixture is the real production page of the
butcher build (bld_83529c13...), changed in one place; the gate, in its default mode, fails the build on it, and a
repair to the unchanged page passes. The unchanged page passes all three -- the gate does not block what customers got.
Real path: the gate wraps the real AutonomousProductEngine's executor; generator, repairer and sandbox are fakes."""
from __future__ import annotations

import inspect
import os
import unittest
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.skill_units import gate as G
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

HE = ['he_gender', 'he_grammar', 'he_translationese']


def build(page):
    rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                executor=_Sandbox(), max_repair_rounds=2)
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ['OMNI_GATE_HE'] = 'block'      # the blocking behaviour, said explicitly (the default is warn while calibrating)
        G.install(e, 'HE')
    return e.build('a page'), rep


class TheHebrewGate(unittest.TestCase):
    def test_the_gate_is_three_units_and_blocks_by_default(self):
        self.assertEqual(G.gate_units('HE'), HE)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_HE', None)
            self.assertEqual(G.mode('HE'), 'warn')    # owner 2026-11-16, rule 4: warn until calibrated on three builds

    def test_each_unit_falls_on_the_real_page_changed_in_one_place(self):
        for unit in HE:
            for name, page, expected in U.fixtures(unit, 'broken'):
                with self.subTest(unit=unit, fixture=name):
                    result, rep = build(page)
                    msgs = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
                    self.assertIn(f'gate-HE-{unit}', msgs)
                    self.assertTrue(msgs[f'gate-HE-{unit}'].startswith(expected['code']))
                    self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_unchanged_page_passes(self):
        self.assertEqual(G.check('HE', {'app.py': as_app_py(BUTCHER['page'])})['status'], 'pass')

    def test_text_is_read_one_node_at_a_time(self):
        # the page's hours table has a "שבת" cell next to a "שבת סגור" cell: two nodes, not a repeated word
        self.assertEqual(U.run('he_grammar', '<table><tr><td>שבת</td><td>שבת סגור</td></tr></table>'), {'status': 'pass'})
        self.assertEqual(U.run('he_grammar', '<p>שבת שבת סגור</p>')['code'], 'HE_GRAMMAR')

    def test_the_findings_say_the_correct_form(self):
        self.assertIn('"טרי"', str(U.run('he_gender', '<p>בשר טרייה</p>')['findings']))
        self.assertIn('בית הקפה', str(U.run('he_grammar', '<p>בהבית קפה שלנו</p>')['findings']))
        self.assertIn('בסופו של דבר', str(U.run('he_translationese', '<p>בסוף היום</p>')['findings']))

    def test_words_outside_the_lists_are_not_judged_and_reduplication_is_hebrew(self):
        for text in ('<p>הודו מובחר</p>', '<p>לאט לאט</p>', '<p>שתי שעות ושני ימים</p>', '<p>מנה טעימה ובשר טרי</p>'):
            with self.subTest(text):
                for unit in HE:
                    self.assertEqual(U.run(unit, text), {'status': 'pass'})

    def test_the_worker_installs_the_gate(self):
        from omni_prod import worker_tasks
        self.assertIn("install_skill_gate(engine, 'HE')", inspect.getsource(worker_tasks._run_live_build_job))


if __name__ == '__main__':
    unittest.main()
