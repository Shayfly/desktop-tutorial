"""Basic stop-loss in the initial-build repair loop (founder decision 2026-10-07).

The sandbox is deterministic, so a repair that does not change the repository,
or returns it to a state that was already verified, cannot change the outcome.
The loop stops instead of paying for identical rounds.
"""
import unittest

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch

FAIL = ExecutionReport(False, (AcceptanceFailure('A1', 'boom'),))
PASS = ExecutionReport(True)


class _Architect:
    def create_spec(self, prompt):
        return 'spec'


class _Generator:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


class _Repairer:
    def __init__(self, contents):
        self.contents, self.calls = list(contents), 0

    def repair(self, **kw):
        self.calls += 1
        return parse_patch({'files': [{'path': 'app.py', 'content': self.contents.pop(0)}]})


class _Executor:
    def __init__(self, passing=()):
        self.passing, self.runs = set(passing), []

    def execute(self, *, repository, spec):
        self.runs.append(repository['app.py'])
        return PASS if repository['app.py'] in self.passing else FAIL


def _engine(repairer, executor, rounds=5):
    return AutonomousProductEngine(architect=_Architect(), generator=_Generator(), repairer=repairer,
                                   executor=executor, max_repair_rounds=rounds)


class StopLossTests(unittest.TestCase):
    def test_unchanged_repository_stops_without_re_verifying(self):
        rep, ex = _Repairer(['v0', 'v1', 'v2']), _Executor()
        result = _engine(rep, ex).build('p')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.stop_reason, 'no_progress_repository_unchanged')
        self.assertEqual(rep.calls, 1)
        self.assertEqual(ex.runs, ['v0'])  # the no-op repair is not sent to the sandbox again

    def test_cycle_stops_and_keeps_repository_paired_with_report(self):
        rep, ex = _Repairer(['v1', 'v0', 'v2']), _Executor()
        result = _engine(rep, ex).build('p')
        self.assertEqual(result.stop_reason, 'no_progress_repository_cycle')
        self.assertEqual(rep.calls, 2)
        self.assertEqual(ex.runs, ['v0', 'v1'])
        self.assertEqual(result.repository['app.py'], 'v1')  # the state whose report is returned
        self.assertEqual(result.repair_rounds, 2)  # both paid repair calls are counted

    def test_progressing_repairs_are_not_stopped(self):
        rep, ex = _Repairer(['v1', 'v2', 'v3']), _Executor(passing={'v3'})
        result = _engine(rep, ex).build('p')
        self.assertEqual((result.status, result.stop_reason, result.repair_rounds), ('ready', 'passed', 3))

    def test_round_cap_reason(self):
        rep, ex = _Repairer(['v1', 'v2']), _Executor()
        result = _engine(rep, ex, rounds=2).build('p')
        self.assertEqual((result.status, result.stop_reason, result.repair_rounds), ('failed', 'max_repair_rounds', 2))

    def test_first_pass_reason(self):
        result = _engine(_Repairer([]), _Executor(passing={'v0'})).build('p')
        self.assertEqual((result.stop_reason, result.repair_rounds), ('passed', 0))



class RoundSnapshotTests(unittest.TestCase):
    """Directive 2026-10-10 P0.3: each verified candidate is stored before the next repair."""

    def test_every_round_is_snapshotted_with_its_decision(self):
        ex = _StagedExecutor({'v0': 'behavior', 'v1': 'build', 'v2': 'pass'})
        engine = _engine(_Repairer(['v1', 'v2']), ex)
        seen = []
        engine.round_hook = lambda i, repo, report, decision, progress: seen.append((i, repo['app.py'], decision))
        engine.build('p')
        self.assertEqual(seen, [(0, 'v0', 'initial'), (1, 'v1', 'discarded'), (2, 'v2', 'passed')])

    def test_worker_stores_rounds_durably_and_logs_a_discard(self):
        from types import SimpleNamespace
        from omni_prod.worker_tasks import install_round_snapshots
        stored, events, sink = {}, [], []
        ws = SimpleNamespace(storage=SimpleNamespace(put_bytes=lambda k, d: stored.__setitem__(k, d)),
                             _zip_repo=lambda repo: repr(sorted(repo.items())).encode())
        control = SimpleNamespace(log=lambda kind, msg: events.append(kind))
        ex = _StagedExecutor({'v0': 'behavior', 'v1': 'build', 'v2': 'pass'})
        engine = _engine(_Repairer(['v1', 'v2']), ex)
        install_round_snapshots(engine, ws, 'bld_x', sink, control)
        engine.build('p')
        self.assertEqual([e['decision'] for e in sink], ['initial', 'discarded', 'passed'])
        self.assertTrue(all(e['key'] in stored and e['key'].startswith('build-rounds/bld_x/') for e in sink))
        self.assertEqual(sink[0]['failing'], ['BEHAVIOR'])
        self.assertEqual(events, ['info'])

    def test_a_failing_store_never_breaks_the_build(self):
        ex = _StagedExecutor({'v0': 'pass'})
        engine = _engine(_Repairer([]), ex)
        engine.round_hook = lambda *a: (_ for _ in ()).throw(OSError('r2 down'))
        self.assertEqual(engine.build('p').status, 'ready')

