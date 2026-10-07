from __future__ import annotations
from dataclasses import dataclass
import json

# The exact shape ProjectManifest.from_repository reads. Stated verbatim to the
# generator and repair agents: Golden E2E #1 on Preview (2026-10-07) failed
# with "at least one verification command required" because the prompts never
# named these keys and the model chose its own.
MANIFEST_SHAPE = (
    '.omni/project.json must use exactly these keys for building and verification: '
    '{"build": [["python", "-m", "compileall", "-q", "."]], '
    '"verify": [{"name": "unit tests", "argv": ["python", "-m", "pytest", "-q"], "acceptance_ids": ["A1", "A2"]}]}. '
    '"build" is a list of argv arrays (it may be empty). "verify" is a non-empty list; every entry has a name, an '
    'argv array and acceptance_ids naming only acceptance ids of the approved specification; together the entries '
    'cover every acceptance id. '
)

@dataclass(frozen=True)
class VerificationCommand:
    name: str
    argv: tuple[str, ...]
    acceptance_ids: tuple[str, ...]

@dataclass(frozen=True)
class ProjectManifest:
    build: tuple[tuple[str, ...], ...]
    verify: tuple[VerificationCommand, ...]

    @classmethod
    def from_repository(cls, repository: dict[str, str]) -> 'ProjectManifest':
        raw = repository.get('.omni/project.json')
        if raw is None:
            raise ValueError('generated repository missing .omni/project.json')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError('invalid .omni/project.json') from exc
        if not isinstance(data, dict):
            raise ValueError('project manifest root must be object')

        def argv(value) -> tuple[str, ...]:
            if not isinstance(value, list) or not value:
                raise ValueError('command argv must be non-empty list')
            out = tuple(str(x) for x in value)
            if any(not x or '\x00' in x for x in out):
                raise ValueError('invalid command argument')
            if len(out) > 64:
                raise ValueError('command too long')
            return out

        builds = tuple(argv(x) for x in data.get('build', []))
        if len(builds) > 16:
            raise ValueError('too many build commands')
        checks = []
        for item in data.get('verify', []):
            if not isinstance(item, dict):
                raise ValueError('verify entry must be object')
            name = str(item.get('name', '')).strip()
            ids = tuple(str(x).strip() for x in item.get('acceptance_ids', []) if str(x).strip())
            if not name or not ids:
                raise ValueError('verify command requires name and acceptance_ids')
            checks.append(VerificationCommand(name, argv(item.get('argv')), ids))
        if not checks:
            raise ValueError('at least one verification command required')
        if len(checks) > 64:
            raise ValueError('too many verification commands')
        return cls(builds, tuple(checks))


def invalid_manifest_report(error: Exception, spec):
    """An unusable manifest is a repository defect the repair loop can fix: it
    fails every acceptance criterion with the parser's exact reason instead of
    aborting the build before any repair round."""
    from .autonomous_core import AcceptanceFailure, ExecutionReport
    message = f'invalid .omni/project.json: {error}'[:500]
    return ExecutionReport(False, tuple(AcceptanceFailure(a.id, message, MANIFEST_SHAPE) for a in spec.acceptance),
                           message)


def uncovered_acceptance_failures(manifest: ProjectManifest, spec) -> tuple:
    """Acceptance criteria that no verification command claims are unverified,
    not passed. Golden E2E #1 (2026-10-07): a build passed sandbox verification
    with 4 of 7 criteria covered and was then rejected by the quality gate
    (traceability 57%) without a repair round. Reporting them as failures lets
    the repair loop add the missing tests."""
    from .autonomous_core import AcceptanceFailure
    covered = {aid for check in manifest.verify for aid in check.acceptance_ids}
    return tuple(
        AcceptanceFailure(
            a.id, 'no verification command covers this acceptance criterion',
            f'Add an automated test for "{a.text}" and list "{a.id}" in the acceptance_ids of a verify entry '
            f'in .omni/project.json. {MANIFEST_SHAPE}')
        for a in spec.acceptance if a.id not in covered)
