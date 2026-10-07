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

PREVIEW_FAILURE_ID = 'PREVIEW'
SMOKE_SECONDS = 20

PREVIEW_SHAPE = (
    'The preview contract lives in the same .omni/project.json as top-level keys: "schema_version": 2, '
    '"runtime": "python:3.11-slim", "start": ["python", "app.py"] (an argv array run from the repository root), '
    '"port": 8000, "health_path": "/". The server must read the PORT environment variable, listen on 0.0.0.0, '
    'use only the Python standard library (no install step runs), write only under /tmp (the rest is '
    'read-only), and answer HTTP 200 on health_path within a few seconds of starting.'
)

# Runs inside the sandbox. Starts the declared server, polls its health path.
_SMOKE = r'''
import json, os, subprocess, sys, time, urllib.request, urllib.error
c = json.load(open(".omni/project.json"))
port, path = int(c["port"]), c.get("health_path", "/")
env = dict(os.environ, PORT=str(port), HOME="/tmp", PYTHONDONTWRITEBYTECODE="1")
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
if p.poll() is None:
    p.terminate()
try:
    out = p.communicate(timeout=3)[0] or b""
except Exception:
    p.kill(); out = b""
print("PREVIEW-SMOKE " + verdict)
print(out.decode("utf-8", "replace")[-1500:])
sys.exit(0 if verdict == "OK" else 1)
''' % {'seconds': SMOKE_SECONDS}


def _failure(message: str, detail: str = '') -> ExecutionReport:
    return ExecutionReport(False, (AcceptanceFailure(PREVIEW_FAILURE_ID, message,
                                                     (detail + '\n' + PREVIEW_SHAPE).strip()),), '')


class PreviewReadyExecutor:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        try:
            contract = parse_preview_contract(repository)
        except NotPreviewable as exc:
            failed = _failure(f'the product cannot be previewed: {exc}')
            return ExecutionReport(False, failed.failures, report.build_log)
        run = getattr(self._inner, '_run', None)
        if not contract.runtime.startswith('python') or not callable(run):
            return report  # contract valid; no sandbox runtime to start it in here
        try:
            result = run(repository, ('python', '-c', _SMOKE), 'preview-smoke')
        except Exception as exc:  # sandbox unavailable: the build cannot be verified
            return ExecutionReport(False, (AcceptanceFailure(PREVIEW_FAILURE_ID, f'preview smoke test could not run: {exc}'),),
                                   report.build_log)
        if int(result.get('returncode', 1)) == 0:
            return report
        output = (str(result.get('stdout', '')) + str(result.get('stderr', '')))[-1800:]
        first = output.strip().splitlines()[0] if output.strip() else 'no output'
        failed = _failure(f'the app did not start for preview: {first}', output)
        return ExecutionReport(False, failed.failures, report.build_log + '\n' + output)
