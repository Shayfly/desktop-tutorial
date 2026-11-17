"""Owner 2026-11-16: wire the five accessibility units into G3 -- each unit fails a build when it fails.

Real path: the production worker installs the gate (source check); the gate wraps the real AutonomousProductEngine's
executor; each unit's own broken fixture, as the generated page, fails the build with that unit's code, and a repair
to its ok fixture passes. The real production page of the butcher build (bld_83529c13..., served from app.py, read
with the read-only inspect-round-artifacts workflow) passes all five -- the gate does not block a page customers got.
The generator, repairer and sandbox are fakes (no model, no Docker); the gate, the probes and the engine are not.
"""
from __future__ import annotations

import inspect
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch
from omni_prod.skill_units import gate as G

A11Y = ['a11y_alt_text', 'a11y_contrast', 'a11y_focus', 'a11y_heading_order', 'a11y_labels']
SECRETS = ['secrets_api_keys', 'secrets_assignment', 'secrets_bearer', 'secrets_db_url', 'secrets_private_key']
PERF = ['perf_blocking_script', 'perf_font_display', 'perf_font_preconnect', 'perf_hero_eager', 'perf_inline_image_weight',
        'perf_lazy_images']
BUTCHER = json.loads((Path(__file__).parent / 'fixtures' / 'butcher_served_page_2026_11_14.json').read_text(encoding='utf-8'))


def as_app_py(html: str) -> str:
    return f'HTML_CONTENT = """{html}"""\n\nif __name__ == "__main__":\n    print(HTML_CONTENT)\n'


class _Arch:
    def create_spec(self, prompt):
        return SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='the page'),), requirements=())


class _Files:
    def __init__(self, files):
        self.files, self.failures = files, []

    def generate(self, spec):
        return parse_patch({'files': [{'path': k, 'content': v} for k, v in self.files.items()]})

    def repair(self, *, spec, repo_summary, failures):
        self.failures.append(failures)
        return parse_patch({'files': [{'path': k, 'content': v} for k, v in self.files.items()]})


class _Sandbox:
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'sandbox ok', tests_executed=3)


def engine(first: dict, repaired: dict, rounds=2, gate='G3'):
    rep = _Files(repaired)
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files(first), repairer=rep, executor=_Sandbox(),
                                max_repair_rounds=rounds)
    with mock.patch.dict(os.environ, {f'OMNI_GATE_{gate}': '1'}):
        G.install(e, gate)
    return e, rep


