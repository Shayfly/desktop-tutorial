"""G8, the runtime and load gate (plan part A: "G8 ריצה ועומס"; the owner, 2026-11-16, stage F: `web_app` + G8).

The preview smoke proves the product STARTS and answers once. Nothing proved it keeps answering: a server that
handles one request at a time and hangs on the second, a handler that leaks until the process dies, a page that
takes seconds to build on every request. A customer's site is opened by more than one person.

After everything before it passed, the product is started in the same isolated sandbox (read-only source, no
network, loopback only) and asked for its health path REQUESTS times, CONCURRENCY at a time. It passes when:

  LOAD_ERRORS      every request was answered 2xx/3xx
  RUNTIME_CRASHED  the server is still running afterwards and answers once more
  LOAD_SLOW        the 95th-percentile answer time is at most P95_LIMIT_MS
  MEMORY_HIGH      the server's resident memory afterwards is at most RSS_LIMIT_KB (read from /proc; NOT_RUN is said
                   when the sandbox does not expose it, never guessed)

No model, bounded: REQUESTS requests, WALL_SECONDS at most. G8 is a new gate, so it enters at warn
(gate.CALIBRATING): the measurements go to the log and the build evidence on every build, and it blocks only after
its limits are calibrated on three real builds.
"""
from __future__ import annotations

import json
import logging

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .preview_runtime import NotPreviewable, parse_preview_contract
from .sandbox_script import staged_script

GATE = 'G8'
ACCEPTANCE_ID = 'gate-G8-runtime-load'
REQUESTS, CONCURRENCY = 60, 6
P95_LIMIT_MS = 1500
RSS_LIMIT_KB = 262_144            # 256 MB
START_SECONDS, WALL_SECONDS = 20, 45
CODES = ('LOAD_ERRORS', 'RUNTIME_CRASHED', 'LOAD_SLOW', 'MEMORY_HIGH', 'NOT_STARTED')
_LOG = logging.getLogger(__name__)

# Runs inside the sandbox; standard library only. Prints one line: "RUNTIME-LOAD <json>".
_LOAD = r'''
import json, os, subprocess, sys, threading, time, urllib.request, urllib.error
REQUESTS, CONCURRENCY, START, WALL = %(requests)d, %(concurrency)d, %(start)d, %(wall)d
c = json.load(open(".omni/project.json"))
port, path = int(c["port"]), c.get("health_path", "/")
url = "http://127.0.0.1:%%d%%s" %% (port, path)
env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
p = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
out = {"requests": 0, "errors": 0, "started": False, "alive": False, "rss_kb": None}
began = time.time()

def one(timeout=5):
    t = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(200000)
            ok = 200 <= r.status < 400
    except Exception:
        ok = False
    return ok, (time.time() - t) * 1000.0

while time.time() - began < START and p.poll() is None:
    if one(timeout=5)[0]:          # a slow first answer is still a start; slowness is judged by LOAD_SLOW
        out["started"] = True
        break
    time.sleep(0.4)

times, lock, left = [], threading.Lock(), [REQUESTS]
def worker():
    while time.time() - began < WALL:
        with lock:
            if left[0] <= 0:
                return
            left[0] -= 1
        ok, ms = one()
        with lock:
            out["requests"] += 1
            times.append(ms)
            if not ok:
                out["errors"] += 1
if out["started"]:
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(CONCURRENCY)]
    for t in threads: t.start()
    for t in threads: t.join(max(1.0, WALL - (time.time() - began)))
    out["alive"] = p.poll() is None and one(timeout=5)[0]
    try:
        for line in open("/proc/%%d/status" %% p.pid):
            if line.startswith("VmRSS:"):
                out["rss_kb"] = int(line.split()[1])
    except Exception:
        pass
    times.sort()
    if times:
        out["p50_ms"] = round(times[len(times) // 2])
        out["p95_ms"] = round(times[min(len(times) - 1, int(len(times) * 0.95))])
        out["max_ms"] = round(times[-1])
if p.poll() is None:
    p.terminate()
    try:
        p.wait(3)
    except Exception:
        p.kill()
out["seconds"] = round(time.time() - began, 1)
print("RUNTIME-LOAD " + json.dumps(out))
''' % {'requests': REQUESTS, 'concurrency': CONCURRENCY, 'start': START_SECONDS, 'wall': WALL_SECONDS}


def parse(stdout: str) -> dict | None:
    for line in reversed(str(stdout or '').splitlines()):
        if line.startswith('RUNTIME-LOAD '):
            try:
                data = json.loads(line[len('RUNTIME-LOAD '):])
            except ValueError:
                return None
            return data if isinstance(data, dict) and isinstance(data.get('requests'), int) else None
    return None


