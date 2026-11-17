"""The game runtime gate (stage F item 20; warehouse 69).

Real games run here in real Chromium: each case is a small product (app.py serving one HTML page with a canvas) that
the gate's own script starts and plays, exactly as the sandbox's browser profile would; the request passes the real
sandbox request policy first. Only the transport to the remote sandbox is replaced by a local process. Without a
local Chromium the browser cases are NOT_RUN (skipped, said)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import game_runtime as GR
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.sandbox_request_policy import validate_command, validate_snapshot
from omni_prod.skill_units import gate as G

PORT = 18474
CHROMIUM = os.environ.get('OMNI_CHROMIUM') or os.environ.get('CHROMIUM_PATH') or '/opt/pw-browsers/chromium'
try:
    import playwright  # noqa: F401
    HAVE_BROWSER = Path(CHROMIUM).is_file()
except ImportError:
    HAVE_BROWSER = False
MANIFEST = json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'],
                       'port': PORT, 'health_path': '/'})
_APP = '''
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PAGE = %r.encode()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''
_PAGE = '''<!doctype html><html lang="he" dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>canvas{max-width:100%%;display:block;margin:0 auto;%(css)s}</style></head><body><h1>משחק</h1>
%(markup)s<p id="score">0</p><script>%(script)s</script></body></html>'''
_LOOP = '''
const c = document.getElementById('g'), x = c.getContext('2d'); let t = 0, px = 100, score = 0;
function draw(){ x.fillStyle = '#123'; x.fillRect(0,0,c.width,c.height); x.fillStyle = '#fc0';
  x.fillRect(px, 100, 30, 30); x.fillStyle = '#fff'; %(moving)s }
%(input)s
%(run)s
'''
CANVAS = '<canvas id="g" width="320" height="240"></canvas>'
MOVING = "x.fillRect((t*3)%320, 20, 10, 10); t++;"
INPUT = ("function act(){ px = (px + 25) % 280; score++; document.getElementById('score').textContent = score; }\n"
         "addEventListener('keydown', act); c.addEventListener('pointerdown', act);")
RAF = "(function loop(){ draw(); requestAnimationFrame(loop); })();"


def game(markup=CANVAS, moving=MOVING, input_=INPUT, run=RAF, css='', script=None):
    js = script if script is not None else _LOOP % {'moving': moving, 'input': input_, 'run': run}
    page = _PAGE % {'markup': markup, 'script': js, 'css': css}
    return {'app.py': _APP % page, '.omni/project.json': MANIFEST}


GOOD = game()
PROPERTY_HANDLERS = game(input_=("function act(){ px = (px + 25) % 280; score++; document.getElementById('score').textContent = score; }\n"
                                 "document.onkeydown = act; c.onpointerdown = act;"))
FROZEN = game(moving='', input_="addEventListener('keydown', () => 0); c.addEventListener('pointerdown', () => 0);", run='draw();')   # one frame, then nothing
BLANK = game(script="document.getElementById('g').getContext('2d');")  # a canvas nobody draws on
IGNORES = game(input_='')                                             # it animates, and no key or tap changes it
THROWS = game(run=RAF + "\nsetTimeout(() => { throw new Error('boom in the loop'); }, 300);")
NO_CANVAS = game(markup='<div id="g">טקסט בלבד</div>', script='')
TOO_WIDE = game(markup='<canvas id="g" width="900" height="240"></canvas>', css='max-width:none;width:900px;')
TURN_BASED = game(moving='', run='draw();', input_=INPUT + "\naddEventListener('keydown', draw); c.addEventListener('pointerdown', draw);")


class LocalBrowserSandbox:
    def __init__(self):
        self.runs = []

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'ok')

    def _run(self, repository, argv, build_id, profile='default'):
        validate_snapshot(repository)                                 # the real request policy, unchanged
        validate_command(argv, build_id=build_id, profile=profile, repository=repository)
        self.runs.append((argv, profile))
        chromium = CHROMIUM if Path(CHROMIUM).is_file() else None
        with tempfile.TemporaryDirectory() as root:
            for path, text in repository.items():
                target = Path(root) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            env = dict(os.environ, **({'OMNI_CHROMIUM': chromium} if chromium else {}))
            done = subprocess.run([sys.executable, *argv[1:]], cwd=root, capture_output=True, text=True,
                                  timeout=GR.WALL_SECONDS + 30, env=env)
        return {'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr}


def play(repo, mode='block'):
    gate = GR.GameRuntimeExecutor(LocalBrowserSandbox(), mode)
    return gate, gate.execute(repository=repo, spec=None)


def codes(gate):
    return {f['code'] for f in gate.last_game['findings']}


@unittest.skipUnless(HAVE_BROWSER, 'NOT_RUN: no local Chromium and Playwright')
class RealGamesInARealBrowser(unittest.TestCase):
    def test_a_game_that_plays_passes_on_the_phone_and_the_desktop(self):
        gate, report = play(GOOD)
        self.assertEqual((gate.last_game['status'], gate.last_game['findings']), ('pass', []), gate.last_game)
        self.assertTrue(report.passed)
        self.assertEqual(sorted(gate.last_game['viewports']), ['desktop', 'phone'])
        for m in gate.last_game['viewports'].values():
            self.assertGreater(len(set(m['idle'] + m['played'])), 2)
            self.assertTrue(m['text_changed'])                          # the score moved when it was played
            self.assertGreater(m['input_calls'], 0)
        self.assertEqual([p for _, p in gate._inner.runs], ['browser', 'browser'])

    def test_one_frozen_frame_is_found(self):
        gate, report = play(FROZEN)
        self.assertFalse(report.passed)
        self.assertEqual(codes(gate), {'GAME_FROZEN'})
        self.assertIn('requestAnimationFrame', ' '.join(f.message for f in report.failures))

    def test_a_canvas_nobody_draws_on_is_found(self):
        gate, _ = play(BLANK)
        self.assertIn('GAME_BLANK', codes(gate))

    def test_a_game_that_ignores_every_key_and_tap_is_found(self):
        gate, _ = play(IGNORES)
        self.assertEqual(codes(gate), {'GAME_IGNORES_INPUT'})

    def test_handlers_set_as_properties_count_too(self):
        gate, report = play(PROPERTY_HANDLERS)
        self.assertEqual(gate.last_game['findings'], [], gate.last_game)

    def test_a_turn_based_game_that_only_moves_on_input_passes(self):
        gate, report = play(TURN_BASED)
        self.assertEqual(gate.last_game['findings'], [], gate.last_game)
        self.assertTrue(report.passed)

    def test_an_error_while_it_runs_is_found(self):
        gate, _ = play(THROWS)
        self.assertIn('GAME_ERROR', codes(gate))
        self.assertTrue(any('boom in the loop' in f['why'] for f in gate.last_game['findings']))

    def test_a_page_with_no_canvas_is_found(self):
        gate, _ = play(NO_CANVAS)
        self.assertEqual(codes(gate), {'GAME_NO_CANVAS'})

    def test_a_canvas_wider_than_the_phone_is_found_on_the_phone_only(self):
        gate, _ = play(TOO_WIDE)
        off = [f for f in gate.last_game['findings'] if f['code'] == 'GAME_OFFSCREEN']
        self.assertEqual([f['viewport'] for f in off], ['phone'])

    def test_in_warn_mode_the_build_goes_on_and_the_finding_is_recorded(self):
        with self.assertLogs(GR.__name__, level='INFO') as logs:
            gate, report = play(FROZEN, 'warn')
        self.assertTrue(report.passed)
        self.assertEqual((gate.last_game['status'], gate.last_game['mode']), ('fail', 'warn'))
        self.assertTrue(any('GAME_RUNTIME mode=warn status=fail' in line for line in logs.output))


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
