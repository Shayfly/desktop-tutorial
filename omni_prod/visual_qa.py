"""Visual quality engineering (Production Assurance v2 §6; issue #6 P1 "Visual QA").

For each viewport (desktop 1440x900, mobile 390x844 with touch) the product is
started inside the browser sandbox (no network, headless Chromium, the same
start contract as the preview), "/" is opened in its initial (empty) state and
a DOM audit runs. Findings are measured, never inferred from pixels alone:

  no_mobile_viewport mobile: no meta viewport, the phone shows the page zoomed out
  h_overflow        the page scrolls sideways (wider than the viewport)
  offscreen_control a button/link/field lies outside the viewport horizontally
  overlap           two visible controls cover each other
  clipped_text      text cut by its box (overflow hidden, content wider)
  small_touch       mobile: a control smaller than 24x24 CSS px (WCAG 2.2 AA 2.5.8)
  broken_image      an <img> that failed to load
  unnamed_control   a button/link with no accessible name
  unlabelled_field  a form field with no label / aria-label / title
  low_contrast      text below WCAG AA contrast (4.5:1, 3:1 for large text)
  tiny_text         mobile: text under 12px
  missing_lang      <html> has no lang
  rtl_mismatch      mostly-Hebrew page not rendered right-to-left
  positive_tabindex tabindex > 0 (breaks keyboard order)
  console_error     console error or uncaught exception on load

Screenshots (JPEG) are returned for evidence and stored by the caller; they
are never sent to any third party. Only rules proven free of false positives on
stored working products block (DEFAULT_ENFORCED; OMNI_VISUAL_QA_ENFORCE
overrides, '' = shadow); the rest are recorded as advisories.
"""
from __future__ import annotations

import base64
import json
import os

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .browser_probe import BROWSER_PROFILE
from .sandbox_script import staged_script

VISUAL_FAILURE_ID = 'VISUAL'
VIEWPORTS = {'desktop': {'width': 1440, 'height': 900, 'mobile': False},
             'mobile': {'width': 390, 'height': 844, 'mobile': True}}
RULES = ('no_mobile_viewport', 'h_overflow', 'offscreen_control', 'overlap', 'clipped_text', 'small_touch', 'broken_image', 'unnamed_control',
         'unlabelled_field', 'low_contrast', 'tiny_text', 'missing_lang', 'rtl_mismatch', 'positive_tabindex',
         'console_error')

