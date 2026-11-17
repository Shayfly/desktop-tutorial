"""A new gate warns until it is calibrated (the owner, 2026-11-16, rule 4), and the rehearsal runs the worker's gates.
Kept apart from tests/test_skill_gates.py so that file's negative controls keep their exact expected failures."""
import unittest

from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py


class ANewGateWarnsUntilItIsCalibrated(unittest.TestCase):
    """The owner, 2026-11-16, rule 4: a new gate enters at warn; three builds, calibration, a proven fall on a broken
    page, and only then block."""
    def test_every_calibrating_gate_warns_by_default_and_the_proven_ones_block(self):
        import os
        from unittest import mock
        from omni_prod.skill_units import gate as G
        self.assertEqual(set(G.CALIBRATING), {'HE', 'G10', 'G11', 'G1', 'BRAND', 'SHARE'})
        with mock.patch.dict(os.environ, {}, clear=False):
            for gate in (*G.CALIBRATING, 'G3', 'G4', 'G6'):
                os.environ.pop(f'OMNI_GATE_{gate}', None)
            for gate in G.CALIBRATING:
                self.assertEqual(G.mode(gate), 'warn', gate)
            self.assertEqual((G.mode('G3'), G.mode('G6'), G.mode('G4')), ('block', 'block', 'warn'))

    def test_every_gate_the_worker_installs_has_a_stated_default(self):
        import re
        from pathlib import Path
        from omni_prod.skill_units import gate as G
        src = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        named = set(re.findall(r"install_skill_gate\(engine, '(\w+)'\)", src))
        loop = re.search(r"for g in \(([^)]*)\):\s*#[^\n]*\n\s*install_skill_gate\(engine, g\)", src)
        named |= set(re.findall(r"'(\w+)'", loop.group(1))) if loop else set()
        self.assertGreaterEqual(len(named), 9)
        self.assertEqual(named - set(G.DEFAULT_MODE), set())      # a gate with no stated default would block in silence
        self.assertEqual(named, set(G.WORKER_GATES))              # the rehearsal installs this list: the same gates

    def test_the_rehearsal_runs_the_gates_a_customers_build_runs(self):
        from pathlib import Path
        from types import SimpleNamespace
        from omni_prod.skill_units import gate as G
        engine = SimpleNamespace(executor=SimpleNamespace(execute=lambda **k: None))
        installed = G.install_all(engine)
        self.assertEqual(tuple(installed), G.WORKER_GATES)
        self.assertEqual(set(engine.gate_modes), set(G.WORKER_GATES))
        src = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertLess(src.index('install_all(engine)'), src.index('result = engine.build(prompt)'))
        self.assertIn("report['skill_gates'] = skill_gate_report(engine)", src)

    def test_a_calibrating_gate_keeps_its_findings_and_a_blocking_one_keeps_codes_only(self):
        import os
        from unittest import mock
        from omni_prod.autonomous_core import AutonomousProductEngine
        from omni_prod.skill_units import gate as G
        page = BUTCHER['page'].replace('</body>', '<p>ברוכים הבאים לאתר שלנו</p><img src="x.png"></body>')
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}),
                                    repairer=_Files({'app.py': as_app_py(page)}), executor=_Sandbox(), max_repair_rounds=0)
        with mock.patch.dict(os.environ, {'OMNI_GATE_G3': 'warn'}):
            os.environ.pop('OMNI_GATE_G10', None)
            G.install(e, 'G3')
            G.install(e, 'G10')
        e.build('a page')
        rep = G.report(e)
        g10 = rep['G10']
        self.assertEqual((g10['mode'], g10['status']), ('warn', 'fail'))
        finding = g10['failures'][0]['findings'][0]
        self.assertIn('ברוכים הבאים', finding['where'] + finding['why'])
        self.assertLessEqual(len(g10['failures'][0]['findings']), G.MAX_CALIBRATION_FINDINGS)
        self.assertEqual(rep['G3']['status'], 'fail')
        self.assertTrue(all('findings' not in f for f in rep['G3']['failures']))     # proven gate: codes only
        self.assertNotIn('G6', G.CALIBRATING)                                        # a secret is never copied

    def test_a_calibrating_gate_can_still_be_set_to_block(self):
        import os
        from unittest import mock
        from omni_prod.skill_units import gate as G
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'block'}):
            self.assertEqual(G.mode('HE'), 'block')


if __name__ == '__main__':
    unittest.main()
