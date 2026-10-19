"""Behavioural acceptance inside the build, feeding the repair loop.

Autonomous completion directive §1 (real-server finding 2026-10-09): the
booking app bld_fde8abb01e4d4085aa180282e6026fb4 reached READY, passed the
browser check, and only *after* delivery its behavioural acceptance found
that creating an appointment returned HTTP 400. Acceptance was a report, not
a gate.

This executor runs the product's behavioural acceptance plan (the
`web_saas_acceptance` block of .omni/project.json) against the app started
inside the same isolated sandbox (read-only source, no network, loopback
only, data under /tmp), using the same `WebSaaSAcceptanceRunner` code the
preview uses (its source is shipped into the sandbox; it is stdlib-only).
The scope of what must pass comes from the approved contract
(requirements-aware: no sign-in -> no auth/role checks; editing/removal
only when promised).

A failure is a repairable BEHAVIOR failure carrying, per failed step, the
request that was sent, the status and an excerpt of the answer, what was
expected and the server's log tail. The acceptance criteria themselves (the
contract's acceptance IDs and the required behaviour kinds) are fixed: the
repair can change the code or correct a wrong test step, but a plan that
drops coverage still fails (missing IDs/kinds).
"""
from __future__ import annotations

import json
from pathlib import Path

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .sandbox_script import staged_script

BEHAVIOR_FAILURE_ID = 'BEHAVIOR'
_RUNNER_SOURCE = (Path(__file__).with_name('web_saas_acceptance.py')).read_text(encoding='utf-8')

PLAN_SHAPE = (
    'The behavioural acceptance plan lives in .omni/project.json under "web_saas_acceptance": '
    '{"product_family": "managed_web_saas_v1", "required_kinds": [...], "personas": [{"id": "...", "steps": '
    '[{"id": "s1", "kind": "data_create", "acceptance_ids": ["A1"], "method": "POST", "path": "/api/...", '
    '"json": {...}, "expect_status": 201, "capture": {"created_id": "id"}}, ...]}]}. Every step runs against the '
    'real app over HTTP; dates in test data must be valid for the app\'s own rules (e.g. from today on): write them as ${today} / ${date_plus_N}, never a fixed date, and never special-case test values in the app.'
)

# Runs inside the sandbox: start the app, run the plan with the shipped runner.
_SCRIPT = r'''
import json, os, subprocess, sys, time, types, urllib.request
cfg = json.load(open(".omni/_behavior_run.json"))
mod = types.ModuleType("wsa"); mod.__dict__["__name__"] = "wsa"
sys.modules["wsa"] = mod
exec(compile(cfg["runner"], "web_saas_acceptance.py", "exec"), mod.__dict__)
c = json.load(open(".omni/project.json"))
port, path = int(c["port"]), c.get("health_path", "/")
import tempfile
scratch = (os.environ.get("OMNI_SCRATCH_DIR") or tempfile.gettempdir())
data_dir = tempfile.mkdtemp(prefix="behavior-", dir=scratch)  # fresh, scratch data for every run
env = dict(os.environ, PORT=str(port), HOME=scratch, DATA_DIR=data_dir, PYTHONDONTWRITEBYTECODE="1")
p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
ok, deadline = False, time.time() + 20
while time.time() < deadline and p.poll() is None:
    try:
        urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2); ok = True; break
    except urllib.error.HTTPError:
        ok = True; break
    except Exception:
        time.sleep(0.4)
if ok:
    runner = mod.WebSaaSAcceptanceRunner(required_kinds=cfg["required_kinds"], build_contract=cfg["scope"])
    report = runner.verify({"preview_url": "http://127.0.0.1:%d" % port}, {"acceptance": cfg["acceptance"]},
                           cfg["personas"]).to_dict()
else:
    report = {"status": "FAIL", "summary": "the app did not answer on its health path", "checks": []}
if p.poll() is None:
    p.terminate()
try:
    out = p.communicate(timeout=3)[0] or b""
except Exception:
    p.kill(); out = b""
report["server_log_tail"] = out.decode("utf-8", "replace")[-1500:]
print("BEHAVIOR-ACCEPTANCE " + json.dumps(report, ensure_ascii=False))
'''


def find_in_chain(executor, cls):
    """The first executor of type `cls` in a wrapper chain (wrappers keep `_inner`)."""
    seen = 0
    while executor is not None and seen < 20:
        if isinstance(executor, cls):
            return executor
        executor = getattr(executor, '__dict__', {}).get('_inner')
        seen += 1
    return None


