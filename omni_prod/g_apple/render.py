"""G-APPLE, part 3: the page as a browser lays it out, at four widths (the owner: 390 / 768 / 1440 / 320, full page).

Runs in the sandbox's browser profile; measured, never judged by eye:

  H_SCROLL          the page scrolls sideways
  CLIPPED_TEXT      text cut by its own box
  CONTROL_UNDER_44  a button, link-button or field under 44 px in either direction
  OFF_GRID          a margin, padding or gap of a visible block that is not a multiple of 4 px (the 8-grid's half step)
  MEASURE           a paragraph of two lines or more whose line is outside 55-75 characters -- judged at 768 and 1440
                    only: at 320 and 390 a 55-character line would need unreadably small text, so it is not asked there
  STRING_30 / STRING_60   a heading, button or nav link given a 30 / 60 character string breaks the layout (sideways
                    scroll, or the text is cut): real names and prices are longer than the sample copy

One full-page screenshot per width is taken and its sha256 and size are reported (the bytes stay in the sandbox; the
reviewers use the screenshots visual QA already returns). Bounded: four widths, MAX_ELEMENTS elements per rule.
"""
from __future__ import annotations

import json

WIDTHS = (390, 768, 1440, 320)
HEIGHT = 900
MIN_CONTROL = 44
MEASURE_MIN, MEASURE_MAX = 55, 75
MEASURE_FROM_WIDTH = 768
MAX_ELEMENTS = 60
CODES = ('H_SCROLL', 'CLIPPED_TEXT', 'CONTROL_UNDER_44', 'OFF_GRID', 'MEASURE', 'STRING_30', 'STRING_60', 'NOT_STARTED',
         'PAGE_ERROR')

