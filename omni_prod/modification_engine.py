from __future__ import annotations
from dataclasses import dataclass
from .product_spec import ProductSpec
from .change_policy import ChangeAssessment
from .autonomous_core import ExecutionReport, Executor
from .repository_patch import apply_patch
from .modifier_engine import repo_summary, run_free_repair
from .modification_diff import ModificationDiff, diff_modification

# M4C/D/E: this module is the pure, testable core of M4 -- it never touches
# durable storage, never enqueues anything, and never mutates the accepted
# version. It takes (spec, repository, followup), returns a *candidate*
# (repository, spec, gate results, diff) or a reason nothing was produced.
# Promotion to "accepted" is a separate, explicit step
# (modification_repository.PostgresModificationRepository.accept()) that only
# a caller invokes -- never this engine.


@dataclass(frozen=True)
class GateResult:
    passed: bool
    blocking_gate: str | None  # 'verification' | 'quality' | 'security' | 'rights' | None
    detail: str | None
    quality: object | None
    security: object | None
    rights: object | None

    def to_dict(self) -> dict:
        return {
            'passed': self.passed,
            'blocking_gate': self.blocking_gate,
            'detail': self.detail,
            'quality': self.quality.to_dict() if self.quality is not None else None,
            'security': self.security.to_dict() if self.security is not None else None,
            'rights': self.rights.to_dict() if self.rights is not None else None,
        }


@dataclass(frozen=True)
class CandidateOutcome:
    # 'ready_for_review'  -- candidate built, all gates passed, awaiting ACCEPT/REJECT
    # 'failed'            -- candidate built but failed verification/quality/security/rights
    # 'needs_clarification' -- ambiguous followup; nothing built
    # 'change_request_not_supported' -- reserved for parity with ModifierEngine;
    #    CandidateModificationEngine itself never returns this (see class
    #    docstring), kept only so callers can pattern-match both engines'
    #    status vocabularies the same way.
    status: str
    assessment: ChangeAssessment
    source_repository: dict[str, str]
    source_spec: ProductSpec
    candidate_repository: dict[str, str]
    candidate_spec: ProductSpec
    repair_rounds: int
    report: ExecutionReport | None
    gates: GateResult | None
    diff: ModificationDiff | None
    billable: bool

    def to_evidence_dict(self) -> dict:
        """Durable evidence_json shape, matching worker_tasks.py's build
        evidence dict convention (gates + repair_rounds + verification)."""
        return {
            'status': self.status,
            'classification': self.assessment.category,
            'classification_reason': self.assessment.reason,
            'billable': self.billable,
            'repair_rounds': self.repair_rounds,
            'verification': None if self.report is None else {
                'passed': self.report.passed,
                'failures': [
                    {'acceptance_id': f.acceptance_id, 'message': f.message, 'evidence': f.evidence}
                    for f in self.report.failures
                ],
                'build_log_tail': self.report.build_log[-4000:],
            },
            'gates': None if self.gates is None else self.gates.to_dict(),
            'diff': None if self.diff is None else self.diff.to_dict(),
        }


