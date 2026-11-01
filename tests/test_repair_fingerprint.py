"""Repair fingerprint (founder brief 2026-11-01, section 1): a failing check names WHERE it failed (file:line) at the
END of AcceptanceFailure.message, and the evidence keeps head AND tail of the output.

Both executors are exercised: SandboxRepositoryExecutor (local docker path) and RemoteSandboxRepositoryExecutor (the
production worker path, OMNI_SANDBOX_RUNNER_URL). Seam rule: the remote executor's real `_run` runs, including
validate_snapshot / validate_command and the HMAC body; only the HTTP transport is replaced, and the transport
answers with the REAL output of pytest run on the fixture. The fixture (tests/fixtures/repair_repro) is built from the
QA-review text of rehearsal run 39313029465, not from that run's files (they were never kept, issue #202).
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.product_spec import AcceptanceCriterion, ProductSpec, Requirement
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox import SandboxLimits
from omni_prod.sandbox_executor import SandboxRepositoryExecutor, _window

FIXTURE = Path(__file__).parent / 'fixtures' / 'repair_repro'
INT_LINE = next(i for i, line in enumerate((FIXTURE / 'app.py').read_text().splitlines(), 1)
                if 'int(payload["score"])' in line)


def repository() -> dict[str, str]:
    return {str(p.relative_to(FIXTURE)): p.read_text(encoding='utf-8')
            for p in FIXTURE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def spec() -> ProductSpec:
    req = (Requirement('R1', 'scores are whole numbers'),)
    acc = tuple(AcceptanceCriterion(f'A{i}', 'R1', t) for i, t in
                ((1, '2.9 is refused with 400'), (2, 'true is refused with 400'), (3, '7 is accepted with 201')))
    return ProductSpec('League', 'league table', ('python',), req, acc)


def run_for_real(repo: dict[str, str], argv) -> SimpleNamespace:
    """Materialize the repository and run the manifest command with this interpreter (real pytest output)."""
    with tempfile.TemporaryDirectory() as td:
        for rel, text in repo.items():
            path = Path(td) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        argv = [sys.executable if a in ('python', 'python3') else a for a in argv]
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        p = subprocess.run(argv + (['-p', 'no:cacheprovider'] if 'pytest' in argv else []), cwd=td,
                           capture_output=True, text=True, timeout=120, env=env)
        return SimpleNamespace(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)


def local_executor():
    def runner(*, source_dir, build_id, limits, command, output_dir):
        repo = {str(p.relative_to(source_dir)): p.read_text(encoding='utf-8')
                for p in Path(source_dir).rglob('*') if p.is_file()}
        return run_for_real(repo, command)
    return SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner)


class FakeHTTP:
    """The only fake on the remote path: the transport. It runs the requested argv for real and answers like the
    sandbox-runner does ({returncode, stdout, stderr})."""
    def __init__(self):
        self.requests = []

    def __call__(self, req, timeout=None):
        body = json.loads(req.data.decode())
        self.requests.append(body)
        r = run_for_real(body['repository'], body['argv'])
        raw = json.dumps({'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}).encode()

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Resp(raw)


def remote_executor(http):
    return RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox-runner:8010', 'x' * 32), urlopen=http)


@unittest.skipUnless(shutil.which('python3') or sys.executable, 'needs a python interpreter')
class PointerInMessage(unittest.TestCase):
    """Verification 1: 2.9 produces a message that ends with app.py:<the int( line>, on BOTH executors."""

    def check(self, report, name):
        by_id = {f.acceptance_id: f for f in report.failures}
        print(f'\n[{name}] ' + '\n'.join(f'{f.acceptance_id}: {f.message}' for f in report.failures))
        a1 = by_id['A1']
        self.assertTrue(a1.message.endswith(f' at app.py:{INT_LINE}'), a1.message)
        line = (FIXTURE / 'app.py').read_text().splitlines()[INT_LINE - 1]
        self.assertIn('int(', line)
        self.assertIn('ValueError', a1.evidence)
        self.assertNotIn('A3', by_id)                                         # 7 -> 201 passes today
        return by_id

    def test_local_executor(self):
        self.check(local_executor().execute(repository=repository(), spec=spec()), 'local')

    def test_remote_executor_real_run_only_http_faked(self):
        http = FakeHTTP()
        by_id = self.check(remote_executor(http).execute(repository=repository(), spec=spec()), 'remote')
        self.assertTrue(by_id['A1'].message.startswith('remote verification failed: fractional score'))
        self.assertEqual([r['argv'][-1].split('::')[-1] for r in http.requests[1:]],
                         ['test_fractional_score_rejected', 'test_boolean_score_rejected', 'test_integer_score_accepted'])

    def test_pointer_survives_the_structured_consumer_cut(self):
        # sanitized_tail cuts from the END, so the pointer at the end of the message survives a tight limit
        from omni_prod.repair_contracts import sanitized_tail
        report = remote_executor(FakeHTTP()).execute(repository=repository(), spec=spec())
        a1 = next(f for f in report.failures if f.acceptance_id == 'A1')
        self.assertTrue(sanitized_tail(a1.message, limit=40).endswith(f'app.py:{INT_LINE}'))


class WindowKeepsHeadAndTail(unittest.TestCase):
    """Verification 2: on long output, both '=== FAILURES ===' (head) and the 'E   AssertionError' line (tail)."""

    def test_window_on_long_real_output(self):
        real = run_for_real(repository(), ['python', '-m', 'pytest', '-q',
                                           'tests/test_matches.py::test_boolean_score_rejected'])
        out = real.stdout + '\n' + real.stderr
        cut = out.index('\n', out.index('FAILURES ===')) + 1          # right after the whole FAILURES header line
        noise = ''.join(f'captured log line {i} ' + 'x' * 60 + '\n' for i in range(400))
        noisy = out[:cut] + noise + out[cut:]                          # long captured output between header and E line
        self.assertGreater(len(noisy), 3000)
        w = _window(noisy)
        print('\n[window] length', len(noisy), '->', len(w))
        self.assertIn('FAILURES ===', w)
        self.assertRegex(w, r'(?m)^E\s+assert 201 == 400')
        self.assertIn('\n…\n', w)
        self.assertNotIn('FAILURES ===', noisy[-3000:])                       # what the old [-3000:] lost

    def test_short_output_is_unchanged(self):
        self.assertEqual(_window('  short  '), 'short')


if __name__ == '__main__':
    unittest.main()


class BehaviourFrameFromServerLog(unittest.TestCase):
    """Section 2: the app frame (not site-packages) from server_log_tail is appended to each failed-step line."""

    LOG = ('Traceback (most recent call last):\n'
           '  File "/usr/local/lib/python3.11/site-packages/werkzeug/serving.py", line 333, in run_wsgi\n'
           f'  File "/workspace/app.py", line {INT_LINE}, in create_match\n'
           '    score = int(payload["score"])\n'
           "ValueError: invalid literal for int() with base 10: '2.9'\n")

    def report(self, log):
        return {'status': 'FAIL', 'summary': '1 failed check(s)', 'server_log_tail': log,
                'checks': [{'step_id': 's3', 'kind': 'data_create', 'acceptance_ids': ['A1'], 'passed': False,
                            'request': 'POST /api/matches {"score": "2.9"}', 'http_status': 500,
                            'detail': 'expected 400', 'response_excerpt': 'Internal Server Error'}]}

    def test_frame_after_detail_before_answer(self):
        from omni_prod.behavior_acceptance import _failure_text
        _, detail = _failure_text(self.report(self.LOG))
        line = next(x for x in detail.splitlines() if x.startswith('- step s3'))
        print('\n[behaviour] ' + line)
        self.assertIn(f'expected 400 (server: /workspace/app.py:{INT_LINE}); answer: Internal Server Error', line)
        self.assertNotIn('site-packages', line)

    def test_no_frame_no_suffix_and_longer_tail_kept(self):
        from omni_prod.behavior_acceptance import _failure_text
        _, detail = _failure_text(self.report('server started\n' + 'y' * 2400 + '\nEND'))
        self.assertNotIn('(server:', detail)
        self.assertIn('server started', detail)                            # 2400+ chars survive ([-2500:], was [-900:])


class SameRepairTwiceStops(unittest.TestCase):
    """Verification 3: two rounds with an identical patch stop at no_progress_repository_unchanged -- in the build
    loop (AutonomousProductEngine._build) AND in the free repair loop (modifier_engine.run_free_repair)."""

    def setUp(self):
        from omni_prod.autonomous_core import ExecutionReport as R
        from omni_prod.repository_patch import parse_patch
        self.FAIL = R(False, (AcceptanceFailureCls('A1', 'boom'),))
        self.parse = parse_patch

    def repairer(self, contents):
        parse, calls = self.parse, []

        class Rep:
            def repair(self, **kw):
                calls.append(1)
                return parse({'files': [{'path': 'app.py', 'content': contents[len(calls) - 1]}]})
        return Rep(), calls

    def executor(self):
        fail, runs = self.FAIL, []

        class Ex:
            def execute(self, *, repository, spec):
                runs.append(repository['app.py'])
                return fail
        return Ex(), runs

    def test_build_loop(self):
        from omni_prod.autonomous_core import AutonomousProductEngine
        parse = self.parse

        class Arch:
            def create_spec(self, prompt):
                return 'spec'

        class Gen:
            def generate(self, spec):
                return parse({'files': [{'path': 'app.py', 'content': 'v0'}]})
        rep, calls = self.repairer(['v1', 'v1', 'v2'])
        ex, runs = self.executor()
        result = AutonomousProductEngine(architect=Arch(), generator=Gen(), repairer=rep, executor=ex,
                                         max_repair_rounds=3).build('p')
        print('\n[build loop] stop_reason=', result.stop_reason, 'repairs=', len(calls), 'sandbox runs=', runs)
        self.assertEqual(result.stop_reason, 'no_progress_repository_unchanged')
        self.assertEqual(len(calls), 2)
        self.assertEqual(runs, ['v0', 'v1'])

    def test_free_repair_loop(self):
        from omni_prod.change_policy import ChangeAssessment
        from omni_prod.modifier_engine import run_free_repair
        rep, calls = self.repairer(['v1', 'v1', 'v2'])
        ex, runs = self.executor()
        assessment = ChangeAssessment('system_bug', 'scores are not validated', ('A1',), False)
        repo, rounds, report, stop = run_free_repair(spec=spec(), repository={'app.py': 'v0'}, assessment=assessment,
                                                     followup='2.9 is accepted', repairer=rep, executor=ex,
                                                     max_repair_rounds=3)
        print('\n[free repair] stop_reason=', stop, 'rounds=', rounds, 'sandbox runs=', runs)
        self.assertEqual(stop, 'no_progress_repository_unchanged')
        self.assertEqual((rounds, len(calls), runs, repo['app.py'], report.passed), (2, 2, ['v1'], 'v1', False))

    def test_modifier_result_carries_the_stop_reason(self):
        from omni_prod.change_policy import ChangeAssessment
        from omni_prod.modifier_engine import ModifierEngine
        rep, _ = self.repairer(['v1', 'v1'])
        ex, _ = self.executor()

        class Cls:
            def classify(self, **kw):
                return ChangeAssessment('system_bug', 'scores are not validated', ('A1',), False)
        r = ModifierEngine(classifier=Cls(), repairer=rep, executor=ex).modify(spec=spec(), repository={'app.py': 'v0'},
                                                                               followup='2.9 is accepted')
        self.assertEqual((r.status, r.stop_reason), ('failed', 'no_progress_repository_unchanged'))


from omni_prod.autonomous_core import AcceptanceFailure as AcceptanceFailureCls  # noqa: E402
