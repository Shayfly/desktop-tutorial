"""Sign-in form check in a real browser (flag site_auth_v2, work order 001 mapped to 148AI).

Only with the flag on, and only for a product that has a password field. The sign-in page is found the way a visitor
finds it (the home page, then /login, /signin, /auth/login, /account/login). At 320px wide and 140% zoom:
  * the form fits: no sideways scroll, no field or button outside the viewport;
  * every field has a label (a <label for>, a wrapping <label>, or aria-label/aria-labelledby);
  * a wrong sign-in moves focus to a field, and that field's aria-describedby points at a non-empty message.
A failure goes to the repair like any other check (failure id AUTH_FORM). With the flag off this module is not
imported anywhere, so the verification chain is the baseline.
"""
from __future__ import annotations

import json

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .browser_probe import BROWSER_PROFILE
from .sandbox_script import staged_script

AUTH_FORM_FAILURE_ID = 'AUTH_FORM'

SCRIPT = r'''
import json, os, subprocess, sys, time, urllib.request
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
AUDIT = r"""() => {
  const F = [];
  const vw = window.innerWidth;
  const doc = document.documentElement;
  if (doc.scrollWidth > vw + 2) F.push('the sign-in page scrolls sideways at 320px/140%: width ' + doc.scrollWidth + 'px');
  const fields = [...document.querySelectorAll('input:not([type=hidden]), select, textarea')];
  for (const el of fields) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && (r.right > vw + 2 || r.left < -2)) F.push('field ' + (el.name || el.id || el.type) + ' is outside the 320px viewport');
    const named = (el.id && document.querySelector('label[for="' + el.id + '"]')) || el.closest('label') ||
                  el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (!named) F.push('field ' + (el.name || el.id || el.type) + ' has no label');
  }
  for (const b of document.querySelectorAll('button, input[type=submit]')) {
    const r = b.getBoundingClientRect();
    if (r.width > 0 && (r.right > vw + 2 || r.left < -2)) F.push('button "' + (b.innerText || b.value || '').trim().slice(0, 30) + '" is outside the viewport');
  }
  return F;
}"""
AFTER = r"""() => {
  const a = document.activeElement;
  if (!a || !['INPUT', 'SELECT', 'TEXTAREA'].includes(a.tagName)) return 'after a wrong sign-in focus is not on a field (it is on ' + (a ? a.tagName.toLowerCase() : 'nothing') + ')';
  const ids = (a.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
  const text = ids.map(i => (document.getElementById(i) || {}).textContent || '').join(' ').trim();
  if (!text) return 'the focused field ' + (a.name || a.id || a.type) + ' has no aria-describedby message';
  return '';
}"""
out = {"page": None, "findings": []}
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    ctx = b.new_context(viewport={"width": 320, "height": 720}, is_mobile=True, has_touch=True,
                        device_scale_factor=1, locale="he-IL")
    page = ctx.new_page()
    for path in ("/", "/login", "/signin", "/auth/login", "/account/login"):
        try:
            page.goto(base + path, wait_until="load", timeout=10000)
        except Exception:
            continue
        if page.query_selector("input[type=password]"):
            out["page"] = path
            break
    if out["page"]:
        page.evaluate("() => { document.documentElement.style.zoom = '1.4'; }")
        page.wait_for_timeout(300)
        out["findings"] += page.evaluate(AUDIT)
        mail = page.query_selector("input[type=email], input[name*=mail i], input[name*=user i]")
        if mail:
            mail.fill("nobody@example.com")
        page.fill("input[type=password]", "wrong-password-1")
        try:
            with page.expect_response(lambda r: r.request.method == "POST", timeout=5000):
                page.press("input[type=password]", "Enter")
        except Exception:
            pass
        page.wait_for_timeout(800)
        problem = page.evaluate(AFTER)
        if problem:
            out["findings"].append(problem)
    b.close()
srv.terminate()
print("OMNI_AUTH_FORM " + json.dumps(out, ensure_ascii=False))
'''


def has_sign_in(repository: dict) -> bool:
    return any(isinstance(t, str) and ('type="password"' in t or "type='password'" in t or 'type=password' in t)
               for t in repository.values())


def parse(stdout: str) -> dict | None:
    for line in str(stdout).splitlines():
        if line.startswith('OMNI_AUTH_FORM '):
            try:
                data = json.loads(line[len('OMNI_AUTH_FORM '):])
            except ValueError:
                return None
            return data if isinstance(data, dict) and isinstance(data.get('findings'), list) else None
    return None


class AuthFormExecutor:
    def __init__(self, inner):
        self._inner = inner
        self.last_auth_form: dict | None = None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        return report if not report.passed else self.check(repository=repository, spec=spec, report=report)

    def check(self, *, repository, spec, report):
        from .verification_verdict import reraise_control, unverified
        if not has_sign_in(repository):
            self.last_auth_form = {'status': 'NOT_APPLICABLE'}
            return report
        run = getattr(self._inner, '_run', None)
        if not callable(run):
            return unverified(AUTH_FORM_FAILURE_ID, 'no sandbox runner', report.build_log)
        try:
            staged, argv = staged_script(repository, 'auth_form', SCRIPT)
            result = run(staged, argv, 'auth-form', profile=BROWSER_PROFILE)
        except Exception as exc:
            reraise_control(exc)
            return unverified(AUTH_FORM_FAILURE_ID, f'{type(exc).__name__}: {exc}'[:200], report.build_log)
        data = parse(result.get('stdout', ''))
        if data is None or not data.get('page'):
            self.last_auth_form = {'status': 'NOT_RUN', 'data': data}
            return unverified(AUTH_FORM_FAILURE_ID, 'the sign-in page was not found or the check did not report',
                              report.build_log)
        self.last_auth_form = {'status': 'PASS' if not data['findings'] else 'FAIL', **data}
        if not data['findings']:
            return report
        failure = AcceptanceFailure(AUTH_FORM_FAILURE_ID, 'the sign-in form at 320px / 140% zoom: ' +
                                    '; '.join(data['findings'][:6]))
        return ExecutionReport(False, (*report.failures, failure), report.build_log)