class TheGate(unittest.TestCase):
    def test_g3_is_the_five_accessibility_units_and_g4_the_five_performance_units(self):
        self.assertEqual(G.gate_units('G3'), A11Y)
        self.assertEqual(G.gate_units('G4'), PERF)
        self.assertEqual(G.gate_units('G6'), SECRETS)
        with self.assertRaises(ValueError):
            G.gate_units('G99')

    def test_each_unit_fails_a_build_when_it_fails(self):
        for gate, members in (('G3', A11Y), ('G4', PERF), ('G6', SECRETS)):
            for unit in members:
                with self.subTest(unit):
                    self._fails_then_repairs(gate, unit)

    def _fails_then_repairs(self, gate, unit):
        # the unit's own broken fixture is the generated page; the repair returns the real production page, which
        # passes every unit (a unit's ok fixture is minimal and may fail a sibling unit, e.g. it has no <h1>)
        [(_, broken, expected), *_] = U.fixtures(unit, 'broken')
        e, rep = engine({'index.html': broken}, {'index.html': BUTCHER['page']}, gate=gate)
        result = e.build('a page')
        first = {f['acceptance_id']: f['message'] for f in rep.failures[0] if f['acceptance_id'].startswith(f'gate-{gate}-')}
        self.assertIn(f'gate-{gate}-{unit}', first)
        self.assertTrue(first[f'gate-{gate}-{unit}'].startswith(expected['code']), first)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))     # the repair fixes it

    def test_a_page_that_keeps_failing_fails_the_build(self):
        [(_, broken, _), *_] = U.fixtures('a11y_contrast', 'broken')
        e, _ = engine({'index.html': broken}, {'index.html': broken}, rounds=1)
        self.assertEqual(e.build('a page').status, 'failed')

    def test_a_broken_page_served_from_app_py_fails_too(self):
        [(_, broken, _), *_] = U.fixtures('a11y_labels', 'broken')
        e, rep = engine({'app.py': as_app_py(broken)}, {'app.py': as_app_py(BUTCHER['page'])})
        self.assertEqual(e.build('a page').status, 'ready')
        self.assertIn('gate-G3-a11y_labels', [f['acceptance_id'] for f in rep.failures[0]])

    def test_the_real_production_page_passes_all_five(self):
        for gate in ('G3', 'G4', 'G6'):
            with self.subTest(gate):
                result = G.check(gate, {'app.py': as_app_py(BUTCHER['page'])})
                self.assertEqual(result['status'], 'pass', result['failures'])
                self.assertEqual(len(result['checked']), len(G.gate_units(gate)))
        self.assertIn('bld_83529c132a864075945080e9390484cb', BUTCHER['_source'])

    def test_a_secret_in_the_server_code_fails_even_with_a_clean_page(self):
        leak = 'import os\nDATABASE = "postgresql://shop:' + 'Xk29sd81hf3Qpl' + '@db.shop.test/shop"\n'
        e, rep = engine({'index.html': BUTCHER['page'], 'server.py': leak},
                        {'index.html': BUTCHER['page'], 'server.py': 'import os\nDATABASE = os.environ["DATABASE_URL"]\n'},
                        gate='G6')
        self.assertEqual(e.build('a page').status, 'ready')
        self.assertEqual([f['acceptance_id'] for f in rep.failures[0]], ['gate-G6-secrets_db_url'])
        self.assertIn('server.py', rep.failures[0][0]['message'])

    def test_no_page_is_not_run_and_said(self):
        e, _ = engine({'main.py': 'print(1)\n'}, {'main.py': 'print(1)\n'})
        with self.assertLogs('omni_prod.skill_units.gate', 'WARNING') as logs:
            result = e.build('a script')
        self.assertEqual(result.status, 'ready')
        self.assertEqual(e.executor.last_gate['status'], 'NOT_RUN')
        self.assertIn('GATE_NOT_RUN gate=G3', logs.output[0])


def real_page_broken(unit: str, name: str) -> str:
    return dict((n, h) for n, h, _ in U.fixtures(unit, 'broken'))[name]


class G3FallsOnTheRealPage(unittest.TestCase):
    """Owner 2026-11-16: "a gate that has not been shown to fail does not go in". The broken pages are the real
    production page of the butcher build, changed in one place each; G3 in its default mode fails the build on them."""

    def build(self, page):
        rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                    executor=_Sandbox(), max_repair_rounds=2)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G3', None)                    # the default mode: block
            G.install(e, 'G3')
        return e.build('a page'), rep

    def test_low_contrast_on_the_real_page_fails_the_build(self):
        result, rep = self.build(real_page_broken('a11y_contrast', 'butcher_low_contrast.html'))
        [failure] = [f for f in rep.failures[0] if f['acceptance_id'] == 'gate-G3-a11y_contrast']
        self.assertIn("CONTRAST_LOW (skill.a11y.contrast) on app.py#1", failure['message'])
        self.assertIn("'ratio': 1.79", failure['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_a_removed_focus_on_the_real_page_fails_the_build(self):
        result, rep = self.build(real_page_broken('a11y_focus', 'butcher_focus_removed.html'))
        self.assertIn('gate-G3-a11y_focus', [f['acceptance_id'] for f in rep.failures[0]])

    def test_the_real_page_is_judged_not_passed_blind(self):
        # the first contrast probe read only literal hex; this page sets every colour through var(--...), so it judged
        # nothing and passed. Now its colour pairs are read.
        from omni_prod.skill_units.a11y_contrast.probe import judged
        self.assertGreaterEqual(judged(BUTCHER['page']), 4)


class G4Warns(unittest.TestCase):
    def test_g4_warns_by_default_and_the_build_goes_on(self):
        heavy = dict((n, h) for n, h, _ in U.fixtures('perf_inline_image_weight', 'broken'))['broken1.html']
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'index.html': heavy}),
                                    repairer=_Files({'index.html': heavy}), executor=_Sandbox(), max_repair_rounds=1)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G4', None)
            self.assertEqual(G.mode('G4'), 'warn')
            G.install(e, 'G4')
        with self.assertLogs('omni_prod.skill_units.gate', 'WARNING') as logs:
            result = e.build('a page')
        self.assertEqual(result.status, 'ready')
        self.assertIn('GATE_WARN gate=G4 perf_inline_image_weight:IMAGE_INLINED_HEAVY', ' '.join(logs.output))
        self.assertEqual(G.report(e)['G4']['mode'], 'warn')
        self.assertIn({'unit': 'perf_inline_image_weight', 'page': 'index.html', 'code': 'IMAGE_INLINED_HEAVY'},
                      G.report(e)['G4']['failures'])


