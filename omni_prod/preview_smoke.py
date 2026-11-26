"""Verification that the product can actually be previewed.

Golden E2E #1 (2026-10-07): the football site passed its tests, quality and
review, then the preview said "preview contract requires schema_version 2,
got None" -- nothing had ever checked that the product declares how to start,
let alone that it starts. After the acceptance checks pass, this executor
requires a valid preview contract and, for the Python runtime, starts the app
inside the same isolated sandbox (read-only source, no network, loopback only)
and waits for its health path. A failure is a repairable PREVIEW failure with
the exact reason, so the repair loop fixes it before anyone sees the product.
"""
from __future__ import annotations

import json

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .preview_runtime import NotPreviewable, parse_preview_contract
from .sandbox_script import staged_script

PREVIEW_FAILURE_ID = 'PREVIEW'
SMOKE_SECONDS = 20

PREVIEW_SHAPE = (
    'The preview contract lives in the same .omni/project.json as top-level keys: "schema_version": 2, '
    '"runtime": "python:3.11-slim", "start": ["python", "app.py"] (an argv array run from the repository root), '
    '"port": 8000, "health_path": "/". The server must read the PORT environment variable, listen on 0.0.0.0, '
    'use only the Python standard library (no install step runs), write only under /tmp (the rest is '
    'read-only), and answer HTTP 200 on health_path within a few seconds of starting. GET / must return the '
    'product\'s full user interface as an HTML page (Content-Type text/html) with real controls (forms, '
    'buttons, tables) wired to the app\'s JSON endpoints -- never a placeholder or a health string. '
    'Image files under assets/ must be served at GET /assets/<name> with their bytes (read in binary mode) and their '
    'Content-Type (image/webp, image/jpeg, image/png).'
)

