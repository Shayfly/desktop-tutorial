"""C24: the failure taxonomy (and first_pass) is written in live builds and on early failure (founder 2026-10-20).

C30 found it written only by rehearsals (rehearsal.py:62), computed only at the very end of a build that returned
(autonomous_core.py:279): a build that raised lost the rounds already verified, and live builds (worker_tasks.py)
recorded no taxonomy at all, so a paid run never reached first_pass_yield.
"""
import json
import unittest

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import FilePatch

from tests.m5_worker_harness import ContractBuildHarness

SPEC = type('S', (), {'acceptance': [type('A', (), {'id': 'A1', 'text': 'opens'})()], 'requirements': []})()


class Architect:
    def create_spec(self, prompt):
        return SPEC


class Generator:
    def __init__(self, exc=None):
        self.exc = exc

    def generate(self, spec):
        if self.exc:
            raise self.exc
        return (FilePatch('app.py', 'print(1)\n'),)


class Repairer:
    def repair(self, *, spec, repo_summary, failures):
        return (FilePatch('app.py', f'print({len(repo_summary)})\n'),)


class Executor:
    """Round 0 fails with a BEHAVIOR failure; the next call raises (a sandbox outage mid-build)."""
    def __init__(self):
        self.calls = 0

    def execute(self, *, repository, spec):
        self.calls += 1
        if self.calls == 1:
            return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'behavioural acceptance failed: 1 failed check(s)'),))
        raise RuntimeError('sandbox unavailable')


def engine(generator=None):
    return AutonomousProductEngine(architect=Architect(), generator=generator or Generator(), repairer=Repairer(),
                                   executor=Executor(), max_repair_rounds=3)


class EngineKeepsWhatItVerified(unittest.TestCase):
    def test_a_build_that_raises_mid_way_keeps_round_0(self):
        e = engine()
        with self.assertRaises(RuntimeError):
            e.build('league')
        self.assertEqual([(r['round_index'], r['layer']) for r in e.failure_taxonomy], [(0, 'behaviour')])
        self.assertIs(e.first_pass, False)

    def test_a_build_that_raises_before_any_round_has_an_empty_taxonomy_not_a_stale_one(self):
        e = engine()
        e.failure_taxonomy, e.first_pass = [{'round_index': 9, 'layer': 'stale'}], True     # a previous build's values
        e.generator = Generator(RuntimeError('model down'))
        with self.assertRaises(RuntimeError):
            e.build('league')
        self.assertEqual(e.failure_taxonomy, [])
        self.assertIs(e.first_pass, False)


class LiveBuildEvidence(unittest.TestCase):
    TAXONOMY = [{'round_index': 0, 'layer': 'preview', 'failure_type': 'placeholder_page', 'chain_depth': 1}]

    def test_success_evidence_carries_taxonomy_and_first_pass(self):
        h = ContractBuildHarness()
        h.engine.failure_taxonomy, h.engine.first_pass = list(self.TAXONOMY), False
        h.run()
        ev = h.final['evidence_json']
        self.assertEqual(ev['failure_taxonomy'], self.TAXONOMY)
        self.assertIs(ev['first_pass'], False)

    def test_an_early_failure_still_writes_it(self):
        h = ContractBuildHarness(engine_exc=RuntimeError('sandbox unavailable'))
        h.engine.failure_taxonomy, h.engine.first_pass = list(self.TAXONOMY), False
        with self.assertRaises(RuntimeError):                                 # the worker records, then re-raises
            h.run()
        self.assertEqual(h.final['target'].value, 'failed')
        ev = h.final['evidence_json']
        self.assertEqual(ev['failure_taxonomy'], self.TAXONOMY)
        self.assertIs(ev['first_pass'], False)
        json.dumps(ev['failure_taxonomy'])                                     # serialisable as stored


if __name__ == '__main__':
    unittest.main()