# Runs inside the sandbox; argv[1] = viewport name. Free of omni_prod imports.
SCRIPT = r'''
import base64, json, os, subprocess, sys, time, urllib.request
VIEW = {"desktop": (1440, 900, False), "mobile": (390, 844, True)}[sys.argv[1]]
c = json.load(open(".omni/project.json"))
port = int(c["port"])
env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = "http://127.0.0.1:%d" % port
for _ in range(60):
    try:
        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
    except Exception:
        time.sleep(0.5)
AUDIT = r"""(mobile) => {
  const F = [];
  const add = (kind, el, detail) => F.push({kind, detail: (detail || '').slice(0, 160),
      at: el ? (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '')) : ''});
  const vw = window.innerWidth, vh = window.innerHeight;
  const vis = (el) => { const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05 && r.width > 0 && r.height > 0; };
  const doc = document.documentElement;
  if (mobile && vw > screen.width + 2) add('no_mobile_viewport', null, 'layout width ' + vw + 'px on a ' + screen.width + 'px phone (no meta viewport): the page is shown zoomed out');
  if (doc.scrollWidth > vw + 2) add('h_overflow', null, 'page width ' + doc.scrollWidth + 'px > viewport ' + vw + 'px');
  if (!doc.getAttribute('lang')) add('missing_lang', doc, '');
  const text = document.body ? document.body.innerText : '';
  const heb = (text.match(/[֐-׿]/g) || []).length, lat = (text.match(/[A-Za-z]/g) || []).length;
  if (heb > 20 && heb > lat && getComputedStyle(document.body).direction !== 'rtl') add('rtl_mismatch', document.body, 'Hebrew text rendered ' + getComputedStyle(document.body).direction);
  const controls = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button]')].filter(vis);
  for (const el of controls) {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 2 || r.left < -2) add('offscreen_control', el, 'x ' + Math.round(r.left) + '..' + Math.round(r.right));
    if (mobile && (r.width < 24 || r.height < 24) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
      add('small_touch', el, Math.round(r.width) + 'x' + Math.round(r.height));
    const name = (el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('aria-labelledby') || '').trim();
    if ((el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') && !name && !(el.innerText || '').trim()
        && !el.querySelector('img[alt]:not([alt=""]), svg title')) add('unnamed_control', el, '');
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) && !['submit', 'button', 'reset', 'image'].includes(el.type)) {
      const labelled = name || el.closest('label') || (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]'));
      if (!labelled) add('unlabelled_field', el, el.getAttribute('placeholder') ? 'placeholder only' : '');
    }
    if (parseInt(el.getAttribute('tabindex') || '0', 10) > 0) add('positive_tabindex', el, el.getAttribute('tabindex'));
  }
  const boxes = controls.slice(0, 80).map(el => [el, el.getBoundingClientRect()]);
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const [a, ra] = boxes[i], [b, rb] = boxes[j];
    if (a.contains(b) || b.contains(a)) continue;
    const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (w > 4 && h > 4) add('overlap', a, 'overlaps ' + b.tagName.toLowerCase() + ' by ' + Math.round(w) + 'x' + Math.round(h));
  }
  for (const img of document.querySelectorAll('img')) if (img.complete && img.naturalWidth === 0 && vis(img)) add('broken_image', img, img.getAttribute('src') || '');
  const lum = (c) => { const m = c.match(/[\d.]+/g); if (!m) return null; const [r, g, b] = m.slice(0, 3).map(v => { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const alpha = (c) => { const m = c.match(/[\d.]+/g); return m && m.length > 3 ? parseFloat(m[3]) : 1; };
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null; if (alpha(s.backgroundColor) > 0.9) return s.backgroundColor; } return 'rgb(255, 255, 255)'; };
  let checked = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (checked > 300) break;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || !vis(el)) continue;
    checked++;
    const s = getComputedStyle(el), size = parseFloat(s.fontSize), bold = parseInt(s.fontWeight, 10) >= 700;
    if (mobile && size < 12) add('tiny_text', el, size + 'px');
    if (el.scrollWidth > el.clientWidth + 2 && ['hidden', 'clip'].includes(s.overflowX) && el.children.length === 0) add('clipped_text', el, el.innerText.slice(0, 60));
    const bg = bgOf(el); if (!bg) continue;
    const L1 = lum(s.color), L2 = lum(bg); if (L1 === null || L2 === null || alpha(s.color) < 0.5) continue;
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const need = (size >= 24 || (bold && size >= 18.66)) ? 3 : 4.5;
    if (ratio < need) add('low_contrast', el, ratio.toFixed(2) + ':1 (needs ' + need + ')');
  }
  return {findings: F, text_elements: checked, controls: controls.length, scroll_width: doc.scrollWidth};
}"""
out = {"viewport": sys.argv[1], "console": [], "findings": [], "screenshot": None}
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    ctx = b.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, is_mobile=VIEW[2], has_touch=VIEW[2],
                        device_scale_factor=1, locale="he-IL")
    page = ctx.new_page()
    # "Failed to load resource" console lines are replaced by the exact failed
    # request below; the browser's own /favicon.ico probe is not the product's.
    page.on("console", lambda m: m.type == "error" and not m.text.startswith("Failed to load resource")
            and out["console"].append(m.text[:200]))
    def on_resp(r):
        if r.status >= 400 and r.url.startswith(base) and not r.url.split("?")[0].endswith("/favicon.ico"):
            out["console"].append(("%s %s -> %s" % (r.request.method, r.url[len(base):], r.status))[:200])
    page.on("response", on_resp)
    page.on("pageerror", lambda e: out["console"].append(("uncaught: " + str(e))[:200]))
    page.goto(base + "/", wait_until="load", timeout=15000)
    page.wait_for_timeout(1200)
    audit = page.evaluate(AUDIT, VIEW[2])
    out.update(audit)
    for q in (50, 30, 15):
        shot = page.screenshot(type="jpeg", quality=q, full_page=False)
        if len(shot) * 4 // 3 < 70000:
            out["screenshot"] = base64.b64encode(shot).decode()
            break
    b.close()
srv.terminate()
for e in out["console"][:5]:
    out["findings"].append({"kind": "console_error", "detail": e, "at": ""})
shot = out.pop("screenshot")
if shot:
    print("OMNI_VISUAL_SHOT " + shot)
print("OMNI_VISUAL_QA " + json.dumps(out, ensure_ascii=False))
'''


def parse(stdout: str) -> tuple[dict | None, bytes | None]:
    report, shot = None, None
    for line in str(stdout).splitlines():
        if line.startswith('OMNI_VISUAL_QA '):
            try:
                report = json.loads(line[len('OMNI_VISUAL_QA '):])
            except ValueError:
                report = None
        elif line.startswith('OMNI_VISUAL_SHOT '):
            try:
                shot = base64.b64decode(line[len('OMNI_VISUAL_SHOT '):], validate=True)
            except (ValueError, base64.binascii.Error):
                shot = None
    return report, shot


# Enforced by default: layout rules with 0 findings on the 5 working stored
# products x 2 viewports (verify-replay 38082307056) -- no false positives.
# Contrast/labels found real WCAG defects in 3 of 5 working products; they stay
# advisory until the founder decides the cost/quality trade-off.
DEFAULT_ENFORCED = ('no_mobile_viewport', 'h_overflow', 'offscreen_control', 'overlap', 'broken_image')


def enforced_rules() -> set[str]:
    raw = os.getenv('OMNI_VISUAL_QA_ENFORCE')
    if raw is None:
        return set(DEFAULT_ENFORCED)
    return {r.strip() for r in raw.split(',') if r.strip() in RULES}


