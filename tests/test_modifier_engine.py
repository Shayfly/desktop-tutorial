import unittest

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.change_policy import ChangeAssessment
from omni_prod.modifier_engine import ModifierEngine
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


class Classifier:
    """Mirrors ChangeClassifierAgent.classify()'s real contract: it returns a
    ChangeAssessment built through ChangeAssessment.from_dict, so the same
    validation the real agent gets from change_policy.py (acceptance ids
    must be non-empty and real for system_bug/missing_requirement) is
    exercised here too, not bypassed."""
    def __init__(self, category, reason='because', acceptance_ids=()):
        self.category = category
        self.reason = reason
        self.acceptance_ids = acceptance_ids
        self.calls = 0

    def classify(self, *, spec, followup):
        self.calls += 1
        self.last_followup = followup
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


class NeverRepairs:
    def __init__(self):
        self.calls = 0

    def repair(self, **kwargs):
        self.calls += 1
        return parse_patch({'files': [{'path': 'app.py', 'content': 'STILL_BROKEN'}]})


class Unreachable:
    """Fails the test loudly if the modifier engine calls it when it
    shouldn't (ambiguous/change_request must not touch repair or the
    sandbox; max_repair_rounds=0 must not call the repairer at all)."""
    def repair(self, **kwargs):
        raise AssertionError('repairer must not be called for this path')

    def execute(self, **kwargs):
        raise AssertionError('executor must not be called for this path')


class Executor:
    def __init__(self):
        self.calls = 0

    def execute(self, *, repository, spec):
        self.calls += 1
        if repository.get('app.py') == 'WORKING':
            return ExecutionReport(True)
        return ExecutionReport(False, (AcceptanceFailure('A1', 'not working', 'app.py'),), 'failed')


def _spec():
    return ProductSpec.from_dict(SPEC)


class NeedsClarificationTests(unittest.TestCase):
    def test_ambiguous_does_not_touch_repair_or_sandbox(self):
        engine = ModifierEngine(
            classifier=Classifier('ambiguous', reason='unclear what they want'),
            repairer=Unreachable(),
            executor=Unreachable(),
        )
        original = {'app.py': 'BROKEN'}
        result = engine.modify(spec=_spec(), repository=original, followup='make it better')
        self.assertEqual(result.status, 'needs_clarification')
        self.assertEqual(result.repair_rounds, 0)
        self.assertIsNone(result.report)
        self.assertEqual(result.repository, original)
        self.assertIsNot(result.repository, original)  # copy, not aliased

    def test_ambiguous_returned_repository_does_not_alias_the_input(self):
        engine = ModifierEngine(
            classifier=Classifier('ambiguous'),
            repairer=Unreachable(),
            executor=Unreachable(),
        )
        original = {'app.py': 'BROKEN'}
        result = engine.modify(spec=_spec(), repository=original, followup='???')
        result.repository['app.py'] = 'MUTATED'
        self.assertEqual(original['app.py'], 'BROKEN')


class ChangeRequestTests(unittest.TestCase):
    def test_change_request_is_classified_but_not_executed(self):
        classifier = Classifier('change_request', reason='wants a calendar view', acceptance_ids=())
        engine = ModifierEngine(classifier=classifier, repairer=Unreachable(), executor=Unreachable())
        original = {'app.py': 'BROKEN'}
        result = engine.modify(spec=_spec(), repository=original, followup='add a calendar view')
        self.assertEqual(result.status, 'change_request_not_supported')
        self.assertTrue(result.billable)
        self.assertEqual(result.assessment.category, 'change_request')
        self.assertEqual(result.assessment.reason, 'wants a calendar view')
        self.assertEqual(result.repair_rounds, 0)
        self.assertIsNone(result.report)
        self.assertEqual(result.repository, original)
        self.assertEqual(classifier.calls, 1)


class FreeRepairTests(unittest.TestCase):
    def test_missing_requirement_applies_after_one_repair_round(self):
        repairer = RepairsOnFirstTry()
        executor = Executor()
        engine = ModifierEngine(
            classifier=Classifier('missing_requirement', reason='list is empty', acceptance_ids=['A1']),
            repairer=repairer,
            executor=executor,
            max_repair_rounds=3,
        )
        result = engine.modify(
            spec=_spec(), repository={'app.py': 'BROKEN'}, followup='the todo list never shows anything',
        )
        self.assertEqual(result.status, 'applied')
        self.assertFalse(result.billable)
        self.assertEqual(result.repair_rounds, 1)
        self.assertEqual(result.repository['app.py'], 'WORKING')
        self.assertTrue(result.report.passed)
        self.assertEqual(executor.calls, 1)

    def test_system_bug_repair_failures_carry_the_classifier_reason_and_followup(self):
        repairer = RepairsOnFirstTry()
        engine = ModifierEngine(
            classifier=Classifier('system_bug', reason='home route 500s', acceptance_ids=['A1']),
            repairer=repairer,
            executor=Executor(),
        )
        engine.modify(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='home page crashes for me')
        self.assertEqual(len(repairer.calls), 1)
        failures = repairer.calls[0]['failures']
        self.assertEqual(failures, [{'acceptance_id': 'A1', 'message': 'home route 500s', 'evidence': 'home page crashes for me'}])

    def test_never_converging_repair_stops_at_max_rounds_and_reports_failed(self):
        repairer = NeverRepairs()
        engine = ModifierEngine(
            classifier=Classifier('system_bug', reason='still broken', acceptance_ids=['A1']),
            repairer=repairer,
            executor=Executor(),
            max_repair_rounds=2,
        )
        result = engine.modify(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='still broken')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.repair_rounds, 2)
        self.assertEqual(repairer.calls, 2)
        self.assertFalse(result.report.passed)

    def test_zero_max_repair_rounds_never_calls_the_repairer_but_still_verifies(self):
        executor = Executor()
        engine = ModifierEngine(
            classifier=Classifier('missing_requirement', reason='x', acceptance_ids=['A1']),
            repairer=Unreachable(),
            executor=executor,
            max_repair_rounds=0,
        )
        result = engine.modify(spec=_spec(), repository={'app.py': 'BROKEN'}, followup='fix it')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.repair_rounds, 0)
        self.assertEqual(executor.calls, 1)
        self.assertIsNotNone(result.report)


class InputValidationTests(unittest.TestCase):
    def test_empty_followup_rejected(self):
        engine = ModifierEngine(classifier=Classifier('ambiguous'), repairer=Unreachable(), executor=Unreachable())
        with self.assertRaises(ValueError):
            engine.modify(spec=_spec(), repository={'app.py': 'x'}, followup='   ')

    def test_empty_repository_rejected(self):
        engine = ModifierEngine(classifier=Classifier('ambiguous'), repairer=Unreachable(), executor=Unreachable())
        with self.assertRaises(ValueError):
            engine.modify(spec=_spec(), repository={}, followup='fix it')

    def test_negative_max_repair_rounds_rejected(self):
        with self.assertRaises(ValueError):
            ModifierEngine(classifier=Classifier('ambiguous'), repairer=Unreachable(), executor=Unreachable(), max_repair_rounds=-1)


if __name__ == '__main__':
    unittest.main()