# Runs inside the sandbox. Starts the declared server, polls its health path.
_SMOKE = r'''
import json, os, subprocess, sys, time, urllib.request, urllib.error
c = json.load(open(".omni/project.json"))
port, path = int(c["port"]), c.get("health_path", "/")
env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
deadline, verdict = time.time() + %(seconds)d, "no answer within %(seconds)ds"
while time.time() < deadline:
    if p.poll() is not None:
        verdict = "server exited with code %%s before answering" %% p.returncode
        break
    try:
        with urllib.request.urlopen("http://127.0.0.1:%%d%%s" %% (port, path), timeout=2) as r:
            verdict = "OK" if 200 <= r.status < 400 else "HTTP %%s" %% r.status
        break
    except urllib.error.HTTPError as e:
        verdict = "health_path answered HTTP %%s" %% e.code
        break
    except Exception:
        time.sleep(0.5)
if verdict == "OK":
    # The product is a website: "/" must serve its real user interface, not a
    # health string (Golden E2E #1: "/" answered "OK" and the UI did not exist).
    try:
        with urllib.request.urlopen("http://127.0.0.1:%%d/" %% port, timeout=3) as r:
            ctype, page = r.headers.get("Content-Type", ""), r.read(200000).decode("utf-8", "replace")
            base = r.geturl()
        low = page.lower()
        # The UI may live in same-origin scripts/styles the page loads
        # (bld_78e26994: a 382-char page was rejected without looking at them).
        import re
        assets = ""
        for ref in re.findall(r"""<(?:script[^>]*\ssrc|link[^>]*\shref)\s*=\s*["']([^"'#?]+)""", page, re.I)[:6]:
            if "//" in ref:
                continue
            try:
                with urllib.request.urlopen("http://127.0.0.1:%%d/%%s" %% (port, ref.lstrip("./")), timeout=3) as a:
                    assets += a.read(200000).decode("utf-8", "replace")
            except Exception:
                pass
        whole = low + assets.lower()
        controls = ("<form", "<input", "<button", "<table", "<select", "<textarea",
                    "createelement('button", 'createelement("button', "createelement('input", 'createelement("input',
                    "createelement('table", 'createelement("table')
        # A website/landing page is real UI without form controls (2026-11-09: a café page whose only action is a
        # WhatsApp link was rejected 6 rounds as "placeholder"): headings plus real visible text also count.
        visible = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", page)
        content_site = len(" ".join(visible.split())) >= 300 and ("<h1" in low or "<h2" in low)
        if "text/html" not in ctype.lower() or ("<html" not in low and "<!doctype" not in low):
            verdict = "GET / did not return an HTML page (Content-Type %%r, starts %%r)" %% (ctype, page[:60])
        elif not content_site and (len(page.strip()) + len(assets.strip()) < 400 or not any(t in whole for t in controls)):
            verdict = ("GET / returned a placeholder page, not the product's user interface "
                       "(%%d chars of HTML, %%d chars of linked scripts/styles; starts %%r)" %% (len(page.strip()), len(assets.strip()), page.strip()[:160]))
    except Exception as e:
        verdict = "GET / failed: %%s" %% e
names = []
if verdict == "OK":
    # Warehouse 118: the images the platform carries are files under assets/ (the runner wrote their bytes). The
    # product's server must serve each one at /assets/<name>: 200, the image's Content-Type, the same bytes.
    import hashlib
    kinds = {".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    names = sorted(os.listdir("assets"))[:50] if os.path.isdir("assets") else []
    for name in names:
        want = kinds.get(os.path.splitext(name)[1].lower())
        if not want or not os.path.isfile(os.path.join("assets", name)):
            continue
        body = open(os.path.join("assets", name), "rb").read()
        if not ((want == "image/webp" and body[:4] == b"RIFF" and body[8:12] == b"WEBP")
                or (want == "image/jpeg" and body[:3] == b"\xff\xd8\xff")
                or (want == "image/png" and body[:8] == b"\x89PNG\r\n\x1a\n")):
            verdict = "assets/%%s is not a %%s file in the work directory (%%d bytes)" %% (name, want, len(body))
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:%%d/assets/%%s" %% (port, name), timeout=3) as a:
                got, ctype = a.read(len(body) + 1), a.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            verdict = "GET /assets/%%s answered HTTP %%s: the server must serve the image files under assets/" %% (name, e.code)
            break
        except Exception as e:
            verdict = "GET /assets/%%s failed: %%s" %% (name, e)
            break
        if not ctype.lower().startswith(want):
            verdict = "GET /assets/%%s answered Content-Type %%r, not %%s" %% (name, ctype, want)
            break
        if hashlib.sha256(got).hexdigest() != hashlib.sha256(body).hexdigest():
            verdict = ("GET /assets/%%s answered %%d bytes that are not the image file (%%d bytes): serve it in "
                       "binary mode" %% (name, len(got), len(body)))
            break
if verdict == "OK" and names:
    # Warehouse 118 (review 2026-11-21): /assets/<name> answering is not enough. The page's reference is relative, so
    # it resolves against the URL of the document (after a redirect of GET /) or of the stylesheet that holds it. Every
    # carried-image reference in the page and in its same-origin stylesheets is resolved the way a browser does and
    # fetched: 200, the image's Content-Type, the same bytes -- else the user sees a broken image and the smoke says so.
    import re, urllib.parse
    origin = "http://127.0.0.1:%%d/" %% port
    carried = re.compile(r"assets/148ai-[a-z]{2,12}(?:-[0-9]{1,3})?\.(?:webp|jpe?g|png)", re.I)
    def references(text):
        # the whole reference: the name plus what is written before it (../, /, a host), at most 200 characters back.
        # Found from the name backwards so that a long token (an inline data: URI) costs nothing.
        found = []
        for m in list(carried.finditer(text))[:50]:
            i = m.start()
            while i > 0 and m.start() - i < 200 and text[i - 1] not in " \t\r\n\"'`()<>=,;":
                i -= 1
            found.append(text[i:m.end()])
        return found
    sources = [(base, page)]
    for ref in re.findall(r"""<link[^>]*\shref\s*=\s*["']([^"'#?]+\.css)""", page, re.I)[:6]:
        u = urllib.parse.urljoin(base, ref)
        if u.startswith(origin):
            try:
                with urllib.request.urlopen(u, timeout=3) as a:
                    sources.append((a.geturl(), a.read(200000).decode("utf-8", "replace")))
            except Exception:
                pass
    seen, checked = set(), 0
    for src_url, text in sources:
        for ref in references(text):
            u = urllib.parse.urljoin(src_url, ref)
            if u in seen:
                continue
            seen.add(u)
            name = ref.rsplit("/", 1)[-1]
            if name not in names:
                verdict = "%%s references %%s but assets/%%s is not in the work directory" %% (src_url, ref, name)
                break
            if not u.startswith(origin):
                verdict = "%%s references %%s, which resolves off the product (%%s)" %% (src_url, ref, u)
                break
            body = open(os.path.join("assets", name), "rb").read()
            want = kinds.get(os.path.splitext(name)[1].lower())
            try:
                with urllib.request.urlopen(u, timeout=3) as a:
                    got, ctype = a.read(len(body) + 1), a.headers.get("Content-Type", "")
            except Exception as e:
                verdict = ("%%s references %%s, which resolves to %%s and failed (%%s): the visitor sees a broken "
                           "image. Serve the page at / and the stylesheet from a URL that mirrors its file path, "
                           "or serve the image at that URL too" %% (src_url, ref, u, e))
                break
            if not ctype.lower().startswith(want or "image/") or got != body:
                verdict = ("%%s references %%s, which resolves to %%s and answered Content-Type %%r with %%d bytes, "
                           "not the %%s file (%%d bytes)" %% (src_url, ref, u, ctype, len(got), want, len(body)))
                break
            checked += 1
        if verdict != "OK":
            break
    if verdict == "OK":
        # printed only now: on a failure the first line of the output is the verdict, which is what the repair reads
        print("PREVIEW-ASSETS " + json.dumps(names))
        print("PREVIEW-ASSET-REFS %%d" %% checked)
if p.poll() is None:
    p.terminate()
try:
    out = p.communicate(timeout=3)[0] or b""
except Exception:
    p.kill(); out = b""
print("PREVIEW-SMOKE " + verdict)
print(out.decode("utf-8", "replace")[-1500:])
if verdict == "OK":
    # 2026-11-10 (Michael): the gates judge the page the product SERVES, not its source. The rendered page and its
    # same-origin assets go back to the review as the last line (stdout keeps its tail).
    print("PREVIEW-PAGE " + json.dumps({"/": page[:45000], "assets": assets[:20000]}, ensure_ascii=False))
sys.exit(0 if verdict == "OK" else 1)
''' % {'seconds': SMOKE_SECONDS}


