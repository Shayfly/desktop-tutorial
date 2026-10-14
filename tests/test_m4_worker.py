"""Real unit tests for omni_prod/worker_tasks.py's M4 slice: _run_modification_job
and resolve_modification_billing.

Mirrors tests/test_m3_preview_logic.py's TestAsyncBuildGatesAndBilling /
BuildHarness pattern for _run_live_build_job -- same idea applied to
_run_modification_job: everything the *worker's own logic* decides (claiming,
loading the exact version-scoped spec, wiring CandidateModificationEngine,
billing resolution, terminal status + evidence written) is real and exercised
here with fakes for its collaborators (jobs/spec_repo/workspace/subscriptions
are fakes; the classifier/repairer/evolver/executor/quality/security/rights
fakes are the same shapes test_m4_modification_engine.py already uses, since
CandidateModificationEngine's own decision logic has its own dedicated tests
there and does not need re-proving here).

What is NOT exercised here: execute_modification_job() itself (the RQ
entrypoint) and _modification_components() (investor_app.py) -- both need
real Postgres/fastapi wiring this sandbox cannot provide, so they are
statically verified only (compileall + cross-reference against real call
sites), exactly like execute_live_build_job before them.

Run with: python3 -m unittest tests.test_m4_worker -v
"""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import worker_tasks
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.change_policy import ChangeAssessment
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import parse_patch
from omni_prod.spec_repository import SpecNotFound

SPEC = {
    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
}

EVOLVED_SPEC = {**SPEC, 'title': 'Todo Plus'}


# ===========================================================================
# Fakes -- same shapes as tests/test_m4_modification_engine.py, redefined
# locally (test modules don't import fixtures from one another).
# ===========================================================================

class Classifier:
    def __init__(self, category, reason='because', acceptance_ids=()):
        self.category = category
        self.reason = reason
        self.acceptance_ids = acceptance_ids
        self.calls = []

    def classify(self, *, spec, followup):
        self.calls.append(followup)
        return ChangeAssessment.from_dict(
            {'category': self.category, 'reason': self.reason, 'acceptance_ids': list(self.acceptance_ids)},
            spec=spec,
        )


class RepairsOnFirstTry:
    def repair(self, **kwargs):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'WORKING'}]})


class RaisingRepairer:
    def repair(self, **kwargs):
        raise RuntimeError('sandbox crashed mid-repair')


class Executor:
    def execute(self, *, repository, spec):
        if repository.get('app.py') == 'WORKING':
            return ExecutionReport(True)
        return ExecutionReport(False, (AcceptanceFailure('A1', 'not working', 'app.py'),), 'failed log')


class EvolverImmediatelyPassing:
    def __init__(self):
        self.calls = []

    def evolve(self, *, spec, repo_summary, followup):
        self.calls.append({'spec': spec, 'followup': followup})
        new_spec = ProductSpec.from_dict(EVOLVED_SPEC)
        patch = parse_patch({'files': [{'path': 'app.py', 'content': 'WORKING'}]})
        return new_spec, patch


class _FakeQuality:
    def __init__(self, passed, score=90, minimum_score=80, blockers=()):
        self.passed, self.score, self.minimum_score, self.blockers = passed, score, minimum_score, blockers

    def to_dict(self):
        return {'passed': self.passed, 'score': self.score}


class _FakeSecurity:
    def __init__(self, passed, findings=()):
        self.passed, self.findings = passed, findings

    def to_dict(self):
        return {'passed': self.passed, 'findings': list(self.findings)}


class FakeRightsEngine:
    def __init__(self, publish_allowed=True, status='CLEAR'):
        self.publish_allowed = publish_allowed
        self.status = status
        self.calls = []

    def assess(self, prompt, *, target_markets, evidence):
        self.calls.append({'prompt': prompt, 'target_markets': target_markets, 'evidence': tuple(evidence)})
        return SimpleNamespace(publish_allowed=self.publish_allowed, status=self.status,
                               to_dict=lambda: {'publish_allowed': self.publish_allowed, 'status': self.status})


