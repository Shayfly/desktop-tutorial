from __future__ import annotations
from pathlib import Path
import tempfile
from typing import Callable
from .autonomous_core import ExecutionReport, AcceptanceFailure
from .product_spec import ProductSpec
from .project_manifest import ProjectManifest
from .sandbox import SandboxLimits, run_sandbox
from .repository_patch import normalize_repo_path

def _materialize_repository(root: Path, repository: dict[str, str]) -> None:
    for rel, content in repository.items():
        safe = normalize_repo_path(rel)
        path = root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

# M2 Revision 4 (native adaptation): close the fake-verification loophole.
# A generated manifest must not be able to "pass" acceptance by proposing a
# verification command that trivially succeeds without exercising anything --
# most obviously `["true"]`, or any command that shells out to `echo` instead
# of running a real test framework. These are rejected before self.runner is
# ever invoked for them, so the sandbox can never be asked to "confirm" a
# no-op as a pass.
def _is_fake_verification(argv: tuple[str, ...]) -> bool:
    if tuple(argv) == ('true',):
        return True
    return any(token == 'echo' for token in argv)

class SandboxRepositoryExecutor:
    def __init__(
        self,
        *,
        limits: SandboxLimits,
        runner: Callable = run_sandbox,
        build_id_factory: Callable[[], str] | None = None,
    ):
        self.limits = limits
        self.runner = runner
        self.build_id_factory = build_id_factory or (lambda: 'autonomous-check')

    def execute(self, *, repository: dict[str, str], spec: ProductSpec) -> ExecutionReport:
        manifest = ProjectManifest.from_repository(repository)
        valid_acceptance = {a.id for a in spec.acceptance}
        failures = []
        logs = []
        with tempfile.TemporaryDirectory(prefix='omni-repo-') as td, \
             tempfile.TemporaryDirectory(prefix='omni-out-') as out:
            root = Path(td)
            _materialize_repository(root, repository)
            counter = 0
            for command in manifest.build:
                counter += 1
                result = self.runner(
                    source_dir=root,
                    build_id=f'{self.build_id_factory()}-b{counter}',
                    limits=self.limits,
                    command=list(command),
                    output_dir=out,
                )
                logs.append(result.stdout)
                logs.append(result.stderr)
                if result.returncode != 0:
                    return ExecutionReport(
                        False,
                        tuple(
                            AcceptanceFailure(a.id, 'build command failed', result.stderr[-2000:])
                            for a in spec.acceptance
                        ),
                        '\n'.join(logs)[-10000:],
                    )

            for check in manifest.verify:
                unknown = [x for x in check.acceptance_ids if x not in valid_acceptance]
                if unknown:
                    raise ValueError('verification references unknown acceptance ids: ' + ','.join(unknown))

                if _is_fake_verification(check.argv):
                    # Never trust a no-op as evidence of a pass. Fail every
                    # acceptance id this check claimed to cover, and do not
                    # spend a sandbox run on it.
                    for aid in check.acceptance_ids:
                        failures.append(
                            AcceptanceFailure(
                                aid,
                                f'verification failed: {check.name}',
                                '[FATAL] Fake verification command detected. You must write an '
                                'executable test framework (pytest, jest, etc).',
                            )
                        )
                    continue

                counter += 1
                result = self.runner(
                    source_dir=root,
                    build_id=f'{self.build_id_factory()}-t{counter}',
                    limits=self.limits,
                    command=list(check.argv),
                    output_dir=out,
                )
                logs.append(result.stdout)
                logs.append(result.stderr)
                if result.returncode != 0:
                    for aid in check.acceptance_ids:
                        failures.append(
                            AcceptanceFailure(
                                aid,
                                f'verification failed: {check.name}',
                                result.stderr[-2000:],
                            )
                        )
        return ExecutionReport(
            passed=not failures,
            failures=tuple(failures),
            build_log='\n'.join(logs)[-10000:],
        )