SERVED_CUT = 45_000     # _SMOKE prints at most this many characters of GET / (the line rides in the stdout tail)


def served_cut(page):
    """The part of a captured page a check can judge as written. The smoke prints page[:45000], so a longer page
    arrives cut mid-text: a street address, an hours range, a phone or a testimonial split at character 45,000 reads as
    another fact -- 'רחוב הנביאים 1' for 'רחוב הנביאים 12' is an invented address (scan of 2026-11-26, caps-a: a page
    of 88,331 characters cut at 85,892). A page of SERVED_CUT characters or more is trimmed back to the end of its last
    complete </section>, or, when it has none, to before its last tag; a shorter page is returned as it is. Used where
    the content route judges or compares the served page (PreviewReadyExecutor.trim_cut, agents.prepass,
    agents.SiteParityExecutor)."""
    if not isinstance(page, str) or len(page) < SERVED_CUT:
        return page
    cut = page[:SERVED_CUT]
    end = cut.rfind('</section>')
    if end >= 0:
        return cut[:end + len('</section>')]
    tag = cut.rfind('<')
    return cut[:tag] if tag >= 0 else cut


def _rendered_pages(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith('PREVIEW-PAGE '):
            try:
                data = json.loads(line[len('PREVIEW-PAGE '):])
            except ValueError:
                return None
            return data if isinstance(data, dict) and isinstance(data.get('/'), str) else None
    return None


def _failure(message: str, detail: str = '') -> ExecutionReport:
    return ExecutionReport(False, (AcceptanceFailure(PREVIEW_FAILURE_ID, message,
                                                     (detail + '\n' + PREVIEW_SHAPE).strip()),), '')


class PreviewReadyExecutor:
    def __init__(self, inner):
        self._inner = inner
        # What the last run did (release policy: NOT_RUN is not PASS).
        self.last_smoke: dict | None = None
        # The page GET / served in the last passing smoke run, as the user receives it: {'/': html, 'assets': css+js}.
        self.last_pages: dict | None = None
        # The content route (site_content.install) sets this: a captured page cut at SERVED_CUT is trimmed to its last
        # complete section (served_cut) before any check reads it. Off elsewhere: every other route reads it as before.
        self.trim_cut = False

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
        try:
            contract = parse_preview_contract(repository)
        except NotPreviewable as exc:
            self.last_smoke = {'status': 'FAIL', 'reason': str(exc)[:300]}
            failed = _failure(f'the product cannot be previewed: {exc}')
            return ExecutionReport(False, failed.failures, report.build_log)
        run = getattr(self._inner, '_run', None)
        if not contract.runtime.startswith('python') or not callable(run):
            self.last_smoke = {'status': 'NOT_RUN', 'reason': 'no sandbox runtime to start this product'}
            from .verification_verdict import unverified        # T4: NOT_RUN is not PASS (release policy says so too)
            return unverified(PREVIEW_FAILURE_ID, f'no sandbox runtime for {contract.runtime!r}', report.build_log)
        try:
            staged, argv = staged_script(repository, 'preview_smoke', _SMOKE)
            result = run(staged, argv, 'preview-smoke')
        except Exception as exc:  # sandbox unavailable: the build cannot be verified
            from .verification_verdict import reraise_control
            reraise_control(exc)  # T4: cancel / ledger / budget stop the build, they are not a preview result
            self.last_smoke = {'status': 'FAIL', 'reason': f'could not run: {exc}'[:300]}
            return ExecutionReport(False, (AcceptanceFailure(PREVIEW_FAILURE_ID, f'preview smoke test could not run: {exc}'),),
                                   report.build_log)
        if int(result.get('returncode', 1)) == 0:
            self.last_smoke = {'status': 'PASS'}
            self.last_pages = _rendered_pages(str(result.get('stdout', '')))
            if self.trim_cut and self.last_pages:
                self.last_pages = {**self.last_pages, '/': served_cut(self.last_pages['/'])}
            return report
        self.last_pages = None
        self.last_smoke = {'status': 'FAIL'}
        output = (str(result.get('stdout', '')) + str(result.get('stderr', '')))[-1800:]
        first = output.strip().splitlines()[0] if output.strip() else 'no output'
        needs = ''
        if 'user interface' in first or 'HTML page' in first:
            # Rehearsal 2026-10-08: three repair rounds produced 116-139 char
            # pages. Say what the page must let the user do, from the spec.
            texts = [r.text for r in getattr(spec, 'requirements', ())][:8]
            if texts:
                needs = ('GET / must render the whole product for a user: ' + '; '.join(texts) +
                         '. Build it as one complete HTML page (inline CSS and JavaScript allowed) with the forms, '
                         'buttons and tables these need, calling the app\'s JSON endpoints.\n')
        failed = _failure(f'the app did not start for preview: {first}', needs + output)
        return ExecutionReport(False, failed.failures, report.build_log + '\n' + output)