def judge(m: dict) -> list[dict]:
    """[{code, why}] for one measurement. Each limit is judged on its own; nothing is averaged away."""
    if not m.get('started'):
        return [{'code': 'NOT_STARTED', 'why': f'the server did not answer within {START_SECONDS} s'}]
    found = []
    if m.get('errors') or m.get('requests') != REQUESTS:
        found.append({'code': 'LOAD_ERRORS', 'why': f"{m.get('errors')} of {m.get('requests')} requests failed, "
                                                    f'and {REQUESTS - int(m.get("requests") or 0)} were never answered'})
    if not m.get('alive'):
        found.append({'code': 'RUNTIME_CRASHED', 'why': 'the server stopped running or stopped answering after the load'})
    if isinstance(m.get('p95_ms'), (int, float)) and m['p95_ms'] > P95_LIMIT_MS:
        found.append({'code': 'LOAD_SLOW', 'why': f"95% of answers took up to {m['p95_ms']} ms; the limit is {P95_LIMIT_MS}"})
    if isinstance(m.get('rss_kb'), int) and m['rss_kb'] > RSS_LIMIT_KB:
        found.append({'code': 'MEMORY_HIGH', 'why': f"the server holds {m['rss_kb']:,} kB; the limit is {RSS_LIMIT_KB:,}"})
    return found


_FIX = {'LOAD_ERRORS': 'Every request must be answered: handle requests concurrently (ThreadingHTTPServer, not '
                       'HTTPServer) and never raise out of a handler.',
        'RUNTIME_CRASHED': 'The server must keep running: catch errors inside each handler and never exit the process.',
        'LOAD_SLOW': 'Build the page once and serve it from memory; do no slow work on every request.',
        'MEMORY_HIGH': 'Do not keep per-request data in memory; hold the page once.',
        'NOT_STARTED': 'The server must listen on 0.0.0.0:$PORT and answer the health path within seconds.'}


class RuntimeLoadExecutor:
    """warn: the measurement is recorded and the build goes on. block: each finding fails the build."""

    def __init__(self, inner, mode: str):
        self._inner, self.mode, self.last_load = inner, mode, None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report                      # a product that fails earlier checks is not load-tested
        return self.check(repository=repository, report=report)

    def _not_run(self, reason: str, report):
        self.last_load = {'status': 'NOT_RUN', 'mode': self.mode, 'reason': reason[:300]}
        _LOG.warning('G8_NOT_RUN mode=%s reason=%s', self.mode, reason[:300])
        if self.mode != 'block':
            return report
        from .verification_verdict import unverified      # NOT_RUN is not PASS
        return unverified(ACCEPTANCE_ID, reason, report.build_log)

    def check(self, *, repository, report):
        try:
            contract = parse_preview_contract(repository)
        except NotPreviewable as exc:
            return self._not_run(f'no preview contract to start the product from: {exc}', report)
        run = getattr(self._inner, '_run', None)
        if not contract.runtime.startswith('python') or not callable(run):
            return self._not_run(f'no sandbox runtime to start {contract.runtime!r}', report)
        try:
            staged, argv = staged_script(repository, 'runtime_load', _LOAD)
            result = run(staged, argv, 'runtime-load')
        except Exception as exc:
            from .verification_verdict import reraise_control
            reraise_control(exc)               # a cancel, a deadline or a budget stop ends the build; it is not a result
            return self._not_run(f'the load run could not start: {type(exc).__name__}: {exc}', report)
        measured = parse(result.get('stdout', ''))
        if measured is None:
            return self._not_run('the load run printed no measurement', report)
        findings = judge(measured)
        self.last_load = {'status': 'fail' if findings else 'pass', 'mode': self.mode, 'measured': measured,
                          'findings': findings,
                          **({'memory': 'NOT_RUN: the sandbox does not expose /proc'} if measured.get('rss_kb') is None
                             and measured.get('started') else {})}
        _LOG.info('G8_LOAD mode=%s status=%s measured=%s', self.mode, self.last_load['status'], measured)
        if not findings or self.mode != 'block':
            return report
        failures = tuple(AcceptanceFailure(ACCEPTANCE_ID, f"{f['code']}: {f['why']}. {_FIX[f['code']]}")
                         for f in findings)
        return ExecutionReport(False, tuple(report.failures) + failures, report.build_log)


def install(engine) -> str:
    """Install G8 in its gate mode (said in the log and written to gate_modes on every build). Returns the mode."""
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
    core.executor = core.runtime_load_check = RuntimeLoadExecutor(core.executor, mode)
    return mode


def report(engine) -> dict:
    core = getattr(engine, 'core', engine)
    modes = getattr(core, 'gate_modes', None)
    checker = getattr(core, 'runtime_load_check', None)
    return {'gate': GATE, 'mode': modes.get(GATE) if isinstance(modes, dict) else None,
            'last': checker.last_load if isinstance(checker, RuntimeLoadExecutor) else None}
