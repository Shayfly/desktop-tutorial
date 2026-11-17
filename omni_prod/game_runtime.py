"""The game runtime gate (plan part A: a game needs "a runtime and load gate (G8)"; stage F item 20, warehouse 69).

A site is judged by its page. A game is judged by whether it PLAYS: the loop draws, the picture changes, a key or a
touch changes what happens, and nothing throws while it runs. None of the page checks see that -- a canvas with one
frozen frame is a valid page.

The product is started in the sandbox's browser profile and opened in headless Chromium at a phone and a desktop
size. For SECONDS it is watched, then given input (a tap in the middle, the arrow keys and space), then watched again:

  GAME_NO_CANVAS     there is no visible <canvas> of at least MIN_SIDE px
  GAME_BLANK         the canvas is one flat colour (nothing was drawn)
  GAME_FROZEN        the canvas did not change between samples: no animation loop is drawing
  GAME_IGNORES_INPUT no code of the page ran in response to a tap, the arrow keys or space: no key, pointer, touch,
                     mouse or click handler was called (counted by wrapping the page's own listeners; a canvas that
                     animates by itself changes with or without input, so pixels cannot answer this)
  GAME_ERROR         an uncaught JavaScript error while it ran
  GAME_OFFSCREEN     on the phone the canvas is wider than the screen

Samples are hashes of the canvas pixels (canvas.toDataURL), compared exactly: no model and no thresholds on "looks
like a game". What this does NOT prove: that a handler which ran did something sensible -- that is the design
review's question, not a gate's. Bounded: two viewports, SAMPLES samples each, WALL_SECONDS at most. It is a new gate (`GAME`), so it
enters at warn (gate.CALIBRATING) and blocks only after three calibration builds.
"""
from __future__ import annotations

import json
import logging

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .preview_runtime import NotPreviewable, parse_preview_contract
from .sandbox_script import staged_script

GATE = 'GAME'
ACCEPTANCE_ID = 'gate-GAME-runtime'
MIN_SIDE = 120
SAMPLES, SAMPLE_GAP_MS = 4, 350
WALL_SECONDS = 60
VIEWPORTS = {'phone': (390, 844, True), 'desktop': (1280, 800, False)}
CODES = ('GAME_NO_CANVAS', 'GAME_BLANK', 'GAME_FROZEN', 'GAME_IGNORES_INPUT', 'GAME_ERROR', 'GAME_OFFSCREEN',
         'GAME_NOT_STARTED')
_LOG = logging.getLogger(__name__)