class VisualQAExecutor:
    """Runs after the inner chain passed. Records per-viewport findings and
    screenshots (`last_visual`; screenshots go to `screenshot_sink(viewport,
    jpeg_bytes) -> key` when set). Blocks only on rules listed in
    OMNI_VISUAL_QA_ENFORCE (shadow mode otherwise)."""

    def __init__(self, inner, *, enabled: bool = True):
        self._inner = inner
        self._enabled = enabled
        self.screenshot_sink = None
        self.last_visual: dict | None = None
        self.visual_rounds: list[dict] = []

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        return self.check(repository=repository, spec=spec, report=report)

    def check(self, *, repository, spec, report):
        """This stage's own check on a report in which everything before it passed (VerificationGroup runs it
        directly; execute() keeps the standalone short-circuit)."""
        if not self._enabled:
            return report
        from .verification_verdict import no_checks, reraise_control, unverified
        run = getattr(self._inner, '_run', None)
        if not callable(run):
            self.last_visual = {'status': 'NOT_RUN', 'reason': 'no sandbox runner'}
            return unverified(VISUAL_FAILURE_ID, 'no sandbox runner', report.build_log)        # T4: never a pass
        viewports, status = {}, 'PASS'
        for name in VIEWPORTS:
            try:
                staged, argv = staged_script(repository, 'visual_qa', SCRIPT, name)
                result = run(staged, argv, f'visual-{name}', profile=BROWSER_PROFILE)
            except Exception as exc:
                reraise_control(exc)                   # T4: cancel / ledger / budget stop the build
                viewports[name] = {'status': 'NOT_RUN', 'reason': f'{type(exc).__name__}: {exc}'[:200]}
                status = 'NOT_RUN'
                continue
            data, shot = parse(result.get('stdout', ''))
            if data is not None and not (isinstance(data, dict) and isinstance(data.get('findings'), list)):
                viewports[name] = {'status': 'NOT_RUN', 'reason': 'malformed visual report'}   # T4: schema first
                status = 'NOT_RUN'
                continue
            if data is not None and int(result.get('returncode', 0) or 0) != 0:
                viewports[name] = {'status': 'NOT_RUN', 'reason': f"visual QA exited {result.get('returncode')}"}
                status = 'NOT_RUN'
                continue
            if data is None:
                viewports[name] = {'status': 'NOT_RUN', 'reason': 'no visual report',
                                   'tail': (str(result.get('stdout', '')) + str(result.get('stderr', '')))[-300:]}
                status = 'NOT_RUN'
                continue
            entry = {'status': 'PASS' if not data['findings'] else 'FINDINGS', 'findings': data['findings'][:40],
                     'counts': _counts(data['findings']), 'controls': data.get('controls'),
                     'text_elements': data.get('text_elements'), 'screenshot_bytes': len(shot) if shot else 0}
            if shot and self.screenshot_sink is not None:
                try:
                    entry['screenshot_key'] = self.screenshot_sink(name, shot)
                except Exception as exc:  # evidence storage must not change the outcome
                    entry['screenshot_error'] = type(exc).__name__
            viewports[name] = entry
        enforce = enforced_rules()
        blocking = [(v, f) for v, e in viewports.items() for f in e.get('findings', []) if f['kind'] in enforce]
        if status == 'NOT_RUN' and not blocking:       # T4: a viewport that was not inspected verified nothing
            self.last_visual = {'status': 'NOT_RUN', 'mode': 'enforce' if enforce else 'shadow', 'viewports': viewports}
            self.visual_rounds.append({'status': 'NOT_RUN', 'counts': {}})
            why = '; '.join(f"{v}: {e.get('reason')}" for v, e in viewports.items() if e.get('status') == 'NOT_RUN')
            return unverified(VISUAL_FAILURE_ID, why, report.build_log)
        inspected = sum(int(e.get('controls') or 0) + int(e.get('text_elements') or 0) for e in viewports.values())
        if not blocking and inspected == 0 and not any(e.get('findings') for e in viewports.values()):
            self.last_visual = {'status': 'NO_CHECKS', 'mode': 'enforce' if enforce else 'shadow', 'viewports': viewports}
            self.visual_rounds.append({'status': 'NO_CHECKS', 'counts': {}})
            return no_checks(VISUAL_FAILURE_ID, 'no control and no text element was inspected', report.build_log)
        if status == 'PASS' and any(e.get('findings') for e in viewports.values()):
            status = 'FINDINGS'
        self.last_visual = {'status': 'FAIL' if blocking else status, 'mode': 'enforce' if enforce else 'shadow',
                            'enforced_rules': sorted(enforce), 'viewports': viewports}
        self.visual_rounds.append({'status': self.last_visual['status'],
                                   'counts': {v: e.get('counts', {}) for v, e in viewports.items()}})
        if not blocking:
            return report
        failures = tuple(AcceptanceFailure(VISUAL_FAILURE_ID, f"visual ({v}) {f['kind']}: {f['at']} {f['detail']}".strip(),
                                           'Fix the layout so it works on desktop (1440x900) and mobile (390x844).')
                         for v, f in blocking[:8])
        return ExecutionReport(False, failures, report.build_log)


def _counts(findings) -> dict:
    out: dict[str, int] = {}
    for f in findings:
        out[f['kind']] = out.get(f['kind'], 0) + 1
    return out
