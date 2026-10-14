import unittest

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.change_policy import ChangeAssessment
from omni_prod.modification_engine import CandidateModificationEngine
from omni_prod.product_evolution import SpecRegressionError
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import parse_patch

SPEC = {
    'title': 'Todo',
    'summary': 'Todo app',
    'stack': ['python'],
    'requirements': [
        {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
    ],
    'acceptance': [
        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
    ],
}

EVOLVED_SPEC = {
    'title': 'Todo',
    'summary': 'Todo app',
    'stack': ['python'],
    'requirements': [
        {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
        {'id': 'R2', 'text': 'calendar view', 'kind': 'functional', 'mandatory': True},
    ],
    'acceptance': [
        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
        {'id': 'A2', 'requirement_id': 'R2', 'text': 'calendar view renders'},
    ],
}

def _spec():
    return ProductSpec.from_dict(SPEC)


class Classifier:
    def __init__(self, category, reason='because', acceptance_ids=()):
        self.category = category
        self.reason = reason
        self.acceptance_ids = acceptance_ids
        self.calls = 0

    def classify(self, *, spec, followup):
        self.calls += 1
        return ChangeAssessment.from_dict(
            {'category': self.category, 'reason': self.reason, 'acceptance_ids': list(self.acceptance_ids)},
            spec=spec,
        )


class RepairsOnFirstTry:
    def __init__(self):
        self.calls = []

    def repair(self, **kwargs):
        self.calls.append(kwargs)
        return parse_patch({'files': [{'path': 'app.py', 'content': 'WORKING'}]})


class Executor:
    def __init__(self):
        self.calls = 0

    def execute(self, *, repository, spec):
        self.calls += 1
        if repository.get('app.py') == 'WORKING':
            return ExecutionReport(True)
        return ExecutionReport(False, (AcceptanceFailure('A1', 'not working', 'app.py'),), 'failed')


class EvolverImmediatelyPassing:
    """Returns a spec + patch that already passes verification -- no repair
    round should be needed afterward."""
    def __init__(self, spec_dict=EVOLVED_SPEC, file_content='WORKING'):
        self.spec_dict = spec_dict
        self.file_content = file_content
        self.calls = []

    def evolve(self, *, spec, repo_summary, followup):
        self.calls.append({'spec': spec, 'repo_summary': repo_summary, 'followup': followup})
        new_spec = ProductSpec.from_dict(self.spec_dict)
        patch = parse_patch({'files': [{'path': 'app.py', 'content': self.file_content}]})
        return new_spec, patch


class EvolverNeedsRepair:
    """Returns a spec but a patch that does NOT pass verification yet, so the
    post-evolution repair loop must run."""
    def evolve(self, *, spec, repo_summary, followup):
        new_spec = ProductSpec.from_dict(EVOLVED_SPEC)
        patch = parse_patch({'files': [{'path': 'app.py', 'content': 'BROKEN'}]})
        return new_spec, patch


class Unreachable:
    def repair(self, **kwargs):
        raise AssertionError('repairer must not be called for this path')

    def execute(self, **kwargs):
        raise AssertionError('executor must not be called for this path')

    def evolve(self, **kwargs):
        raise AssertionError('evolver must not be called for this path')


def quality_fn_factory(passed=True, score=90, minimum_score=80, blockers=()):
    calls = []

    def fn(*, spec, repository, minimum_score=minimum_score):
        calls.append((spec, dict(repository)))
        return _FakeQuality(passed, score, minimum_score, blockers)
    fn.calls = calls
    return fn


class _FakeQuality:
    def __init__(self, passed, score, minimum_score, blockers):
        self.passed = passed
        self.score = score
        self.minimum_score = minimum_score
        self.blockers = blockers

    def to_dict(self):
        return {'passed': self.passed, 'score': self.score}


def security_fn_factory(passed=True, findings=()):
    calls = []

    def fn(repository):
        calls.append(dict(repository))
        return _FakeSecurity(passed, findings)
    fn.calls = calls
    return fn


class _FakeSecurity:
    def __init__(self, passed, findings):
        self.passed = passed
        self.findings = findings

    def to_dict(self):
        return {'passed': self.passed, 'findings': list(self.findings)}


class FakeRightsEngine:
    def __init__(self, publish_allowed=True, status='CLEAR'):
        self.publish_allowed = publish_allowed
        self.status = status
        self.calls = []

    def assess(self, prompt, *, target_markets, evidence):
        self.calls.append({'prompt': prompt, 'target_markets': target_markets, 'evidence': evidence})
        return _FakeRights(self.publish_allowed, self.status)


class _FakeRights:
    def __init__(self, publish_allowed, status):
        self.publish_allowed = publish_allowed
        self.status = status

    def to_dict(self):
        return {'publish_allowed': self.publish_allowed, 'status': self.status}


def _engine(classifier, *, repairer=None, executor=None, evolver=None,
            quality_ok=True, security_ok=True, rights_ok=True, max_repair_rounds=3):
    return CandidateModificationEngine(
        classifier=classifier,
        repairer=repairer or Unreachable(),
        executor=executor or Unreachable(),
        evolver=evolver or Unreachable(),
        quality_fn=quality_fn_factory(passed=quality_ok),
        security_fn=security_fn_factory(passed=security_ok),
        rights_engine=FakeRightsEngine(publish_allowed=rights_ok),
        max_repair_rounds=max_repair_rounds,
    )


class AmbiguousTests(unittest.TestCase):
    def test_ambiguous_builds_nothing(self):
        engine = _engine(Classifier('ambiguous'))
        original = {'app.py': 'BROKEN'}
        outcome = engine.propose(spec=_spec(), repository=original, followup='make it better somehow')
        self.assertEqual(outcome.status, 'needs_clarification')
        self.assertEqual(outcome.repair_rounds, 0)
        self.assertIsNone(outcome.report)
        self.assertIsNone(outcome.gates)
        self.assertIsNone(outcome.diff)
        self.assertEqual(outcome.candidate_repository, original)
        self.assertIsNot(outcome.candidate_repository, original)


class FreeRepairPathTests(unittest.TestCase):
    def test_missing_requirement_reaches_ready_for_review_when_all_gates_pass(self):
        repairer = RepairsOnFirstTry()
        executor = Executor()
        classifier = Classifier('missing_requirement', reason='list is empty', acceptance_ids=['A1'])
        engine = CandidateModificationEngine(
            classifier=classifier, repairer=repairer, executor=executor, evolver=Unreachable(),
            quality_fn=quality_fn_factory(passed=True), security_fn=security_fn_factory(passed=True),
            rights_engine=FakeRightsEngine(publish_allowed=True),
        )
        source_spec = _spec()
        outcome = engine.propose(spec=source_spec, repository={'app.py': 'BROKEN'}, followup='list never shows anything')
        self.assertEqual(outcome.status, 'ready_for_review')
        self.assertEqual(outcome.repair_rounds, 1)
        self.assertTrue(outcome.gates.passed)
        self.assertIsNone(outcome.gates.blocking_gate)
        # M4B: free repair must never change the spec.
        self.assertIs(outcome.candidate_spec, source_spec)
        self.assertTrue(outcome.diff.spec.is_empty)
        self.assertIn('app.py', outcome.diff.repository.modified)
        self.assertFalse(outcome.billable)

    def test_verification_failure_blocks_before_any_gate_runs(self):
        # A repairer that never produces a passing file, and max_repair_rounds=1
        # so verification is still failing when the loop ends.
        class NeverRepairs:
            def repair(self, **kwargs):
                return parse_patch({'files': [{'path': 'app.py', 'content': 'STILL_BROKEN'}]})
        engine = CandidateModificationEngine(
            classifier=Classifier('system_bug', reason='crashes', acceptance_ids=['A1']),
            repairer=NeverRepairs(), executor=Executor(), evolver=Unreachable(),
            quality_fn=lambda **kw: (_ for _ in ()).throw(AssertionError('quality must not run')),
            security_fn=lambda repo: (_ for _ in ()).throw(AssertionError('security must not run')),
            rights_engine=None,
            max_repair_rounds=1,
        )
        outcome = engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='crashes')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(outcome.gates.blocking_gate, 'verification')

    def test_quality_gate_blocks_before_security_and_rights_run(self):
        engine = CandidateModificationEngine(
            classifier=Classifier('missing_requirement', reason='x', acceptance_ids=['A1']),
            repairer=RepairsOnFirstTry(), executor=Executor(), evolver=Unreachable(),
            quality_fn=quality_fn_factory(passed=False, score=50, minimum_score=80),
            security_fn=lambda repo: (_ for _ in ()).throw(AssertionError('security must not run')),
            rights_engine=None,
        )
        outcome = engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='fix it')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(outcome.gates.blocking_gate, 'quality')

    def test_security_gate_blocks_before_rights_runs(self):
        engine = CandidateModificationEngine(
            classifier=Classifier('missing_requirement', reason='x', acceptance_ids=['A1']),
            repairer=RepairsOnFirstTry(), executor=Executor(),
            evolver=Unreachable(), quality_fn=quality_fn_factory(passed=True),
            security_fn=security_fn_factory(passed=False, findings=('bad',)),
            rights_engine=None,
        )
        outcome = engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='fix it')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(outcome.gates.blocking_gate, 'security')

    def test_rights_gate_blocks_last(self):
        engine = CandidateModificationEngine(
            classifier=Classifier('missing_requirement', reason='x', acceptance_ids=['A1']),
            repairer=RepairsOnFirstTry(), executor=Executor(), evolver=Unreachable(),
            quality_fn=quality_fn_factory(passed=True), security_fn=security_fn_factory(passed=True),
            rights_engine=FakeRightsEngine(publish_allowed=False, status='REVIEW'),
        )
        outcome = engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='fix it')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(outcome.gates.blocking_gate, 'rights')


