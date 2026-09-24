from __future__ import annotations
from dataclasses import dataclass
import json

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
