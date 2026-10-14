from __future__ import annotations
from dataclasses import dataclass
from .product_spec import ProductSpec

# M4F: "Do not rely on an LLM-only prose summary as the canonical diff." Every
# function in this module is a pure, deterministic function of two
# repositories/specs -- no model call, no randomness, same inputs always
# produce the same diff. An LLM-written prose explanation can be layered on
# top of this (not built here -- no directive asked for one), but this is the
# diff a caller can trust and re-derive independently.

_DEPENDENCY_MANIFESTS = {
    'requirements.txt', 'requirements-production.txt', 'requirements-demo.txt',
    'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'pyproject.toml', 'poetry.lock', 'Pipfile', 'Pipfile.lock',
    'Cargo.toml', 'Cargo.lock', 'go.mod', 'go.sum',
}
_SCHEMA_HINTS = ('.sql', '/migrations/', 'schema.sql', 'schema.prisma')
# Heuristic, not exhaustive (same disclaimer style as security_testing.py's
# hostile_repository_scan): a path/content hint that a change is worth a
# human's extra attention before accepting, not a security gate on its own --
# the real security gate is security_testing.hostile_repository_scan(),
# already run on every candidate by CandidateModificationEngine.
_SECURITY_SENSITIVE_HINTS = (
    'auth', 'login', 'password', 'secret', 'token', 'permission', 'security',
    'admin', '.env', 'cors', 'session', 'credential', 'webhook',
)


@dataclass(frozen=True)
class RepositoryDiff:
    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]
    dependency_manifests_changed: tuple[str, ...]
    schema_files_changed: tuple[str, ...]
    security_sensitive_files_changed: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            'added': list(self.added),
            'modified': list(self.modified),
            'deleted': list(self.deleted),
            'dependency_manifests_changed': list(self.dependency_manifests_changed),
            'schema_files_changed': list(self.schema_files_changed),
            'security_sensitive_files_changed': list(self.security_sensitive_files_changed),
        }

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.modified or self.deleted)


def diff_repositories(old: dict[str, str], new: dict[str, str]) -> RepositoryDiff:
    old_paths, new_paths = set(old), set(new)
    added = tuple(sorted(new_paths - old_paths))
    deleted = tuple(sorted(old_paths - new_paths))
    modified = tuple(sorted(p for p in (old_paths & new_paths) if old[p] != new[p]))
    changed = set(added) | set(modified) | set(deleted)

    def _basename(p: str) -> str:
        return p.rsplit('/', 1)[-1]

    dependency = tuple(sorted(p for p in changed if _basename(p) in _DEPENDENCY_MANIFESTS))
    schema = tuple(sorted(p for p in changed if any(h in p.lower() for h in _SCHEMA_HINTS)))
    sensitive = tuple(sorted(p for p in changed if any(h in p.lower() for h in _SECURITY_SENSITIVE_HINTS)))
    return RepositoryDiff(added, modified, deleted, dependency, schema, sensitive)


@dataclass(frozen=True)
class SpecDiff:
    title_changed: bool
    summary_changed: bool
    stack_added: tuple[str, ...]
    stack_removed: tuple[str, ...]
    requirements_added: tuple[str, ...]
    requirements_removed: tuple[str, ...]
    requirements_changed: tuple[str, ...]
    acceptance_added: tuple[str, ...]
    acceptance_removed: tuple[str, ...]
    acceptance_changed: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            'title_changed': self.title_changed,
            'summary_changed': self.summary_changed,
            'stack_added': list(self.stack_added),
            'stack_removed': list(self.stack_removed),
            'requirements_added': list(self.requirements_added),
            'requirements_removed': list(self.requirements_removed),
            'requirements_changed': list(self.requirements_changed),
            'acceptance_added': list(self.acceptance_added),
            'acceptance_removed': list(self.acceptance_removed),
            'acceptance_changed': list(self.acceptance_changed),
        }

    @property
    def is_empty(self) -> bool:
        return not (
            self.title_changed or self.summary_changed or self.stack_added or self.stack_removed
            or self.requirements_added or self.requirements_removed or self.requirements_changed
            or self.acceptance_added or self.acceptance_removed or self.acceptance_changed
        )


def diff_specs(old: ProductSpec, new: ProductSpec) -> SpecDiff:
    old_stack, new_stack = set(old.stack), set(new.stack)
    old_reqs = {r.id: r for r in old.requirements}
    new_reqs = {r.id: r for r in new.requirements}
    old_acc = {a.id: a for a in old.acceptance}
    new_acc = {a.id: a for a in new.acceptance}

    req_changed = tuple(sorted(
        rid for rid in (set(old_reqs) & set(new_reqs))
        if old_reqs[rid] != new_reqs[rid]
    ))
    acc_changed = tuple(sorted(
        aid for aid in (set(old_acc) & set(new_acc))
        if old_acc[aid] != new_acc[aid]
    ))
    return SpecDiff(
        title_changed=old.title != new.title,
        summary_changed=old.summary != new.summary,
        stack_added=tuple(sorted(new_stack - old_stack)),
        stack_removed=tuple(sorted(old_stack - new_stack)),
        requirements_added=tuple(sorted(set(new_reqs) - set(old_reqs))),
        requirements_removed=tuple(sorted(set(old_reqs) - set(new_reqs))),
        requirements_changed=req_changed,
        acceptance_added=tuple(sorted(set(new_acc) - set(old_acc))),
        acceptance_removed=tuple(sorted(set(old_acc) - set(new_acc))),
        acceptance_changed=acc_changed,
    )


@dataclass(frozen=True)
class ModificationDiff:
    repository: RepositoryDiff
    spec: SpecDiff

    def to_dict(self) -> dict:
        return {'repository': self.repository.to_dict(), 'spec': self.spec.to_dict()}


def diff_modification(*, old_repository: dict[str, str], new_repository: dict[str, str],
                       old_spec: ProductSpec, new_spec: ProductSpec) -> ModificationDiff:
    return ModificationDiff(
        repository=diff_repositories(old_repository, new_repository),
        spec=diff_specs(old_spec, new_spec),
    )