class ChangeRequestPathTests(unittest.TestCase):
    def test_change_request_evolves_spec_and_builds_a_candidate_with_no_extra_repair(self):
        evolver = EvolverImmediatelyPassing()
        engine = _engine(
            Classifier('change_request', reason='wants a calendar', acceptance_ids=()),
            executor=Executor(), evolver=evolver, quality_ok=True, security_ok=True, rights_ok=True,
        )
        source_spec = _spec()
        outcome = engine.propose(spec=source_spec, repository={'app.py': 'BROKEN'}, followup='add a calendar view')
        self.assertEqual(outcome.status, 'ready_for_review')
        self.assertEqual(outcome.repair_rounds, 0)
        self.assertTrue(outcome.billable)
        self.assertNotEqual(outcome.candidate_spec, source_spec)
        self.assertIn('R2', outcome.diff.spec.requirements_added)
        self.assertIn('A2', outcome.diff.spec.acceptance_added)
        self.assertEqual(len(evolver.calls), 1)
        self.assertEqual(evolver.calls[0]['followup'], 'add a calendar view')

    def test_change_request_runs_repair_loop_after_evolution_when_needed(self):
        class RepairsToWorking:
            def __init__(self):
                self.calls = 0

            def repair(self, **kwargs):
                self.calls += 1
                return parse_patch({'files': [{'path': 'app.py', 'content': 'WORKING'}]})

        repairer = RepairsToWorking()
        engine = CandidateModificationEngine(
            classifier=Classifier('change_request', reason='wants a calendar', acceptance_ids=()),
            repairer=repairer, executor=Executor(), evolver=EvolverNeedsRepair(),
            quality_fn=quality_fn_factory(passed=True), security_fn=security_fn_factory(passed=True),
            rights_engine=FakeRightsEngine(publish_allowed=True),
        )
        outcome = engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='add a calendar view')
        self.assertEqual(outcome.status, 'ready_for_review')
        self.assertEqual(outcome.repair_rounds, 1)
        self.assertEqual(repairer.calls, 1)
        # The repair call after evolution must target the *new* spec, not the original.
        self.assertEqual(outcome.candidate_spec.title, 'Todo')
        self.assertIn('R2', {r.id for r in outcome.candidate_spec.requirements})

    def test_evolver_exceptions_are_not_swallowed(self):
        # ProductEvolutionAgent.evolve() itself is what detects a dropped id
        # (see tests/test_product_evolution.py) -- this checks the orchestrator
        # doesn't catch and hide that (or any other evolver) exception, the
        # same way AutonomousProductEngine.build() and ModifierEngine.modify()
        # let internal exceptions propagate to their caller rather than
        # reporting a fabricated 'failed' outcome.
        class RaisingEvolver:
            def evolve(self, *, spec, repo_summary, followup):
                raise SpecRegressionError('evolution dropped existing requirement id(s): [\'R1\']')

        engine = _engine(
            Classifier('change_request', reason='wants a calendar', acceptance_ids=()),
            executor=Executor(), evolver=RaisingEvolver(),
        )
        with self.assertRaises(SpecRegressionError):
            engine.propose(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='add a calendar view')


class InputValidationTests(unittest.TestCase):
    def test_empty_followup_rejected(self):
        engine = _engine(Classifier('ambiguous'))
        with self.assertRaises(ValueError):
            engine.propose(spec=_spec(), repository={'app.py': 'x'}, followup='   ')

    def test_empty_repository_rejected(self):
        engine = _engine(Classifier('ambiguous'))
        with self.assertRaises(ValueError):
            engine.propose(spec=_spec(), repository={}, followup='fix it')

    def test_negative_max_repair_rounds_rejected(self):
        with self.assertRaises(ValueError):
            CandidateModificationEngine(
                classifier=Classifier('ambiguous'), repairer=Unreachable(), executor=Unreachable(),
                evolver=Unreachable(), quality_fn=None, security_fn=None, rights_engine=None,
                max_repair_rounds=-1,
            )


if __name__ == '__main__':
    unittest.main()
