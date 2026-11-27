"""game_probe: a built game is played in a real Chromium before anyone calls it ready (warehouse 134, acceptance 2-4).

It opens the page twice, at a computer's width with a keyboard and at a phone's width with a touch screen, and
reports what a player would meet:

  page_error         an uncaught exception or a console error
  blank_canvas       the canvas shows one flat colour: nothing is drawn
  input_ignored      a key (computer) or the on-screen button (phone) does not change the game
  no_touch_controls  on a touch screen there is no button to play with, or it is smaller than 44 px
  score_never_rose   a simple player (holds forward, jumps at walls, shoots at the nearest enemy, makes the
                     suggested swap) never scores
  never_ends         stepping past the time limit reaches no end
  no_end_screen      the game ended but the end screen with its words is not shown
  slow               fewer than 30 frames in one second

Everything is read from window.__game, the runtime's read-only window into its own state; the inputs are real
keyboard, mouse and touch events. fastForward steps the same 60 Hz simulation the frame loop steps.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

DESKTOP = {'width': 1280, 'height': 800}
PHONE = {'width': 390, 'height': 844}
MIN_FPS = 30
MIN_TARGET_PX = 44

# Sampled inside the game's own area: the letterbox bars around it are one flat colour by design.
_NOT_BLANK = """() => { const c = document.getElementById('game'); const x = c.getContext('2d');
  const r = c.width / c.height, a = r > 16 / 9 ? [c.height * 16 / 9, c.height] : [c.width, c.width * 9 / 16];
  const area = (c.height > c.width && window.__game.kind === 'match') ? [Math.min(c.width, c.height * 9 / 16), Math.min(c.height, c.width * 16 / 9)] : a;
  const ox = (c.width - area[0]) / 2, oy = (c.height - area[1]) / 2;
  const seen = new Set(); for (let i = 1; i < 16; i++) for (let j = 1; j < 9; j++) {
    const d = x.getImageData(Math.floor(ox + area[0] * i / 16), Math.floor(oy + area[1] * j / 9), 1, 1).data;
    seen.add((d[0] >> 4) + ',' + (d[1] >> 4) + ',' + (d[2] >> 4)); } return seen.size; }"""
_SCREEN = """() => { const s = document.getElementById('screen'); const r = s.getBoundingClientRect();
  return { shown: !s.hidden && getComputedStyle(s).display !== 'none' && r.width > 0, text: s.innerText }; }"""
_BUTTONS = """() => [...document.querySelectorAll('#touch .tb')].map(b => { const r = b.getBoundingClientRect();
  const s = getComputedStyle(b); return { cls: b.className, w: r.width, h: r.height, x: r.x + r.width / 2, y: r.y + r.height / 2,
  visible: s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && !b.closest('[hidden]'),
  inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight }; })"""


def _chromium():
    from playwright.sync_api import sync_playwright
    return sync_playwright


def _launch(p):
    exe = os.environ.get('OMNI_CHROMIUM') or os.environ.get('CHROMIUM_PATH')
    kw = {'args': ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']}
    if exe:
        kw['executable_path'] = exe
    return p.chromium.launch(**kw)


def _state(page):
    return page.evaluate('() => window.__game.state()')


def _ff(page, seconds):
    return page.evaluate('(s) => window.__game.fastForward(s)', seconds)


def _moved(a, b):
    return (a['player'], a['cursor'], a['selected']) != (b['player'], b['cursor'], b['selected'])


def _play_for_score(page, kind, tap=None):
    """A deliberately simple player. It uses only what a person could see, through window.__game.sense()."""
    kb = page.keyboard
    if kind == 'match':
        for _ in range(3):
            pair = page.evaluate('() => window.__game.hint()')
            if not pair:
                return
            for cell in pair:
                pt = page.evaluate('(a) => window.__game.cellCenter(a.c, a.r)', cell)
                (tap or page.mouse.click)(pt['x'], pt['y'])
            if _state(page)['score'] > 0:
                return
        return
    if kind == 'platformer':
        kb.down('ArrowRight')
        for _ in range(160):
            s = page.evaluate('() => window.__game.sense()')
            if any(s.get(k) for k in ('wallAhead', 'gapAhead', 'enemyAhead', 'spikeAhead', 'coinAbove')):
                kb.press('Space')
            if _ff(page, 0.2) != 'playing' or _state(page)['score'] > 0:
                break
        kb.up('ArrowRight')
        return
    if kind == 'shooter':
        kb.down('Space')
        held = None
        for _ in range(200):
            dx = page.evaluate('() => window.__game.sense()').get('targetDx', 0)
            want = 'ArrowRight' if dx > 12 else 'ArrowLeft' if dx < -12 else None
            if want != held:
                if held:
                    kb.up(held)
                if want:
                    kb.down(want)
                held = want
            if _ff(page, 0.15) != 'playing' or _state(page)['score'] > 0:
                break
        if held:
            kb.up(held)
        kb.up('Space')
        return
    if kind == 'runner':
        for _ in range(300):
            if page.evaluate('() => window.__game.sense()').get('obstacleAhead'):
                kb.press('Space')
            if _ff(page, 0.1) != 'playing' or _state(page)['score'] > 0:
                break
        return
    raise ValueError(f'game_probe: unknown kind {kind!r}')


def _run(browser, url, *, phone: bool, texts: dict, time_limit: int) -> tuple[list[dict], dict]:
    where = 'phone' if phone else 'computer'
    findings: list[dict] = []

    def find(kind, message):
        findings.append({'kind': kind, 'where': where, 'message': message[:300]})

    opts = {'viewport': PHONE if phone else DESKTOP}
    if phone:
        opts.update(has_touch=True, is_mobile=True)
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    errors: list[str] = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(url)
    page.wait_for_function('() => window.__game && window.__game.state().frames > 3', timeout=10000)
    kind = page.evaluate('() => window.__game.kind')
    tap = (lambda x, y: page.touchscreen.tap(x, y)) if phone else None
    m: dict = {}

    # start the way a person does
    if phone:
        box = page.locator('#screen-btn').bounding_box()
        page.touchscreen.tap(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    else:
        page.keyboard.press('Enter')
    page.wait_for_timeout(150)
    if _state(page)['status'] != 'playing':
        find('input_ignored', 'the start button or Enter did not start the game')
        ctx.close()
        return findings, m

    m['colours'] = page.evaluate(_NOT_BLANK)
    if m['colours'] < 4:
        find('blank_canvas', f'only {m["colours"]} colour(s) on the canvas')

    f0 = _state(page)['frames']
    page.wait_for_timeout(1000)
    m['fps'] = _state(page)['frames'] - f0
    if m['fps'] < MIN_FPS:
        find('slow', f'{m["fps"]} frames in one second (at least {MIN_FPS})')

    before = _state(page)
    if phone and kind == 'match':
        a, b = (page.evaluate(f'() => window.__game.cellCenter({c}, 1)') for c in (1, 2))
        m['cell_px'] = round(abs(b['x'] - a['x']), 1)
        if m['cell_px'] < MIN_TARGET_PX:
            find('no_touch_controls', f'a board cell is {m["cell_px"]} px wide on the phone (at least {MIN_TARGET_PX})')
        pt = a
        page.touchscreen.tap(pt['x'], pt['y'])
        _ff(page, 0.05)
    elif phone:
        buttons = page.evaluate(_BUTTONS)
        m['buttons'] = len(buttons)
        usable = [b for b in buttons if b['visible'] and b['inside'] and b['w'] >= MIN_TARGET_PX and b['h'] >= MIN_TARGET_PX]
        if not usable or len(usable) != len(buttons):
            find('no_touch_controls', f'{len(usable)} usable of {len(buttons)} on-screen buttons (need all, at least one, '
                                      f'{MIN_TARGET_PX} px or larger, inside the screen)')
        if usable:
            b = next((b for b in usable if 'tb-right' in b['cls']), usable[0])
            page.touchscreen.tap(b['x'], b['y'])
            _ff(page, 0.3)
    else:
        page.keyboard.down('ArrowRight')
        _ff(page, 0.3)
        page.keyboard.up('ArrowRight')
        if kind == 'runner':
            page.keyboard.press('Space')
            _ff(page, 0.1)
    after = _state(page)
    if not _moved(before, after):
        find('input_ignored', f'{"a tap" if phone else "a key"} did not change the game')
    page.wait_for_timeout(150)          # an on-screen tap is held for 120 ms; let it go before the player starts

    if _state(page)['status'] == 'playing':
        _play_for_score(page, kind, tap)
    m['score'] = _state(page)['score']
    if m['score'] <= 0:
        find('score_never_rose', 'a simple player never scored')

    status = _ff(page, time_limit + 5)
    m['end'] = status
    if status not in ('won', 'lost'):
        find('never_ends', f'still {status!r} after the time limit')
    else:
        scr = page.evaluate(_SCREEN)
        words = texts['win'] if status == 'won' else texts['lose']
        if not scr['shown'] or words not in scr['text']:
            find('no_end_screen', f'the game ended ({status}) but the end screen with {words!r} is not shown')
    for e in errors:
        find('page_error', e)
    ctx.close()
    return findings, m


def probe_html(html: str, defn: dict, *, launch=None, files: dict | None = None) -> dict:
    """Play the page at both widths. Returns {'ok', 'findings', 'measures'}; ok only with zero findings. `files` are the
    other files of the game ({'assets/148ai-player.png': bytes}), written next to the page so its art loads as it will."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'index.html'
        path.write_text(html, encoding='utf-8')
        for name, data in (files or {}).items():
            target = (Path(d) / name).resolve()
            if Path(d).resolve() not in target.parents:
                raise ValueError(f'game_probe: {name!r} is outside the game')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        # A page with art is served over HTTP, as a deployment serves it: from a file:// address its images are cross-origin
        # and taint the canvas the probe reads. A page with none opens from the file, as it always did.
        server, url = None, path.as_uri()
        if files:
            import functools
            import http.server
            import threading

            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_GET(self):          # the browser asks for a favicon by itself; its 404 is not the game's error
                    if self.path == '/favicon.ico':
                        self.send_response(204)
                        self.end_headers()
                    else:
                        super().do_GET()
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=d))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/index.html'
        try:
            with _chromium()() as p:
                browser = (launch or _launch)(p)
                try:
                    findings, measures = [], {}
                    for phone in (False, True):
                        f, m = _run(browser, url, phone=phone, texts=defn['texts'], time_limit=defn['time_limit_s'])
                        findings += f
                        measures['phone' if phone else 'computer'] = m
                finally:
                    browser.close()
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
    return {'ok': not findings, 'findings': findings, 'measures': measures}