class CandidateModificationEngine:
    """M4's "propose a candidate" engine.

    Composes only already-real, already-tested pieces:
      - `classifier` (ChangeClassifierAgent) / `ChangeAssessment` -- M4C intent
        routing, reused verbatim from the M4 foundation.
      - `modifier_engine.run_free_repair` -- the exact system_bug/
        missing_requirement loop `ModifierEngine.modify()` uses, extracted so
        it can be driven here with an assessment already computed once (see
        `run_free_repair`'s docstring for why classifying twice was rejected).
      - `evolver` (product_evolution.ProductEvolutionAgent) -- the new,
        dedicated change_request path M4C explicitly requires instead of
        forcing that category through RepairAgent.
      - `quality_fn` / `security_fn` / `rights_engine` -- the same three
        gates `worker_tasks.evaluate_release_gates` already applies to a
        *build*, applied here to a *candidate modification* (M4E). No new
        gate logic invented; same functions, same thresholds.
      - `modification_diff.diff_modification` -- the deterministic diff M4F
        asks for.

    `propose()` never writes anywhere and never touches `source_repository`
    in place (M4D: "never patch the current accepted version destructively").
    Its result is handed to a caller that decides what to persist -- in this
    codebase, `worker_tasks.execute_modification_job` (statically verified
    only here; see STATUS.md) writes the candidate as a new, unpromoted
    `ProjectVersion` + `ProductSpec` row and stores this outcome as the
    modification's evidence, exactly the way `_run_live_build_job` already
    stores a `AutonomousResult`'s evidence for a build.
    """

    def __init__(self, *, classifier, repairer, executor: Executor, evolver,
                 quality_fn, security_fn, rights_engine, min_quality: int = 80,
                 max_repair_rounds: int = 3):
        if max_repair_rounds < 0:
            raise ValueError('max_repair_rounds cannot be negative')
        self.classifier = classifier
        self.repairer = repairer
        self.executor = executor
        self.evolver = evolver
        self.quality_fn = quality_fn
        self.security_fn = security_fn
        self.rights = rights_engine
        self.min_quality = min_quality
        self.max_repair_rounds = max_repair_rounds

    def _evolve_and_verify(self, *, spec: ProductSpec, repository: dict[str, str],
                            followup: str) -> tuple[dict[str, str], ProductSpec, int, ExecutionReport]:
        new_spec, patch = self.evolver.evolve(spec=spec, repo_summary=repo_summary(repository), followup=followup)
        repo = apply_patch(dict(repository), patch)
        report = self.executor.execute(repository=repo, spec=new_spec)
        failures = [f.__dict__ for f in report.failures]
        rounds = 0
        # Same bounded, self-correcting shape as AutonomousProductEngine.build()
        # and run_free_repair() -- verify, and if it doesn't pass yet, hand the
        # real failures to RepairAgent against the *new* spec (the candidate's
        # spec, not the original) until it passes or the round budget runs out.
        while failures and rounds < self.max_repair_rounds:
            rounds += 1
            repair_patch = self.repairer.repair(spec=new_spec, repo_summary=repo_summary(repo), failures=failures)
            repo = apply_patch(repo, repair_patch)
            report = self.executor.execute(repository=repo, spec=new_spec)
            failures = [f.__dict__ for f in report.failures]
        return repo, new_spec, rounds, report

    def _evaluate_gates(self, *, report: ExecutionReport | None, spec: ProductSpec,
                         repository: dict[str, str], followup: str,
                         target_markets: tuple[str, ...], rights_evidence: tuple) -> GateResult:
        if report is None or not report.passed:
            return GateResult(False, 'verification', 'candidate did not pass sandbox verification', None, None, None)
        quality = self.quality_fn(spec=spec, repository=repository, minimum_score=self.min_quality)
        if not quality.passed:
            blockers = '; '.join(getattr(quality, 'blockers', ()) or ()) or 'no blocker detail'
            return GateResult(False, 'quality', f'quality score {quality.score} below minimum {quality.minimum_score} ({blockers})',
                               quality, None, None)
        security = self.security_fn(repository)
        if not security.passed:
            return GateResult(False, 'security', f'hostile repository scan: {len(security.findings)} finding(s)',
                               quality, security, None)
        # M4E: "rights/provenance gate". The closest analog to a build's
        # original user prompt is the followup text itself -- it is the new
        # natural-language input that could introduce a new rights-sensitive
        # reference (e.g. "add a Mario-style mascot"); the accepted source
        # repository already passed this gate once when it was built/accepted.
        rights = self.rights.assess(followup, target_markets=target_markets, evidence=rights_evidence)
        if not rights.publish_allowed:
            status = getattr(rights.status, 'value', rights.status)
            return GateResult(False, 'rights', f'rights status {status}: not releasable until rights evidence is added',
                               quality, security, rights)
        return GateResult(True, None, None, quality, security, rights)

    def propose(self, *, spec: ProductSpec, repository: dict[str, str], followup: str,
                target_markets: tuple[str, ...] = ('US', 'EU', 'IL'), rights_evidence: tuple = ()) -> CandidateOutcome:
        if not followup.strip():
            raise ValueError('followup cannot be empty')
        if not repository:
            raise ValueError('repository cannot be empty -- nothing to modify')

        assessment = self.classifier.classify(spec=spec, followup=followup)

        if assessment.category == 'ambiguous':
            return CandidateOutcome('needs_clarification', assessment, repository, spec,
                                     dict(repository), spec, 0, None, None, None, assessment.billable)

        if assessment.category == 'change_request':
            candidate_repo, candidate_spec, rounds, report = self._evolve_and_verify(
                spec=spec, repository=repository, followup=followup)
        else:
            candidate_repo, rounds, report = run_free_repair(
                spec=spec, repository=repository, assessment=assessment, followup=followup,
                repairer=self.repairer, executor=self.executor, max_repair_rounds=self.max_repair_rounds,
            )
            # M4B: free repair fixes the *implementation* of an existing,
            # already-accepted requirement; it never changes what the product
            # is contracted to do. Only change_request may produce a new spec.
            candidate_spec = spec

        gates = self._evaluate_gates(
            report=report, spec=candidate_spec, repository=candidate_repo, followup=followup,
            target_markets=target_markets, rights_evidence=rights_evidence,
        )
        diff = diff_modification(old_repository=repository, new_repository=candidate_repo,
                                  old_spec=spec, new_spec=candidate_spec)
        status = 'ready_for_review' if gates.passed else 'failed'
        return CandidateOutcome(status, assessment, repository, spec, candidate_repo, candidate_spec,
                                 rounds, report, gates, diff, assessment.billable)