class FakeModJobs:
    def __init__(self, request=None, claim=True, missing=False):
        self.request = request or {
            'project_id': 'tenant_abc', 'user_id': 'u1', 'source_version_id': 'v10',
            'followup': 'fix the login bug', 'target_markets': ('US',),
            'rights_evidence': [{'id': 'ev1', 'right_kind': 'trademark', 'subject': 'Acme',
                                 'evidence_type': 'license', 'scope': 'global'}],
        }
        self.claim = claim
        self.missing = missing
        self.completions: list[dict] = []

    def get_request(self, modification_id):
        if self.missing:
            raise KeyError('not found')
        return self.request

    def transition_running(self, modification_id):
        return self.claim

    def complete(self, modification_id, **kw):
        self.completions.append(kw)
        return True

    @property
    def final(self):
        return self.completions[-1]


class FakeSpecRepo:
    def __init__(self, raise_not_found=False):
        self.raise_not_found = raise_not_found

    def get(self, version_id, project_id):
        if self.raise_not_found:
            raise SpecNotFound(f'no spec for {version_id}')
        return ProductSpec.from_dict(SPEC)


def fake_workspace(repository=None):
    ws = MagicMock()
    repo = dict(repository or {'app.py': 'BROKEN'})
    ws.get.return_value = SimpleNamespace(repository=lambda: dict(repo))
    return ws


class ModHarness:
    def __init__(self, *, category='missing_requirement', acceptance_ids=('A1',),
                quality_ok=True, security_ok=True, rights_ok=True,
                spend='0', calls=0, request=None, factory_exc=None, repo=None,
                repairer=None, evolver=None, executor=None, claim=True, missing=False):
        self.jobs = FakeModJobs(request=request, claim=claim, missing=missing)
        self.spec_repo = FakeSpecRepo()
        self.workspace = fake_workspace(repo)
        self.subs = MagicMock()
        self.classifier = Classifier(category, acceptance_ids=acceptance_ids)
        self.repairer = repairer or RepairsOnFirstTry()
        self.evolver = evolver or EvolverImmediatelyPassing()
        self.executor = executor or Executor()
        self.gateway = SimpleNamespace(state=SimpleNamespace(external_spend_usd=Decimal(spend), external_calls=calls))
        self.factory_exc = factory_exc
        self.quality = _FakeQuality(quality_ok, 90 if quality_ok else 40, 80, () if quality_ok else ('no tests',))
        self.security = _FakeSecurity(security_ok, () if security_ok else ('secret',))
        self.rights = FakeRightsEngine(publish_allowed=rights_ok)

    def factory(self):
        if self.factory_exc:
            raise self.factory_exc
        return self.classifier, self.repairer, self.evolver, self.executor, self.gateway

    def run(self):
        return worker_tasks._run_modification_job(
            'mod_1', jobs=self.jobs, spec_repo=self.spec_repo, workspace=self.workspace,
            subscriptions=self.subs, components_factory=self.factory,
            quality_fn=lambda **kw: self.quality, security_fn=lambda repo: self.security,
            rights_engine=self.rights,
        )


class ResolveModificationBillingTests(unittest.TestCase):
    def test_billable_settles_at_actual_spend(self):
        subs = MagicMock()
        out = worker_tasks.resolve_modification_billing(
            subs, modification_id='mod_1', billable=True, spent=Decimal('0.50'), external_calls=2)
        self.assertEqual(out, 'settled')
        subs.settle.assert_called_once_with(build_id='mod_1', actual_provider_cost_usd=Decimal('0.50'))
        subs.release.assert_not_called()

    def test_not_billable_releases_even_with_real_spend(self):
        # Free-by-policy categories (system_bug/missing_requirement/ambiguous)
        # are never charged, even though real compute was spent producing them.
        subs = MagicMock()
        out = worker_tasks.resolve_modification_billing(
            subs, modification_id='mod_1', billable=False, spent=Decimal('0.35'), external_calls=1)
        self.assertEqual(out, 'released')
        subs.release.assert_called_once_with(build_id='mod_1')
        subs.settle.assert_not_called()