class TheSwitch(unittest.TestCase):
    def test_every_gate_states_its_mode_on_every_build_off_included(self):
        e = SimpleNamespace(executor=_Sandbox())
        with mock.patch.dict(os.environ, {'OMNI_GATE_G3': '1', 'OMNI_GATE_G4': 'warn', 'OMNI_GATE_G6': '0'}):
            with self.assertLogs('omni_prod.skill_units.gate', 'INFO') as logs:
                for g in ('G3', 'G4', 'G6'):
                    G.install(e, g)
        self.assertEqual(G.report(e), {'G3': {'mode': 'block'}, 'G4': {'mode': 'warn'}, 'G6': {'mode': 'off'}})
        self.assertIn('GATE_OFF gate=G6', ' '.join(logs.output))

    def test_the_report_walk_is_bounded(self):
        # 2026-11-16, a bug of mine caught before push: report() followed `_inner` without a bound; on a MagicMock
        # engine (the worker harness) every attribute is a new mock and the walk ran out of memory.
        engine = mock.MagicMock()
        self.assertEqual(G.report(engine), {})
        G.install(engine, 'G3')
        self.assertEqual(G.report(engine), {'G3': {'mode': 'block'}})

    def test_the_build_evidence_carries_the_gates(self):
        from omni_prod import worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertIn("evidence['skill_gates'] = skill_gate_report(engine)", src)
        self.assertLess(src.index("evidence['skill_gates']"), src.index('target = BuildStatus.READY if ready'))

    def test_on_by_default_off_said_and_an_unknown_value_raises(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for g in ('OMNI_GATE_G3', 'OMNI_GATE_G4', 'OMNI_GATE_G6'):
                os.environ.pop(g, None)
            self.assertEqual((G.mode('G3'), G.mode('G4'), G.mode('G6')), ('block', 'warn', 'block'))
            self.assertTrue(G.enabled('G3'))
        e = SimpleNamespace(executor=_Sandbox())
        with mock.patch.dict(os.environ, {'OMNI_GATE_G3': '0'}), self.assertLogs('omni_prod.skill_units.gate', 'WARNING'):
            self.assertEqual(G.install(e, 'G3'), [])
        self.assertIsInstance(e.executor, _Sandbox)
        with mock.patch.dict(os.environ, {'OMNI_GATE_G3': 'yes'}), self.assertRaises(ValueError):
            G.install(e, 'G3')

    def test_the_worker_installs_the_gate(self):
        from omni_prod import worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertIn("install_skill_gate(engine, 'G3')", src)
        self.assertIn("install_skill_gate(engine, 'G4')", src)
        self.assertIn("install_skill_gate(engine, 'G6')", src)
        self.assertLess(src.index('install_window_gate(engine'), src.index("install_skill_gate(engine, 'G3')"))


if __name__ == '__main__':
    unittest.main()


class ANewGateWarnsUntilItIsCalibrated(unittest.TestCase):
    """The owner, 2026-11-16, rule 4: a new gate enters at warn; three builds, calibration, a proven fall on a broken
    page, and only then block."""
    def test_every_calibrating_gate_warns_by_default_and_the_proven_ones_block(self):
        import os
        from unittest import mock
        from omni_prod.skill_units import gate as G
        self.assertEqual(set(G.CALIBRATING), {'HE', 'G10', 'G11', 'G1', 'BRAND', 'SHARE', 'G5', 'A4', 'G8', 'GAME'})
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
