"""Owner 2026-11-16, build track item 7: the empty-blocks gate (G1), the brand gate (BRAND) and the share gate (SHARE),
one unit each. Each unit's broken fixture is the real butcher production page changed in one place; the gate, in its
default mode, fails the build on it, and the repair to the unchanged page passes. The unchanged page passes all three."""
from __future__ import annotations

import inspect
import os
import unittest
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.skill_units import gate as G
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

GATES = {'G1': 'blocks_empty', 'BRAND': 'brand_name', 'SHARE': 'share_meta'}


def build(gate, page):
    rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                executor=_Sandbox(), max_repair_rounds=2)
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop(f'OMNI_GATE_{gate}', None)
        G.install(e, gate)
    return e.build('a page'), rep


class TheThreeGates(unittest.TestCase):
    def test_each_gate_is_its_unit_and_blocks_by_default(self):
        for gate, unit in GATES.items():
            with self.subTest(gate):
                self.assertEqual(G.gate_units(gate), [unit])
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(f'OMNI_GATE_{gate}', None)
                    self.assertEqual(G.mode(gate), 'block')

    def test_each_falls_on_the_real_page_changed_in_one_place(self):
        for gate, unit in GATES.items():
            for name, page, expected in U.fixtures(unit, 'broken'):
                with self.subTest(gate=gate, fixture=name):
                    result, rep = build(gate, page)
                    msgs = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
                    self.assertTrue(msgs[f'gate-{gate}-{unit}'].startswith(expected['code']), msgs)
                    self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_unchanged_page_passes(self):
        for gate in GATES:
            with self.subTest(gate):
                self.assertEqual(G.check(gate, {'app.py': as_app_py(BUTCHER['page'])})['status'], 'pass')

    def test_a_block_with_content_or_media_is_not_empty(self):
        for html in ('<section><h2>מי אנחנו</h2><p>אטליז משפחתי</p></section>',
                     '<section><h2>מפה</h2><iframe src="/map"></iframe></section>'):
            self.assertEqual(U.run('blocks_empty', html), {'status': 'pass'})
        self.assertEqual(U.run('blocks_empty', '<section><h2>המלצות</h2>\n  </section>')['code'], 'EMPTY_BLOCK')

    def test_no_title_and_an_empty_og_value_fail(self):
        self.assertEqual(U.run('brand_name', '<html><body><h1>x</h1></body></html>')['code'], 'BRAND_MISSING')
        self.assertEqual(U.run('share_meta', '<meta property="og:title" content=""><meta property="og:description" '
                                             'content="x">')['code'], 'SHARE_META_MISSING')

    def test_the_worker_installs_the_three(self):
        from omni_prod import worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertIn("for g in ('G1', 'BRAND', 'SHARE'):", src)
        self.assertIn('install_skill_gate(engine, g)', src)


if __name__ == '__main__':
    unittest.main()
