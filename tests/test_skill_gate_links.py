"""Owner 2026-11-16, build track item 3: the links gate (G11) -- tel: links, in-page anchors, a whole address (3 skills).

Each unit's broken fixture is the real production page of the butcher build changed in one place; G11, in its default
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

LINKS = ['links_address', 'links_anchor', 'links_tel']


def build(page):
    rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                executor=_Sandbox(), max_repair_rounds=2)
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('OMNI_GATE_G11', None)
        G.install(e, 'G11')
    return e.build('a page'), rep


class TheLinksGate(unittest.TestCase):
    def test_the_gate_is_three_units_and_blocks_by_default(self):
        self.assertEqual(G.gate_units('G11'), LINKS)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G11', None)
            self.assertEqual(G.mode('G11'), 'block')

    def test_each_unit_falls_on_the_real_page_changed_in_one_place(self):
        for unit in LINKS:
            for name, page, expected in U.fixtures(unit, 'broken'):
                with self.subTest(unit=unit, fixture=name):
                    result, rep = build(page)
                    msgs = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
                    self.assertTrue(msgs[f'gate-G11-{unit}'].startswith(expected['code']), msgs)
                    self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_unchanged_page_passes(self):
        self.assertEqual(G.check('G11', {'app.py': as_app_py(BUTCHER['page'])})['status'], 'pass')

    def test_phones(self):
        run = lambda html: U.run('links_tel', html)
        self.assertEqual(run('<p>חייגו <a href="tel:0504000162">050-4000162</a></p>'), {'status': 'pass'})
        self.assertEqual(run('<p>טלפון: 050-4000162</p>')['code'], 'TEL_BROKEN')           # shown, cannot be tapped
        self.assertEqual(run('<a href="tel:12345">x</a>')['code'], 'TEL_BROKEN')             # not a number
        self.assertIn('does not show', str(run('<p>03-5551234</p><a href="tel:035551234">a</a><a href="tel:0504000162">b</a>')))

    def test_anchors_and_addresses(self):
        self.assertEqual(U.run('links_anchor', '<a href="#a">a</a><section id="a"></section><a href="#">top</a>'),
                         {'status': 'pass'})
        self.assertEqual(U.run('links_anchor', '<a href="#menu">a</a>')['code'], 'ANCHOR_BROKEN')
        self.assertEqual(U.run('links_address', '<p>כתובת: הרצל 12, חיפה</p>'), {'status': 'pass'})
        self.assertEqual(U.run('links_address', '<dt>כתובת</dt><dd>הרצל 12, חיפה</dd>'), {'status': 'pass'})
        self.assertIn('a city', str(U.run('links_address', '<p>כתובת: הרצל 12</p>')))
        self.assertEqual(U.run('links_address', '<h2>כתובת והתקשרות</h2><p>בואו לבקר</p>'), {'status': 'pass'})  # a heading

    def test_the_worker_installs_the_gate(self):
        from omni_prod import worker_tasks
        self.assertIn("install_skill_gate(engine, 'G11')", inspect.getsource(worker_tasks._run_live_build_job))


if __name__ == '__main__':
    unittest.main()