# Runs inside the sandbox (browser profile). argv[1] = viewport name. Prints one line: "GAME-RUNTIME <json>".
_PROBE = r'''
import hashlib, json, os, subprocess, sys, tempfile, time, urllib.request
VIEW = %(viewports)s[sys.argv[1]]
MIN_SIDE, SAMPLES, GAP = %(min_side)d, %(samples)d, %(gap)d
c = json.load(open(".omni/project.json"))
port = int(c["port"])
scratch = (os.environ.get("OMNI_SCRATCH_DIR") or tempfile.gettempdir())
env = dict(os.environ, PORT=str(port), HOME=scratch, DATA_DIR=scratch, PYTHONDONTWRITEBYTECODE="1")
srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = "http://127.0.0.1:%%d" %% port
out = {"viewport": sys.argv[1], "started": False, "errors": [], "canvas": None, "idle": [], "played": [], "text_changed": False, "input_calls": None, "input_listeners": None}
for _ in range(40):
    try:
        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); out["started"] = True; break
    except Exception:
        if srv.poll() is not None: break
        time.sleep(0.5)
CANVAS = """(min) => { let best = null;
  for (const el of document.querySelectorAll('canvas')) {
    const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || r.width < min || r.height < min) continue;
    if (!best || r.width * r.height > best.w * best.h) best = {w: r.width, h: r.height, x: r.x, y: r.y, el};
  }
  if (!best) return null;
  best.el.dataset.omniGame = '1';
  return {w: Math.round(best.w), h: Math.round(best.h), x: Math.round(best.x), y: Math.round(best.y),
          screen: document.documentElement.clientWidth}; }"""
SHOT = """() => { const el = document.querySelector('canvas[data-omni-game]'); if (!el) return null;
  try { return el.toDataURL('image/png'); } catch (e) { return 'TAINTED'; } }"""
FLAT = """() => { const el = document.querySelector('canvas[data-omni-game]'); if (!el) return null;
  const t = document.createElement('canvas'); t.width = 32; t.height = 32;
  const g = t.getContext('2d'); try { g.drawImage(el, 0, 0, 32, 32); } catch (e) { return null; }
  const d = g.getImageData(0, 0, 32, 32).data; const seen = new Set();
  for (let i = 0; i < d.length; i += 4) seen.add(d[i] + ',' + d[i+1] + ',' + d[i+2] + ',' + d[i+3]);
  return seen.size; }"""
TEXT = "() => (document.body.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 4000)"
# Installed before any script of the page runs: counts calls of the page's own input listeners, and (WRAP, run just
# before the input) of handlers set as properties (onkeydown = ...).
INIT = """(() => { const TYPES = ['keydown','keyup','keypress','pointerdown','pointerup','touchstart','touchend','mousedown','mouseup','click'];
  window.__omniInput = {calls: 0, listeners: 0};
  const add = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function(type, fn, opts) {
    if (TYPES.includes(type) && fn) { window.__omniInput.listeners++;
      const wrapped = function(e) { window.__omniInput.calls++; return (fn.handleEvent ? fn.handleEvent(e) : fn.apply(this, arguments)); };
      return add.call(this, type, wrapped, opts); }
    return add.call(this, type, fn, opts); }; })()"""
WRAP = """() => { const TYPES = ['keydown','keyup','keypress','pointerdown','pointerup','touchstart','touchend','mousedown','mouseup','click'];
  for (const t of [window, document, document.body, ...document.querySelectorAll('canvas, button')]) { if (!t) continue;
    for (const type of TYPES) { const fn = t['on' + type]; if (typeof fn === 'function' && !fn.__omni) {
      window.__omniInput.listeners++;
      const w = function(e) { window.__omniInput.calls++; return fn.apply(this, arguments); }; w.__omni = true; t['on' + type] = w; } } } }"""
if out["started"]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                              args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        ctx = b.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, is_mobile=VIEW[2], has_touch=VIEW[2], locale="he-IL")
        page = ctx.new_page()
        page.add_init_script(INIT)
        page.on("pageerror", lambda e: out["errors"].append(str(e)[:300]))
        try:
            page.goto(base + "/", wait_until="load", timeout=15000)
            page.wait_for_timeout(600)
            out["canvas"] = page.evaluate(CANVAS, MIN_SIDE)
            if out["canvas"]:
                out["colours"] = page.evaluate(FLAT)
                def sample():
                    shot = page.evaluate(SHOT)
                    return None if shot is None else hashlib.sha256(shot.encode()).hexdigest()[:16]
                for _ in range(SAMPLES):
                    out["idle"].append(sample()); page.wait_for_timeout(GAP)
                text_before = page.evaluate(TEXT)
                page.evaluate(WRAP)
                before_calls = page.evaluate("() => window.__omniInput.calls")
                cx, cy = out["canvas"]["x"] + out["canvas"]["w"] / 2, out["canvas"]["y"] + out["canvas"]["h"] / 2
                for _ in range(SAMPLES):
                    if VIEW[2]: page.touchscreen.tap(cx, cy)
                    else: page.mouse.click(cx, cy)
                    for key in ("ArrowRight", "ArrowUp", "Space", "ArrowLeft"):
                        page.keyboard.down(key); page.wait_for_timeout(40); page.keyboard.up(key)
                    page.wait_for_timeout(max(0, GAP - 160))
                    out["played"].append(sample())
                out["text_changed"] = page.evaluate(TEXT) != text_before
                state = page.evaluate("() => window.__omniInput")
                out["input_calls"], out["input_listeners"] = state["calls"] - before_calls, state["listeners"]
        except Exception as e:
            out["errors"].append("probe: " + str(e)[:300])
        b.close()
if srv.poll() is None:
    srv.terminate()
print("GAME-RUNTIME " + json.dumps(out, ensure_ascii=False))
''' % {'viewports': repr({k: list(v) for k, v in VIEWPORTS.items()}), 'min_side': MIN_SIDE, 'samples': SAMPLES,
       'gap': SAMPLE_GAP_MS}


def parse(stdout: str) -> dict | None:
    for line in reversed(str(stdout or '').splitlines()):
        if line.startswith('GAME-RUNTIME '):
            try:
                data = json.loads(line[len('GAME-RUNTIME '):])
            except ValueError:
                return None
            return data if isinstance(data, dict) and 'viewport' in data and isinstance(data.get('idle'), list) else None
    return None


def judge(m: dict) -> list[dict]:
    """[{code, viewport, why}] for one viewport's measurement."""
    v = m.get('viewport')

    def f(code, why):
        return {'code': code, 'viewport': v, 'why': why}
    if not m.get('started'):
        return [f('GAME_NOT_STARTED', 'the server did not answer')]
    found = [f('GAME_ERROR', e) for e in (m.get('errors') or [])[:3]]
    canvas = m.get('canvas')
    if not canvas:
        return found + [f('GAME_NO_CANVAS', f'no visible <canvas> of at least {MIN_SIDE} px')]
    if v == 'phone' and canvas['w'] > canvas.get('screen', canvas['w']) + 2:
        found.append(f('GAME_OFFSCREEN', f"the canvas is {canvas['w']} px wide on a {canvas.get('screen')} px screen"))
    if isinstance(m.get('colours'), int) and m['colours'] <= 1:
        found.append(f('GAME_BLANK', 'the canvas is one flat colour: nothing was drawn'))
    idle, played = [s for s in m.get('idle') or [] if s], [s for s in m.get('played') or [] if s]
    if len(set(idle)) <= 1 and len(set(played)) <= 1 and set(idle) == set(played):
        found.append(f('GAME_FROZEN', 'the canvas never changed, with or without input: no loop is drawing'))
    if m.get('input_calls') == 0:
        found.append(f('GAME_IGNORES_INPUT', f"a tap, the arrow keys and space called no handler of the page "
                                             f"({m.get('input_listeners')} input listener(s) registered)"))
    return found