if __name__ == '__main__':
    unittest.main()


class _StagedExecutor:
    """Reports per repository content: 'build' / 'behavior' failures or pass."""

    def __init__(self, outcomes):
        self.outcomes, self.runs = outcomes, []

    def execute(self, *, repository, spec):
        content = repository['app.py']
        self.runs.append(content)
        kind = self.outcomes[content]
        if kind == 'pass':
            return PASS
        if kind == 'build':
            return ExecutionReport(False, tuple(AcceptanceFailure(a, 'remote build failed') for a in ('A1', 'A2')))
        return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'behavioural acceptance failed: 1 failed check'),))


class _RecordingRepairer(_Repairer):
    def __init__(self, contents):
        super().__init__(contents)
        self.seen = []

    def repair(self, **kw):
        self.seen.append((kw['repo_summary'], kw['failures']))
        return super().repair(**kw)


class ProgressAwareRepairTests(unittest.TestCase):
    """Paid builds 2026-10-09: a repair turned '1 behaviour check fails' into
    'build fails' and later rounds drifted further from passing."""

    def test_a_repair_that_goes_backwards_is_discarded_and_the_next_starts_from_the_best(self):
        ex = _StagedExecutor({'v0': 'behavior', 'v1': 'build', 'v2': 'pass'})
        rep = _RecordingRepairer(['v1', 'v2'])
        engine = _engine(rep, ex)
        engine._summary = lambda repo, failures=(): dict(repo)
        result = engine.build('p')
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.repository['app.py'], 'v2')
        second_repo, second_failures = rep.seen[1]
        self.assertEqual(second_repo['app.py'], 'v0')                       # back to the best candidate
        self.assertEqual(second_failures[-1]['acceptance_id'], 'REPAIR_REGRESSION')
        self.assertIn('discarded', engine.trace[0])

    def test_a_failed_build_returns_the_best_candidate_not_the_last(self):
        ex = _StagedExecutor({'v0': 'build', 'v1': 'behavior', 'v2': 'build', 'v3': 'build'})
        result = _engine(_Repairer(['v1', 'v2', 'v3']), ex, rounds=3).build('p')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.repository['app.py'], 'v1')
        self.assertEqual(result.report.failures[0].acceptance_id, 'BEHAVIOR')

    def test_progress_orders_the_verification_chain(self):
        P = AutonomousProductEngine.progress
        build = ExecutionReport(False, (AcceptanceFailure('A1', 'remote build failed'),))
        unit = ExecutionReport(False, (AcceptanceFailure('A1', 'remote verification failed: unit tests'),))
        acc = ExecutionReport(False, (AcceptanceFailure('A1', 'remote verification failed: acceptance tests'),))
        prev = ExecutionReport(False, (AcceptanceFailure('PREVIEW', 'placeholder page'),))
        beh = ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'x'),))
        self.assertLess(P(build), P(unit))
        self.assertLess(P(unit), P(acc))
        self.assertLess(P(acc), P(prev))
        self.assertLess(P(prev), P(beh))
        review = ExecutionReport(False, (AcceptanceFailure('REVIEW', 'hard-coded exception for test names'),))
        browser = ExecutionReport(False, (AcceptanceFailure('BROWSER', 'x'),))
        self.assertLess(P(beh), P(browser))
        self.assertLess(P(browser), P(review))   # review runs only after behaviour passed
        self.assertLess(P(review), P(PASS))
