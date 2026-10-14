"""Real-browser behaviour check of a generated web product (directive
2026-10-09 §11, §17: "a model review does not replace API, browser or visual
inspection").

Why: the founder's library site (v_f65e904334, 2026-10-08) passed unit tests,
HTTP acceptance probes and a code review, yet in a browser every status message
after the first one stayed hidden (`showBanner` left `style.display='none'`).
Only something that clicks like a user sees that.

`PROBE` runs inside the browser sandbox image (no network, read-only source,
headless Chromium driven by Playwright). It starts the product the way the
preview does, opens "/", and for each form fills plausible values by field
type and submits it -- twice, a few seconds apart, the way a person adds two
records. It reports, as JSON on stdout:

  page_error          an uncaught JavaScript exception (the page is broken)
  dead_form           submit produced no request and no visible change
  feedback_disappears the first submit revealed a message, the second
                      (also successful) revealed nothing: the user cannot
                      tell whether anything happened
  server_error        a same-origin request answered 5xx during the flow

These are blocking findings for repair (`BrowserFlowExecutor`). Nothing here
knows the product: it is generic, so it never encodes a demo prompt.
"""
from __future__ import annotations

import json

from .autonomous_core import AcceptanceFailure, ExecutionReport

BROWSER_FAILURE_ID = 'BROWSER'
BROWSER_PROFILE = 'browser'

# Runs inside the sandbox. Kept free of omni_prod imports.
PROBE = r'''
import json, os, subprocess, sys, time, urllib.request
from datetime import date, timedelta
c = json.load(open(".omni/project.json"))
port = int(c["port"])
env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = "http://127.0.0.1:%d" % port
out = {"page_errors": [], "server_errors": [], "forms": [], "findings": []}
def finding(kind, message):
    out["findings"].append({"kind": kind, "message": message[:400]})
for _ in range(60):
    try:
        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
    except Exception:
        time.sleep(0.5)
from playwright.sync_api import sync_playwright
VISIBLE = """() => { let n = 0; for (const el of document.querySelectorAll('body *')) {
  el.dataset.omniSeen = String(n++); } }"""
REVEALED = """(before) => { const out = [];
  for (const el of document.querySelectorAll('[data-omni-seen]')) {
    const id = el.dataset.omniSeen; const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    const vis = s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05 && r.width > 0 && r.height > 0;
    const text = (el.innerText || '').trim();
    if (vis && text && before.indexOf(id) >= 0 && !el.closest('table, ul, ol, form')) out.push(text.slice(0, 80));
  } return out; }"""
HIDDEN = """() => { const out = [];
  for (const el of document.querySelectorAll('[data-omni-seen]')) {
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (s.display === 'none' || s.visibility === 'hidden' || r.width === 0 || r.height === 0) out.push(el.dataset.omniSeen);
  } return out; }"""
FILL = """(args) => { const [formIndex, round] = args; const f = document.forms[formIndex]; if (!f) return 0;
  const day = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
  let filled = 0;
  for (const el of f.elements) {
    if (el.disabled || el.type === 'hidden' || el.type === 'submit' || el.type === 'button') continue;
    const key = ((el.name || '') + ' ' + (el.id || '') + ' ' + (el.placeholder || '')).toLowerCase();
    let v = null;
    if (el.tagName === 'SELECT') { const o = [...el.options].find(o => o.value && !o.disabled); if (o) v = o.value; }
    else if (el.type === 'checkbox' || el.type === 'radio') { if (el.required) { el.checked = true; filled++; } continue; }
    else if (el.type === 'number' || el.type === 'range') { const lo = el.min !== '' ? Number(el.min) : 1; const hi = el.max !== '' ? Number(el.max) : lo + 10;
      v = String(Math.min(hi, Math.max(lo, lo + 1 + round))); if (/year|שנה/.test(key)) v = String(Math.min(hi, Math.max(lo, 2001 + round))); }
    else if (el.type === 'date') v = day(2 + round);
    else if (el.type === 'time') v = (10 + round) + ':00';
    else if (el.type === 'datetime-local') v = day(2 + round) + 'T1' + round + ':00';
    else if (el.type === 'email' || /mail/.test(key)) v = 'user' + round + '@example.com';
    else if (el.type === 'tel' || /phone|tel|טלפון|נייד/.test(key)) v = '05012345' + (10 + round);
    else if (el.type === 'url') v = 'https://example.com/' + round;
    else if (el.type === 'color') v = '#336699';
    else if (el.type === 'password') v = 'Passw0rd-' + round;
    else v = 'בדיקה ' + (round + 1);
    if (v !== null) { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); filled++; }
  } return filled; }"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    page = b.new_page(viewport={"width": 1280, "height": 900}, locale="he-IL")
    page.on("pageerror", lambda e: out["page_errors"].append(str(e)[:300]))
    reqs = []
    def on_resp(r):
        if r.url.startswith(base):
            reqs.append((r.request.method, r.url[len(base):], r.status))
            if r.status >= 500:
                out["server_errors"].append("%s %s -> %s" % (r.request.method, r.url[len(base):], r.status))
    page.on("response", on_resp)
    page.goto(base + "/", wait_until="load", timeout=15000)
    page.wait_for_timeout(1500)
    nforms = min(page.evaluate("() => document.forms.length"), 5)
    for i in range(nforms):
        rounds = []
        for rnd in range(2):
            page.evaluate(VISIBLE)
            hidden = page.evaluate(HIDDEN)
            text_before = page.evaluate("() => document.body.innerText")
            page.evaluate(FILL, [i, rnd])
            mark = len(reqs)
            submitted = page.evaluate("""(i) => { const f = document.forms[i]; if (!f) return false;
              const btn = f.querySelector('[type=submit], button:not([type])');
              if (btn) { btn.click(); return true; }
              if (f.requestSubmit) { f.requestSubmit(); return true; } return false; }""", i)
            page.wait_for_timeout(1500)
            new = reqs[mark:]
            writes = [r for r in new if r[0] != "GET"]
            ok_write = any(200 <= r[2] < 300 for r in writes)
            changed = page.evaluate("() => document.body.innerText") != text_before
            revealed = page.evaluate(REVEALED, hidden)
            rounds.append({"submitted": submitted, "requests": ["%s %s %s" % r for r in new][:6],
                           "ok_write": ok_write, "text_changed": changed, "revealed": revealed[:3]})
            if rnd == 0:
                page.wait_for_timeout(6000)  # let transient messages time out, like a person reading
        fid = page.evaluate("(i) => { const f = document.forms[i]; return f ? (f.id || f.getAttribute('name') || ('form ' + (i + 1))) : ''; }", i)
        out["forms"].append({"form": fid, "rounds": rounds})
        first, second = rounds[0], rounds[1]
        if first["submitted"] and not first["requests"] and not first["text_changed"]:
            finding("dead_form", "form %r: submitting it sent no request and changed nothing on the page" % fid)
        elif first["revealed"] and second["ok_write"] and not second["revealed"]:
            finding("feedback_disappears", "form %r: the first submit showed %r, the second successful submit showed no message at all "
                    "(an element hidden after the first message is never shown again)" % (fid, first["revealed"][0]))
    b.close()
srv.terminate()
for e in out["page_errors"][:3]:
    finding("page_error", "uncaught JavaScript error: " + e)
for e in out["server_errors"][:3]:
    finding("server_error", "server error during the browser flow: " + e)
print("OMNI_BROWSER_PROBE " + json.dumps(out, ensure_ascii=False))
'''

