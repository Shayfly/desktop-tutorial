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
                 max_repair_rounds: int = 3):
        if max_repair_rounds < 0:
            raise ValueError('max_repair_rounds cannot be negative')
        self.architect = architect
        self.generator = generator
        self.repairer = repairer
        self.executor = executor
        self.max_repair_rounds = max_repair_rounds

    @staticmethod
    def _summary(repo: dict[str, str], failures=()) -> dict:
        # Golden E2E #1 build bld_85cc573b473341e9b3f10d248d743ff1: five repair
        # rounds could not list acceptance ids in .omni/project.json because the
        # repair agent saw only {path, chars}. Same bounded content summary the
        # modification path uses.
        from .modifier_engine import repo_summary
        return repo_summary(repo, failures)

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
        report = self.executor.execute(repository=repo, spec=spec)
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
            patch = self.repairer.repair(
                spec=spec,
                repo_summary=self._summary(repo, failures),
                failures=failures,
            )
            candidate = apply_patch(repo, patch)
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
        return AutonomousResult(
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
            stop_reason,
        )