# Runs inside the sandbox (browser profile). argv[1] = width. Prints one line: "APPLE-RENDER <json>".
PROBE = r'''
import hashlib, json, os, subprocess, sys, tempfile, time, urllib.request
WIDTH, HEIGHT, MIN_CONTROL, MMIN, MMAX, MFROM, MAXEL = int(sys.argv[1]), %(height)d, %(min_control)d, %(mmin)d, %(mmax)d, %(mfrom)d, %(maxel)d
c = json.load(open(".omni/project.json"))
port = int(c["port"])
scratch = (os.environ.get("OMNI_SCRATCH_DIR") or tempfile.gettempdir())
env = dict(os.environ, PORT=str(port), HOME=scratch, DATA_DIR=scratch, PYTHONDONTWRITEBYTECODE="1")
srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = "http://127.0.0.1:%%d" %% port
out = {"width": WIDTH, "started": False, "findings": [], "screenshot": None, "errors": []}
for _ in range(40):
    try:
        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); out["started"] = True; break
    except Exception:
        if srv.poll() is not None: break
        time.sleep(0.5)
AUDIT = """([minControl, mmin, mmax, judgeMeasure, maxEl]) => { const out = []; const doc = document.documentElement;
  const sel = (el) => { let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id;
    if (typeof el.className === 'string' && el.className.trim()) s += '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.'); return s; };
  const add = (code, el, why) => { if (out.filter(f => f.code === code).length < 6) out.push({code, selector: el ? sel(el) : '', why}); };
  const vis = (el) => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
  if (doc.scrollWidth > doc.clientWidth + 1) add('H_SCROLL', null, 'page ' + doc.scrollWidth + 'px wide in a ' + doc.clientWidth + 'px window');
  let n = 0;
  for (const el of document.querySelectorAll('button, input:not([type=hidden]), select, textarea, a.btn, a.button, a.cta, [role=button]')) {
    if (++n > maxEl) break; if (!vis(el)) continue; const r = el.getBoundingClientRect();
    if (r.width < minControl || r.height < minControl) add('CONTROL_UNDER_44', el, Math.round(r.width) + 'x' + Math.round(r.height) + ' px'); }
  n = 0;
  for (const el of document.querySelectorAll('h1, h2, h3, p, li, a, button, span, td, th, label')) {
    if (++n > maxEl * 4) break; if (!vis(el) || el.children.length) continue; const s = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 1 && ['hidden', 'clip'].includes(s.overflowX)) add('CLIPPED_TEXT', el, (el.innerText || '').slice(0, 40)); }
  n = 0;
  for (const el of document.querySelectorAll('section, header, footer, main, nav, article, div, ul, form, h1, h2, h3, p, button, a')) {
    if (++n > maxEl * 4) break; if (!vis(el)) continue; const s = getComputedStyle(el);
    for (const p of ['marginTop', 'marginBottom', 'paddingTop', 'paddingBottom', 'paddingLeft', 'paddingRight', 'rowGap', 'columnGap']) {
      const v = parseFloat(s[p]); if (!isFinite(v) || v <= 0) continue;
      if (Math.abs(v - Math.round(v / 4) * 4) > 0.5) { add('OFF_GRID', el, p + ' ' + s[p]); break; } } }
  if (judgeMeasure) { n = 0;
    for (const el of document.querySelectorAll('p')) { if (++n > maxEl) break; if (!vis(el)) continue;
      const s = getComputedStyle(el); const lh = parseFloat(s.lineHeight) || parseFloat(s.fontSize) * 1.2;
      const lines = Math.round(el.getBoundingClientRect().height / lh); const chars = (el.innerText || '').trim().length;
      if (lines >= 2 && chars >= 2 * mmin) { const per = Math.round(chars / lines);
        if (per < mmin || per > mmax) add('MEASURE', el, per + ' characters a line'); } } }
  return out; }"""
STRETCH = """(len) => { const rtl = getComputedStyle(document.documentElement).direction === 'rtl';
  const word = rtl ? 'אבגדהוזחטי' : 'abcdefghij'; let text = ''; while (text.length < len) text += word + ' '; text = text.slice(0, len);
  const els = [...document.querySelectorAll('h1, h2, h3, button, a.btn, a.button, a.cta, nav a')].filter(el => el.children.length === 0).slice(0, 20);
  const before = els.map(el => el.textContent); els.forEach(el => { el.textContent = text; });
  const doc = document.documentElement; const broken = [];
  if (doc.scrollWidth > doc.clientWidth + 1) broken.push({selector: '', why: 'the page scrolls sideways'});
  for (const el of els) { const s = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 1 && ['hidden', 'clip'].includes(s.overflowX)) broken.push({selector: el.tagName.toLowerCase(), why: 'the text is cut'}); }
  els.forEach((el, i) => { el.textContent = before[i]; }); return broken.slice(0, 4); }"""
if out["started"]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                              args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        mobile = WIDTH < 768
        ctx = b.new_context(viewport={"width": WIDTH, "height": HEIGHT}, is_mobile=mobile, has_touch=mobile, locale="he-IL")
        page = ctx.new_page()
        page.on("pageerror", lambda e: out["errors"].append(str(e)[:200]))
        try:
            page.goto(base + "/", wait_until="load", timeout=15000)
            page.wait_for_timeout(300)
            out["findings"] = page.evaluate(AUDIT, [MIN_CONTROL, MMIN, MMAX, WIDTH >= MFROM, MAXEL])
            for n in (30, 60):
                for f in page.evaluate(STRETCH, n):
                    out["findings"].append({"code": "STRING_%%d" %% n, "selector": f["selector"], "why": f["why"]})
            shot = page.screenshot(full_page=True, type="png")
            out["screenshot"] = {"sha256": hashlib.sha256(shot).hexdigest(), "bytes": len(shot)}
        except Exception as e:
            out["errors"].append("probe: " + str(e)[:300])
        b.close()
if srv.poll() is None:
    srv.terminate()
print("APPLE-RENDER " + json.dumps(out, ensure_ascii=False))
''' % {'height': HEIGHT, 'min_control': MIN_CONTROL, 'mmin': MEASURE_MIN, 'mmax': MEASURE_MAX,
       'mfrom': MEASURE_FROM_WIDTH, 'maxel': MAX_ELEMENTS}


def parse(stdout: str) -> dict | None:
    for line in reversed(str(stdout or '').splitlines()):
        if line.startswith('APPLE-RENDER '):
            try:
                data = json.loads(line[len('APPLE-RENDER '):])
            except ValueError:
                return None
            return data if isinstance(data, dict) and isinstance(data.get('findings'), list) and 'width' in data else None
    return None


def findings(measured: dict) -> list[dict]:
    """[{code, width, selector, why}] of one width's measurement."""
    w = measured.get('width')
    if not measured.get('started'):
        return [{'code': 'NOT_STARTED', 'width': w, 'selector': '', 'why': 'the server did not answer'}]
    out = [{'code': 'PAGE_ERROR', 'width': w, 'selector': '', 'why': str(e)[:200]} for e in (measured.get('errors') or [])[:3]]
    for f in measured.get('findings') or []:
        if isinstance(f, dict) and f.get('code') in CODES:
            out.append({'code': f['code'], 'width': w, 'selector': str(f.get('selector', ''))[:80],
                        'why': str(f.get('why', ''))[:160]})
    return out