class RunModificationJobTests(unittest.TestCase):
    def test_missing_requirement_reaches_ready_for_review_and_is_free(self):
        h = ModHarness(category='missing_requirement', acceptance_ids=('A1',))
        self.assertEqual(h.run(), 'READY_FOR_REVIEW')
        f = h.jobs.final
        self.assertEqual(f['status'], 'READY_FOR_REVIEW')
        self.assertEqual(f['classification'], 'missing_requirement')
        self.assertFalse(f['billable'])
        self.assertEqual(f['candidate_repository'], {'app.py': 'WORKING'})
        self.assertEqual(f['candidate_spec'].title, 'Todo')  # unchanged spec, free-repair path
        h.subs.release.assert_called_once_with(build_id='mod_1')
        h.subs.settle.assert_not_called()
        self.assertIsNone(f['error_code'])
        # Acceptance K: the source version is never touched while a
        # candidate is built -- only workspace.get() (read) is used; commit()
        # is never called here at all (only accept() may call it, later, on
        # explicit promotion).
        h.workspace.commit.assert_not_called()

    def test_change_request_reaches_ready_for_review_and_settles_at_real_spend(self):
        h = ModHarness(category='change_request', spend='0.50', calls=2)
        self.assertEqual(h.run(), 'READY_FOR_REVIEW')
        f = h.jobs.final
        self.assertEqual(f['classification'], 'change_request')
        self.assertTrue(f['billable'])
        self.assertEqual(f['candidate_spec'].title, 'Todo Plus')  # evolved spec carried through
        h.subs.settle.assert_called_once_with(build_id='mod_1', actual_provider_cost_usd=Decimal('0.50'))
        self.assertEqual(h.evolver.calls[0]['followup'], 'fix the login bug')
        h.workspace.commit.assert_not_called()  # Acceptance K, change_request path too

    def test_ambiguous_needs_clarification_and_is_free_with_no_candidate(self):
        h = ModHarness(category='ambiguous', acceptance_ids=())
        self.assertEqual(h.run(), 'NEEDS_CLARIFICATION')
        f = h.jobs.final
        self.assertEqual(f['status'], 'NEEDS_CLARIFICATION')
        self.assertIsNone(f['candidate_repository'])
        self.assertIsNone(f['candidate_spec'])
        h.subs.release.assert_called_once_with(build_id='mod_1')

    def test_gate_failure_is_failed_with_the_blocking_gate_as_error_code(self):
        h = ModHarness(category='missing_requirement', quality_ok=False)
        self.assertEqual(h.run(), 'FAILED')
        f = h.jobs.final
        self.assertEqual(f['error_code'], 'quality')
        self.assertIsNone(f['candidate_repository'])  # never stored for a failed candidate
        h.subs.release.assert_called_once_with(build_id='mod_1')  # still free -- category-driven, not outcome-driven

    def test_rights_evidence_dicts_are_rebuilt_into_real_evidence_objects(self):
        h = ModHarness(category='missing_requirement')
        h.run()
        self.assertEqual(len(h.rights.calls), 1)
        evidence = h.rights.calls[0]['evidence']
        self.assertEqual(evidence[0].right_kind.value, 'trademark')
        self.assertEqual(h.rights.calls[0]['target_markets'], ('US',))

    def test_no_stored_spec_for_source_version_fails_cleanly_not_as_worker_exception_masking(self):
        # Terminal state is still durably recorded (jobs.complete) even though
        # the exception propagates afterward -- exactly like
        # _run_live_build_job's own exception path (see test_m3_preview_logic.py).
        h = ModHarness()
        h.spec_repo = FakeSpecRepo(raise_not_found=True)
        with self.assertRaises(RuntimeError):
            h.run()
        f = h.jobs.final
        self.assertEqual(f['status'], 'FAILED')
        self.assertEqual(f['error_code'], 'worker_exception')
        self.assertIn('no stored ProductSpec', f['error_message'])
        h.subs.release.assert_called_once_with(build_id='mod_1')  # no spend incurred

    def test_exception_with_real_spend_already_incurred_is_settled_not_released(self):
        h = ModHarness(spend='0.10', calls=1, repairer=RaisingRepairer())
        with self.assertRaises(RuntimeError):
            h.run()
        self.assertEqual(h.jobs.final['error_code'], 'worker_exception')
        h.subs.settle.assert_called_once_with(build_id='mod_1', actual_provider_cost_usd=Decimal('0.10'))
        h.subs.release.assert_not_called()

    def test_duplicate_delivery_is_a_noop(self):
        h = ModHarness(claim=False)
        self.assertIsNone(h.run())
        self.assertEqual(h.jobs.completions, [])
        h.subs.release.assert_not_called()
        h.subs.settle.assert_not_called()

    def test_unknown_modification_id_is_a_noop(self):
        h = ModHarness(missing=True)
        self.assertIsNone(h.run())
        self.assertEqual(h.jobs.completions, [])


if __name__ == '__main__':
    unittest.main()
