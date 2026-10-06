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
    def _summary(repo: dict[str, str]) -> dict:
        return {
            'files': [{'path': p, 'chars': len(c)} for p, c in sorted(repo.items())],
            'file_count': len(repo),
            'total_chars': sum(len(c) for c in repo.values()),
        }

    @staticmethod
    def _fingerprint(repo: dict[str, str]) -> str:
        return hashlib.sha256(json.dumps(sorted(repo.items())).encode('utf-8')).hexdigest()

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
        rounds = 0
        seen = {self._fingerprint(repo)}
        stop_reason = 'passed' if report.passed else 'max_repair_rounds'
        while not report.passed and rounds < self.max_repair_rounds:
            rounds += 1
            failures = [f.__dict__ for f in report.failures]
            patch = self.repairer.repair(
                spec=spec,
                repo_summary=self._summary(repo),
                failures=failures,
            )
            candidate = apply_patch(repo, patch)
            fingerprint = self._fingerprint(candidate)
            if fingerprint in seen:
                # `repo` and `report` stay paired: the rejected candidate is not adopted.
                stop_reason = ('no_progress_repository_unchanged' if candidate == repo
                               else 'no_progress_repository_cycle')
                break
            seen.add(fingerprint)
            repo = candidate
            report = self.executor.execute(repository=repo, spec=spec)
            if report.passed:
                stop_reason = 'passed'
        return AutonomousResult(
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
            stop_reason,
        )
