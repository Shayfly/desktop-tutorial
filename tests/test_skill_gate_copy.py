"""Owner 2026-11-16, build track item 3: the generic-copy gate (G10) -- filler sentences and placeholders (2 skills).

Each unit's broken fixture is the real production page of the butcher build changed in one place; G10, in its default
mode, fails the build on it, and a repair to the unchanged page passes. The unchanged page passes both."""
from __future__ import annotations

import inspect
import os
import unittest
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.skill_units import gate as G
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

COPY = ['copy_filler', 'copy_placeholder']


def build(page):
    rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                executor=_Sandbox(), max_repair_rounds=2)
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('OMNI_GATE_G10', None)
        G.install(e, 'G10')
    return e.build('a page'), rep


class TheCopyGate(unittest.TestCase):
    def test_the_gate_is_two_units_and_blocks_by_default(self):
        self.assertEqual(G.gate_units('G10'), COPY)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G10', None)
            self.assertEqual(G.mode('G10'), 'block')

    def test_each_unit_falls_on_the_real_page_changed_in_one_place(self):
        for unit in COPY:
            for name, page, expected in U.fixtures(unit, 'broken'):
                with self.subTest(unit=unit, fixture=name):
                    result, rep = build(page)
                    msgs = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
                    self.assertTrue(msgs[f'gate-G10-{unit}'].startswith(expected['code']), msgs)
                    self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_unchanged_page_passes(self):
        self.assertEqual(G.check('G10', {'app.py': as_app_py(BUTCHER['page'])})['status'], 'pass')

    def test_placeholders_in_text_and_links(self):
        for html in ('<p>lorem ipsum dolor</p>', '<p>[שם העסק] בירושלים</p>', '<p>שלום {{business_name}}</p>',
                     '<p>טקסט לדוגמה</p>', '<a href="mailto:info@example.com">מייל</a>'):
            with self.subTest(html):
                self.assertEqual(U.run('copy_placeholder', html)['code'], 'COPY_PLACEHOLDER')
        self.assertEqual(U.run('copy_filler', '<h1>Welcome to our website</h1>')['code'], 'COPY_FILLER')

    def test_a_real_sentence_is_not_filler(self):
        for html in ('<p>אנחנו מוציאים בשר טרי כל בוקר</p>', '<p>ברוכים הבאים לאטליז של סבא שמעון</p>',
                     '<style>a{}</style><script>var x = {a: 1}</script><p>מחירים</p>'):
            with self.subTest(html):
                for unit in COPY:
                    self.assertEqual(U.run(unit, html), {'status': 'pass'})

    def test_the_worker_installs_the_gate(self):
        from omni_prod import worker_tasks
        self.assertIn("install_skill_gate(engine, 'G10')", inspect.getsource(worker_tasks._run_live_build_job))


if __name__ == '__main__':
    unittest.main()