def _failure_text(report: dict) -> tuple[str, str]:
    failed = [c for c in report.get('checks', []) if not c.get('passed')]
    lines = []
    for c in failed[:6]:
        lines.append(f"- step {c.get('step_id')} ({c.get('kind')}, acceptance {','.join(c.get('acceptance_ids') or [])}): "
                     f"sent {c.get('request')!s} -> HTTP {c.get('http_status')}; {c.get('detail')}"
                     + (f"; answer: {c.get('response_excerpt')!s}"[:400] if c.get('response_excerpt') else ''))
    missing = []
    if report.get('missing_acceptance_ids'):
        missing.append('acceptance criteria not covered by a passing step: ' + ','.join(report['missing_acceptance_ids']))
    if report.get('missing_kinds'):
        missing.append('behaviours that must be shown working: ' + ','.join(report['missing_kinds']))
    waived = [str(k) for k in (report.get('not_required_kinds') or ())]
    if waived and report.get('missing_acceptance_ids'):
        missing.append('kinds NOT_REQUIRED for this approved product (never run, never counted as coverage): '
                       + ','.join(waived) + '. A criterion whose only step has such a kind stays uncovered: attach it to a '
                       'step of a required kind that really checks it (e.g. a GET of the page asserting the approved text).')
    message = 'behavioural acceptance failed: ' + str(report.get('summary', ''))[:300]
    detail = ('The real app was started and the acceptance plan was run against it over HTTP.\n'
              + '\n'.join(lines + missing)
              + '\nFix the app so these requests behave as the product promises (validation that rejects a valid '
                'request is a bug). Only correct a test step if the step itself is wrong for the approved '
                'requirements; never remove coverage of an acceptance criterion.\n'
              + 'Server log tail:\n' + str(report.get('server_log_tail', ''))[-900:] + '\n' + PLAN_SHAPE)
    return message, detail


class BehaviorAcceptanceExecutor:
    def __init__(self, inner, *, enabled: bool = True):
        self._inner = inner
        self._enabled = enabled
        self.scope: dict | None = None          # set from the approved contract by the worker
        self.last_report: dict | None = None
        self.history: list[dict] = []

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
        from .preview_runtime import NotPreviewable, parse_preview_contract, parse_web_saas_acceptance_plan
        try:
            contract = parse_preview_contract(repository)
            plan = parse_web_saas_acceptance_plan(repository)
        except NotPreviewable as exc:
            return ExecutionReport(False, (AcceptanceFailure(BEHAVIOR_FAILURE_ID, f'invalid acceptance plan: {exc}',
                                                             PLAN_SHAPE),), report.build_log)
        acceptance = [{'id': a.id} for a in getattr(spec, 'acceptance', ())]
        if plan is None:
            if not acceptance:
                return report
            return ExecutionReport(False, (AcceptanceFailure(
                BEHAVIOR_FAILURE_ID, 'the product has no behavioural acceptance plan',
                'Add a plan that exercises every acceptance criterion over HTTP.\n' + PLAN_SHAPE),), report.build_log)
        run = getattr(self._inner, '_run', None)
        if not contract.runtime.startswith('python') or not callable(run):
            self.last_report = {'status': 'NOT_RUN', 'summary': 'no sandbox runtime for this product'}
            return report
        config = {'runner': _RUNNER_SOURCE, 'required_kinds': list(plan.required_kinds), 'scope': self.scope,
                  'acceptance': acceptance, 'personas': [dict(p) for p in plan.personas]}
        # The run gets a copy of the repository plus its configuration file;
        # the product's own repository is not changed.
        staged = dict(repository)
        staged['.omni/_behavior_run.json'] = json.dumps(config, ensure_ascii=False)
        try:
            staged, argv = staged_script(staged, 'behavior_acceptance', _SCRIPT)
            result = run(staged, argv, 'behavior-acceptance')
        except Exception as exc:
            return ExecutionReport(False, (AcceptanceFailure(BEHAVIOR_FAILURE_ID,
                                                             f'behavioural acceptance could not run: {exc}'),),
                                   report.build_log)
        out = str(result.get('stdout', ''))
        parsed = None
        for line in out.splitlines():
            if line.startswith('BEHAVIOR-ACCEPTANCE '):
                try:
                    parsed = json.loads(line[len('BEHAVIOR-ACCEPTANCE '):])
                except ValueError:
                    parsed = None
        if parsed is None:
            tail = (out + str(result.get('stderr', '')))[-900:]
            parsed = {'status': 'FAIL', 'summary': 'acceptance run produced no result', 'checks': [],
                      'server_log_tail': tail}
        self.last_report = {k: parsed.get(k) for k in ('status', 'summary', 'checks', 'missing_acceptance_ids',
                                                        'missing_kinds', 'not_required_kinds', 'covered_kinds')}
        self.history.append({'status': parsed.get('status'), 'summary': parsed.get('summary')})
        if parsed.get('status') == 'PASS':
            return report
        message, detail = _failure_text(parsed)
        return ExecutionReport(False, (AcceptanceFailure(BEHAVIOR_FAILURE_ID, message, detail),),
                               report.build_log + '\n' + message)
