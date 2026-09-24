from __future__ import annotations
from dataclasses import dataclass
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

    def build(self, prompt: str) -> AutonomousResult:
        spec = self.architect.create_spec(prompt)
        initial = self.generator.generate(spec)
        repo = apply_patch({}, initial)
        report = self.executor.execute(repository=repo, spec=spec)
        rounds = 0
        while not report.passed and rounds < self.max_repair_rounds:
            rounds += 1
            failures = [f.__dict__ for f in report.failures]
            patch = self.repairer.repair(
                spec=spec,
                repo_summary=self._summary(repo),
                failures=failures,
            )
            repo = apply_patch(repo, patch)
            report = self.executor.execute(repository=repo, spec=spec)
        return AutonomousResult(
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
        )
