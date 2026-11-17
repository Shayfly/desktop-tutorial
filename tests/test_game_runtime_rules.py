"""The game runtime gate's rules, bounds and wiring, without a browser (the real-browser cases are in
tests/test_game_runtime.py). Every rule of `judge` is exercised on its own here, so each negative control is quick."""
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import game_runtime as GR
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.skill_units import gate as G
from tests.test_game_runtime import GOOD, LocalBrowserSandbox


class TheRules(unittest.TestCase):
    OK = {'viewport': 'phone', 'started': True, 'errors': [], 'canvas': {'w': 320, 'h': 240, 'x': 0, 'y': 0, 'screen': 390},
          'colours': 4, 'idle': ['a', 'b', 'c', 'd'], 'played': ['e', 'f', 'g', 'h'], 'text_changed': True,
          'input_calls': 9, 'input_listeners': 2}

    def judged(self, **change):
        return [f['code'] for f in GR.judge({**self.OK, **change})]

    def test_each_rule_on_its_own(self):
        self.assertEqual(self.judged(), [])
        self.assertEqual(self.judged(started=False), ['GAME_NOT_STARTED'])
        self.assertEqual(self.judged(canvas=None), ['GAME_NO_CANVAS'])
        self.assertEqual(self.judged(colours=1), ['GAME_BLANK'])
        self.assertEqual(self.judged(idle=['a'] * 4, played=['a'] * 4, text_changed=False), ['GAME_FROZEN'])
        self.assertEqual(self.judged(input_calls=0, input_listeners=0), ['GAME_IGNORES_INPUT'])
        self.assertEqual(self.judged(input_calls=0, input_listeners=3), ['GAME_IGNORES_INPUT'])  # registered, never called
        self.assertEqual(self.judged(input_calls=None), [])                                      # not measured is not a finding
        self.assertEqual(self.judged(idle=['a'] * 4, played=['b', 'c', 'd', 'e']), [])          # turn-based
        self.assertEqual(self.judged(errors=['x']), ['GAME_ERROR'])
        self.assertEqual(self.judged(canvas={**self.OK['canvas'], 'w': 900}), ['GAME_OFFSCREEN'])
        self.assertEqual(self.judged(viewport='desktop', canvas={**self.OK['canvas'], 'w': 900}), [])
        for code in GR.CODES:
            self.assertIn(code, GR._FIX)

    def test_the_run_is_bounded(self):
        self.assertEqual(len(GR.VIEWPORTS), 2)
        self.assertLessEqual(GR.SAMPLES, 8)
        self.assertLess(2 * GR.SAMPLES * GR.SAMPLE_GAP_MS / 1000 + 25, GR.WALL_SECONDS)

    def test_what_cannot_run_is_not_run_never_a_pass(self):
        class NoSandbox:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), 'ok')
        warn = GR.GameRuntimeExecutor(NoSandbox(), 'warn')
        self.assertTrue(warn.execute(repository=GOOD, spec=None).passed)
        self.assertEqual(warn.last_game['status'], 'NOT_RUN')
        self.assertFalse(GR.GameRuntimeExecutor(NoSandbox(), 'block').execute(repository=GOOD, spec=None).passed)

    def test_a_deadline_ends_the_build_instead_of_being_a_result(self):
        from omni_prod.build_control import BuildDeadline

        class Late(LocalBrowserSandbox):
            def _run(self, *a, **k):
                raise BuildDeadline('out of time')
        with self.assertRaises(BuildDeadline):
            GR.GameRuntimeExecutor(Late(), 'warn').execute(repository=GOOD, spec=None)

    def test_the_rehearsal_judges_a_game_request_as_a_game_and_customers_still_cannot_order_one(self):
        from omni_prod import output_profile as OP
        from omni_prod.intake.families import classify_family
        self.assertEqual(classify_family('תבנה לי משחק קפיצות עם ניקוד'), 'game')
        self.assertFalse(OP.route('game').supported)                       # the profile is not declared yet
        src = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertIn("if report['family'] == 'game':", src)
        self.assertLess(src.index('install_game_runtime(engine)'), src.index('result = engine.build(prompt)'))
        self.assertIn("report['game_runtime'] = game_runtime_report(engine)", src)
        worker = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertNotIn('game_runtime', worker)                           # no customer build is judged as a game

    def test_it_enters_at_warn_and_the_mode_is_written(self):
        from types import SimpleNamespace
        self.assertIn('GAME', G.CALIBRATING)
        engine = SimpleNamespace(executor=LocalBrowserSandbox())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_GAME', None)
            self.assertEqual(GR.install(engine), 'warn')
        self.assertEqual(GR.report(engine), {'gate': 'GAME', 'mode': 'warn', 'last': None})



if __name__ == '__main__':
    unittest.main()