_FIX = {'GAME_NO_CANVAS': 'Draw the game on one visible <canvas> that fills the play area.',
        'GAME_BLANK': 'Draw the first frame as soon as the page loads (background, player, score).',
        'GAME_FROZEN': 'Run a requestAnimationFrame loop that updates and redraws every frame.',
        'GAME_IGNORES_INPUT': 'Handle keydown (arrow keys, space) AND pointerdown/touchstart on the canvas; each must '
                              'change the game state that is drawn.',
        'GAME_ERROR': 'Fix the JavaScript error; the game loop must never throw.',
        'GAME_OFFSCREEN': 'Size the canvas with CSS max-width: 100% and scale its drawing to its client size.',
        'GAME_NOT_STARTED': 'The server must listen on 0.0.0.0:$PORT and serve the game at /.'}


class GameRuntimeExecutor:
    """warn: findings are recorded and the build goes on. block: each finding fails the build."""

    def __init__(self, inner, mode: str):
        self._inner, self.mode, self.last_game = inner, mode, None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        return self.check(repository=repository, report=report)

    def _not_run(self, reason: str, report):
        self.last_game = {'status': 'NOT_RUN', 'mode': self.mode, 'reason': reason[:300]}
        _LOG.warning('GAME_NOT_RUN mode=%s reason=%s', self.mode, reason[:300])
        if self.mode != 'block':
            return report
        from .verification_verdict import unverified
        return unverified(ACCEPTANCE_ID, reason, report.build_log)

    def check(self, *, repository, report):
        try:
            contract = parse_preview_contract(repository)
        except NotPreviewable as exc:
            return self._not_run(f'no preview contract to start the game from: {exc}', report)
        run = getattr(self._inner, '_run', None)
        if not contract.runtime.startswith('python') or not callable(run):
            return self._not_run(f'no sandbox runtime to start {contract.runtime!r}', report)
        viewports, findings = {}, []
        for name in VIEWPORTS:                               # bounded: two viewports
            try:
                staged, argv = staged_script(repository, 'game_runtime', _PROBE, name)
                result = run(staged, argv, f'game-{name}', profile='browser')
            except Exception as exc:
                from .verification_verdict import reraise_control
                reraise_control(exc)
                return self._not_run(f'the game run could not start ({name}): {type(exc).__name__}: {exc}', report)
            measured = parse(result.get('stdout', ''))
            if measured is None:
                return self._not_run(f'the game run printed no measurement ({name})', report)
            viewports[name] = measured
            findings.extend(judge(measured))
        self.last_game = {'status': 'fail' if findings else 'pass', 'mode': self.mode, 'viewports': viewports,
                          'findings': findings}
        _LOG.info('GAME_RUNTIME mode=%s status=%s findings=%s', self.mode, self.last_game['status'],
                  [(f['viewport'], f['code']) for f in findings])
        if not findings or self.mode != 'block':
            return report
        seen, failures = set(), []
        for f in findings:
            if f['code'] in seen:
                continue                                     # one instruction per code; the evidence keeps them all
            seen.add(f['code'])
            failures.append(AcceptanceFailure(ACCEPTANCE_ID, f"{f['code']} ({f['viewport']}): {f['why']}. {_FIX[f['code']]}"))
        return ExecutionReport(False, tuple(report.failures) + tuple(failures), report.build_log)


def install(engine) -> str:
    from .skill_units import gate as G
    core = getattr(engine, 'core', engine)
    mode = G.mode(GATE)
    modes = dict(getattr(core, 'gate_modes', None) or {})
    modes[GATE] = mode
    core.gate_modes = modes
    if mode == 'off':
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s): this build is NOT checked by %s', GATE, GATE, GATE)
        return mode
    _LOG.info('GATE_ON gate=%s mode=%s', GATE, mode)
    core.executor = core.game_runtime_check = GameRuntimeExecutor(core.executor, mode)
    return mode


def report(engine) -> dict:
    core = getattr(engine, 'core', engine)
    modes = getattr(core, 'gate_modes', None)
    checker = getattr(core, 'game_runtime_check', None)
    return {'gate': GATE, 'mode': modes.get(GATE) if isinstance(modes, dict) else None,
            'last': checker.last_game if isinstance(checker, GameRuntimeExecutor) else None}
