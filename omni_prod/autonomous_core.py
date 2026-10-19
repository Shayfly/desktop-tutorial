from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol
from .product_spec import ProductSpec
from .repository_patch import apply_patch

@dataclass(frozen=True)
class AcceptanceFailure:
    acceptance_id: str
    message: str
    evidence: str = ''

# A one-line summary of the OTHER failing post-build checks of a round (VerificationGroup): it tells the repairer what
# else fails without counting as a verification stage, so progress() skips it.
SUMMARY_FAILURE_ID = 'ALSO_FAILING'
# Absolute cap on repair rounds whatever the plan (Studio = 8): bounds spend if a ceiling is ever misconfigured.
REPAIR_ROUNDS_HARD_MAX = 8


@dataclass(frozen=True)
class ExecutionReport:
    passed: bool
    failures: tuple[AcceptanceFailure, ...] = ()
    build_log: str = ''

@dataclass(frozen=True)
class AutonomousResult:
    status: str
    spec: ProductSpec
    repository: dict[str, str]
    repair_rounds: int
    report: ExecutionReport
    stop_reason: str = ''

class Executor(Protocol):
    def execute(self, *, repository: dict[str, str], spec: ProductSpec) -> ExecutionReport:
        ...

class AutonomousProductEngine:
    def __init__(self, *, architect, generator, repairer, executor: Executor,
                 max_repair_rounds: int = 3, repair_ceiling: int = 3):
        if isinstance(max_repair_rounds, bool) or not isinstance(max_repair_rounds, int) or max_repair_rounds < 0:
            raise ValueError('max_repair_rounds must be a non-negative integer')
        self.architect = architect
        self.generator = generator
        self.repairer = repairer
        self.executor = executor
        # J3/T05: initial build + at most three repair candidates, each verified.
        # Clamp even stale environment overrides; never spend on a fourth repair.
        # 2026-10-19 seam: a caller that knows the plan may pass repair_ceiling (pricing.repair_rounds_for_plan, up to
        # REPAIR_ROUNDS_HARD_MAX). No caller does yet, so the ceiling stays 3 everywhere.
        if isinstance(repair_ceiling, bool) or not isinstance(repair_ceiling, int) or not 0 <= repair_ceiling <= REPAIR_ROUNDS_HARD_MAX:
            raise ValueError(f'repair_ceiling must be an integer 0..{REPAIR_ROUNDS_HARD_MAX}')
        self.max_repair_rounds = min(max_repair_rounds, repair_ceiling)

    @staticmethod
    def _summary(repo: dict[str, str], failures=()) -> dict:
        # Golden E2E #1 build bld_85cc573b473341e9b3f10d248d743ff1: five repair
        # rounds could not list acceptance ids in .omni/project.json because the
        # repair agent saw only {path, chars}. Same bounded content summary the
        # modification path uses.
        from .modifier_engine import repo_summary
        return repo_summary(repo, failures)

    def _repair_summary(self, repo, failures=()):
        transform = getattr(self, 'repository_transform', None)
        original_fingerprint = self._fingerprint(repo)
        if transform is not None and hasattr(transform, 'redact'):
            repo = transform.redact(repo)
        summary = dict(self._summary(repo, failures))
        summary['base_repository_fingerprint'] = 'sha256:' + original_fingerprint
        from .repair_contracts import attributed_files
        diagnostic = '\n'.join(str(f.get('message', '')) + '\n' + str(f.get('evidence', ''))
                               for f in failures if isinstance(f, dict))
        summary['candidate_files'] = attributed_files(repo, stderr=diagnostic)
        return summary

    @staticmethod
    def _fingerprint(repo: dict[str, str]) -> str:
        return hashlib.sha256(json.dumps(sorted(repo.items())).encode('utf-8')).hexdigest()

    # Directive 2026-10-10 P0.3: every verified candidate is handed to this
    # hook (the worker stores it durably) before the next repair; the loop
    # itself rolls back to the best candidate when a repair goes backwards.
    round_hook = None

    def _snapshot(self, index: int, repo: dict, report, decision: str) -> None:
        if self.round_hook is None:
            return
        try:
            self.round_hook(index, repo, report, decision, self.progress(report))
        except Exception:  # a snapshot must never change the build
            import logging
            logging.getLogger(__name__).warning('round snapshot failed', exc_info=True)
            if getattr(self, 'require_durable_snapshots', False):
                # In verified strict mode, never claim READY without round evidence.
                raise

    def _observed_failures(self, report):
        """Every failure of a verified round for the taxonomy: the post-build group's full list when the round's
        report summarised some of them (ALSO_FAILING), otherwise the report's own failures."""
        if report.passed:
            return []
        own = [f for f in report.failures if f.acceptance_id != SUMMARY_FAILURE_ID]
        if len(own) == len(report.failures):
            return own
        group = getattr(self.executor, 'group_failures', None) or ()
        seen = {(f.acceptance_id, f.message) for f in own}
        return own + [f for f in group if (f.acceptance_id, f.message) not in seen]

    @staticmethod
    def progress(report) -> tuple[int, int]:
        """How far a candidate got through the verification chain (build ->
        unit tests -> acceptance tests -> preview -> behaviour -> browser ->
        quality -> review), then fewer failures. Higher is better."""
        if report.passed:
            return (11, 0)
        stage = 11
        # Chain order (investor_app): sandbox -> dependency gate -> preview ->
        # behaviour -> browser -> quality -> model review. A REVIEW failure
        # means everything before it passed (paid build bld_2be07937 ranked it
        # lowest and discarded the candidate whose behaviour had passed).
        later = {'REVIEW': 9, 'QUALITY': 8, 'VISUAL': 7, 'BROWSER': 6}
        for f in report.failures:
            msg, aid = (getattr(f, 'message', '') or '').lower(), getattr(f, 'acceptance_id', '')
            if aid == SUMMARY_FAILURE_ID:
                continue
            if aid in later:
                s = later[aid]
            elif aid == 'BEHAVIOR':
                s = 5
            elif aid == 'PREVIEW':
                s = 4
            elif 'acceptance tests' in msg:
                s = 3
            elif 'unit tests' in msg:
                s = 2
            elif 'build failed' in msg or 'install' in msg:
                s = 0
            else:
                s = 1
            stage = min(stage, s)
        return (stage, -len(report.failures))

    def build(self, prompt: str) -> AutonomousResult:
        """Generate, verify, repair.

        Basic stop-loss (founder decision 2026-10-07): the sandbox is
        deterministic (pinned image, no network), so verifying a repository
        state that was already verified cannot change the outcome. A repair
        that leaves the repository unchanged, or returns it to an earlier
        state, stops the loop instead of paying for more identical rounds.
        `stop_reason` records why the loop ended.
        """
        spec = self.architect.create_spec(prompt)
        initial = self.generator.generate(spec)
        repo = apply_patch({}, initial)
        if getattr(self,'repository_transform',None):
            repo = self.repository_transform(repo)
        report = self.executor.execute(repository=repo, spec=spec)
        self._taxonomy_rounds = [(0, self._observed_failures(report))]
        self._snapshot(0, repo, report, 'passed' if report.passed else 'initial')
        rounds = 0
        seen = {self._fingerprint(repo)}
        stop_reason = 'passed' if report.passed else 'max_repair_rounds'
        self.trace = []  # per round: what failed and what the repair changed (diagnostics only)
        # Paid builds 2026-10-09: a weaker repair turned "1 behaviour check
        # fails" into "build fails" and later rounds drifted further. A repair
        # that goes backwards is discarded; the next one starts from the best.
        best_repo, best_report = repo, report
        discarded_note = None
        while not report.passed and rounds < self.max_repair_rounds:
            rounds += 1
            failures = [f.__dict__ for f in report.failures]
            if discarded_note:
                failures = failures + [discarded_note]
                discarded_note = None
            transform = getattr(self, 'repository_transform', None)
            if transform is not None and hasattr(transform, 'redact_text'):
                failures = [{k: transform.redact_text(v) if isinstance(v, str) else v
                             for k, v in f.items()} for f in failures]
            patch = self.repairer.repair(
                spec=spec,
                repo_summary=self._repair_summary(repo, failures),
                failures=failures,
            )
            candidate = apply_patch(repo, patch)
            if getattr(self,'repository_transform',None):
                candidate = self.repository_transform(candidate)
            self.trace.append({
                'round': rounds,
                'failing': sorted({f['acceptance_id'] for f in failures}),
                'first_failure': (failures[0].get('message', '') + ' | ' + (failures[0].get('evidence') or '')[-300:])
                                 if failures else '',
                'changed': sorted(p for p in set(candidate) | set(repo) if candidate.get(p) != repo.get(p))[:12],
            })
            fingerprint = self._fingerprint(candidate)
            if fingerprint in seen:
                # `repo` and `report` stay paired: the rejected candidate is not adopted.
                stop_reason = ('no_progress_repository_unchanged' if candidate == repo
                               else 'no_progress_repository_cycle')
                break
            seen.add(fingerprint)
            new_report = self.executor.execute(repository=candidate, spec=spec)
            self._taxonomy_rounds.append((rounds, self._observed_failures(new_report)))
            worse = not new_report.passed and self.progress(new_report) < self.progress(best_report)
            self._snapshot(rounds, candidate, new_report,
                           'passed' if new_report.passed else ('discarded' if worse else 'adopted'))
            if new_report.passed:
                repo, report, stop_reason = candidate, new_report, 'passed'
                break
            if worse:
                failing = [f'{f.acceptance_id}: {f.message}' for f in new_report.failures][:4]
                self.trace[-1]['discarded'] = failing
                discarded_note = {'acceptance_id': 'REPAIR_REGRESSION',
                                  'message': 'Your previous change made the product worse and was discarded; this is '
                                             'the better version again. Do not repeat that change.',
                                  'evidence': '; '.join(failing)[:600]}
                repo, report = best_repo, best_report
                continue
            repo, report = candidate, new_report
            if self.progress(report) >= self.progress(best_report):
                best_repo, best_report = repo, report
        if not report.passed:
            repo, report = best_repo, best_report
        from .failure_taxonomy import records
        self.failure_taxonomy = records(self._taxonomy_rounds)
        self.first_pass = bool(self._taxonomy_rounds) and not self._taxonomy_rounds[0][1]
        return AutonomousResult(
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
            stop_reason,
        )