BLOCKING = ('page_error', 'dead_form', 'feedback_disappears', 'server_error')


def parse_probe_output(stdout: str) -> dict | None:
    for line in reversed((stdout or '').splitlines()):
        if line.startswith('OMNI_BROWSER_PROBE '):
            try:
                return json.loads(line[len('OMNI_BROWSER_PROBE '):])
            except ValueError:
                return None
    return None


class BrowserFlowExecutor:
    """After the checks, tests, preview smoke and quality gate pass, click
    through the product in a real browser. Blocking findings become a
    repairable BROWSER failure with the exact observation. If the browser
    sandbox is not available the build is not failed for that reason: the
    report records `browser_check: unavailable` so nobody reads it as passed."""

    def __init__(self, inner, *, enabled: bool = True):
        self._inner = inner
        self._enabled = enabled
        self.last_probe: dict | None = None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed or not self._enabled:
            return report
        run = getattr(self._inner, '_run', None)
        if not callable(run):
            self.last_probe = {'status': 'unavailable', 'reason': 'no sandbox runner'}
            return report
        try:
            result = run(repository, ('python', '-c', PROBE), 'browser-probe', profile=BROWSER_PROFILE)
        except TypeError:
            self.last_probe = {'status': 'unavailable', 'reason': 'sandbox runner has no browser profile'}
            return report
        except Exception as exc:
            self.last_probe = {'status': 'unavailable', 'reason': f'{type(exc).__name__}: {exc}'[:300]}
            return report
        probe = parse_probe_output(str(result.get('stdout', '')))
        if probe is None:
            tail = (str(result.get('stdout', '')) + str(result.get('stderr', '')))[-600:]
            self.last_probe = {'status': 'unavailable', 'reason': 'probe produced no result', 'tail': tail}
            return report
        blocking = [f for f in probe.get('findings', []) if f.get('kind') in BLOCKING]
        self.last_probe = {'status': 'failed' if blocking else 'passed', 'forms': len(probe.get('forms', [])),
                           'findings': probe.get('findings', [])}
        if not blocking:
            return report
        message = 'the product misbehaves in a real browser: ' + '; '.join(f['message'] for f in blocking[:4])
        detail = ('A headless browser opened "/", filled every form with plausible values and submitted it twice. '
                  'Fix the page so every action gives visible feedback every time (do not leave a message element '
                  'permanently hidden after its first use), and so no JavaScript error is thrown.\n'
                  + json.dumps(probe.get('forms', [])[:4], ensure_ascii=False)[:1500])
        return ExecutionReport(False, (AcceptanceFailure(BROWSER_FAILURE_ID, message, detail),),
                               report.build_log + '\n' + message)
