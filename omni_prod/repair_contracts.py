"""Versioned contracts for the EXISTING autonomous repair path.

Additive, side-effect-free validation. This module never opens an AI provider,
executes shell commands or changes billing/approval. It translates a validated
RepairPatchV1 to the pre-existing FilePatch contract.

Feature use is gated in autonomous_agents.RepairAgent; legacy JSON stays the
unchanged default until the actual worker/sandbox acceptance gates pass.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .repository_patch import FilePatch, PatchValidationError, normalize_repo_path

MAX_CHANGES = 12
MAX_BYTES_PER_FILE = 96_000
MAX_PATCH_BYTES = 240_000
MAX_LOG_CHARS = 3_000
MAX_CANDIDATES = 12
_PROTECTED_PARTS = frozenset(('.git', '.github', '.venv', 'venv', 'node_modules', '__pycache__', '.secrets'))
_SECRET_FILE = re.compile(r'(^|/)(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials(?:\..*)?|'
                          r'[^/]+\.(?:pem|key|p12|pfx))$', re.I)
_TEST_FILE = re.compile(r'(^|/)(?:tests?|__tests__|specs?)/|(^|/)test_[^/]+\.py$|\.(?:test|spec)\.[a-z]+$', re.I)
_DEPENDENCY_FILE = re.compile(r'(^|/)(?:package(?:-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|'
                              r'pyproject\.toml|requirements(?:-[^/]*)?\.txt|Pipfile(?:\.lock)?|'
                              r'poetry\.lock|uv\.lock|Dockerfile)$', re.I)
_SENSITIVE_TEXT = [
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(r'(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'(?<![A-Za-z0-9])AIza[A-Za-z0-9_-]{25,}'),
    re.compile(r'(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,}'),
]
_REDACT = [
    re.compile(r'(?i)\b(?:postgres(?:ql)?|redis(?:s)?)://[^\s"\']+'),
    re.compile(r'(?i)\b(?:authorization\s*:\s*bearer)\s+\S+'),
    re.compile(r'(?i)\b[A-Z_]*(?:API_KEY|ACCESS_TOKEN|SECRET_KEY|PASSWORD)\s*[:=]\s*[^\s;,]+'),
    *_SENSITIVE_TEXT,
]


def sanitized_tail(raw: str, *, limit: int = MAX_LOG_CHARS) -> str:
    if not isinstance(raw, str):
        raise ValueError('log evidence must be text')
    for rx in _REDACT:
        raw = rx.sub('[REDACTED]', raw)
    return raw[-limit:]


def repository_fingerprint(repository: dict[str, str]) -> str:
    return 'sha256:' + hashlib.sha256(json.dumps(sorted(repository.items())).encode('utf-8')).hexdigest()


def safe_patch_path(path: str, *, allow_tests: bool = False,
                    allow_dependency_changes: bool = False) -> str:
    if not isinstance(path, str):
        raise PatchValidationError('path must be a string')
    normalized = normalize_repo_path(path)
    if path != normalized or path == '.' or path.endswith('/'):
        raise PatchValidationError('noncanonical repository path')
    parts = PurePosixPath(path).parts
    if any(x in _PROTECTED_PARTS for x in parts):
        raise PatchValidationError('protected directory')
    if _SECRET_FILE.search(path):
        raise PatchValidationError('secret/private key path forbidden')
    if path == '.omni/project.json':
        raise PatchValidationError('approved manifest cannot be altered by automatic repair')
    if _TEST_FILE.search(path) and not allow_tests:
        raise PatchValidationError('acceptance/test files cannot be altered by automatic repair')
    if _DEPENDENCY_FILE.search(path) and not allow_dependency_changes:
        raise PatchValidationError('dependency manifest needs separate policy authorization')
    return path


class StrictContract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)

    @field_validator('schema_version', mode='before', check_fields=False)
    @classmethod
    def _schema_version_integer(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('schema_version must be integer 1')
        return value


class CandidateFile(StrictContract):
    path: str = Field(min_length=1, max_length=320)
    reason: str = Field(min_length=1, max_length=180)
    confidence: Literal['HIGH', 'MEDIUM']

    @field_validator('path')
    @classmethod
    def _path(cls, value: str) -> str:
        return safe_patch_path(value, allow_tests=True, allow_dependency_changes=True)


class RepairFailureV1(StrictContract):
    schema_version: Literal[1] = 1
    build_id: str = Field(min_length=1, max_length=120)
    attempt_id: str = Field(min_length=1, max_length=120)
    accepted_spec_fingerprint: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    repository_fingerprint: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    stage: Literal['COMPILE', 'UNIT', 'ACCEPTANCE', 'BROWSER', 'QUALITY', 'SECURITY']
    error_code: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    exit_code: int | None = None
    stdout_tail: str = Field(max_length=MAX_LOG_CHARS)
    stderr_tail: str = Field(max_length=MAX_LOG_CHARS)
    failing_acceptance_ids: list[str] = Field(default_factory=list, max_length=30)
    candidate_files: list[CandidateFile] = Field(default_factory=list, max_length=MAX_CANDIDATES)
    artifact_refs: list[str] = Field(default_factory=list, max_length=15)

    @field_validator('stdout_tail', 'stderr_tail')
    @classmethod
    def _logs(cls, value: str) -> str:
        if sanitized_tail(value) != value:
            raise ValueError('unsanitized or oversized evidence')
        return value


class RepairChange(StrictContract):
    path: str = Field(min_length=1, max_length=320)
    operation: Literal['UPSERT', 'DELETE']
    content: str | None = None

    @field_validator('path')
    @classmethod
    def _path(cls, value: str) -> str:
        return safe_patch_path(value, allow_tests=True, allow_dependency_changes=True)

    @model_validator(mode='after')
    def _content(self):
        if self.operation == 'UPSERT' and not isinstance(self.content, str):
            raise ValueError('UPSERT needs text content')
        if self.operation == 'DELETE' and self.content is not None:
            raise ValueError('DELETE must have null content')
        if self.content is not None and len(self.content.encode('utf-8')) > MAX_BYTES_PER_FILE:
            raise ValueError('file content exceeds byte ceiling')
        return self


class RepairPatchV1(StrictContract):
    schema_version: Literal[1] = 1
    reason_code: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    base_repository_fingerprint: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    changes: list[RepairChange] = Field(min_length=1, max_length=MAX_CHANGES)
    repaired_acceptance_ids: list[str] = Field(default_factory=list, max_length=30)
    summary: str = Field(max_length=350)
    requires_dependency_change: bool = False

    @model_validator(mode='after')
    def _unique(self):
        paths = [x.path for x in self.changes]
        if len(paths) != len(set(paths)):
            raise ValueError('duplicate changed path')
        if len(set(self.repaired_acceptance_ids)) != len(self.repaired_acceptance_ids):
            raise ValueError('duplicate acceptance id')
        if sum(len((x.content or '').encode('utf-8')) for x in self.changes) > MAX_PATCH_BYTES:
            raise ValueError('patch exceeds total byte ceiling')
        return self


class EvidenceCheck(StrictContract):
    name: str = Field(min_length=1, max_length=120)
    status: Literal['PASS', 'FAIL', 'NOT_RUN']
    exit_code: int | None = None
    log_ref: str | None = Field(default=None, max_length=250)

    @model_validator(mode='after')
    def _outcome(self):
        if self.status == 'NOT_RUN' and self.exit_code is not None:
            raise ValueError('NOT_RUN check cannot have an exit code')
        if self.status == 'PASS' and self.exit_code != 0:
            raise ValueError('PASS requires actual exit code zero')
        if self.status == 'FAIL' and (self.exit_code is None or self.exit_code == 0):
            raise ValueError('FAIL requires nonzero exit code')
        return self


class ExecutionEvidenceV1(StrictContract):
    schema_version: Literal[1] = 1
    build_id: str = Field(min_length=1, max_length=120)
    round: int = Field(ge=0, le=3)
    source_sha: str = Field(pattern=r'^[a-f0-9]{40}$')
    sandbox_adapter: Literal['docker', 'e2b']
    workspace_digest: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    checks: list[EvidenceCheck] = Field(min_length=1, max_length=40)
    external_model_cost_usd: str
    artifact_digest: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    tested_at: str = Field(min_length=10, max_length=40)

    @field_validator('external_model_cost_usd')
    @classmethod
    def _decimal(cls, value: str) -> str:
        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError('invalid Decimal cost') from exc
        if not amount.is_finite() or amount < 0:
            raise ValueError('cost must be finite and nonnegative')
        return value


def validated_file_patches(raw: dict, *, base_fingerprint: str,
                           approved_acceptance_ids: set[str],
                           allowed_dependency_changes: bool = False) -> tuple[FilePatch, ...]:
    """Convert untrusted model data to the existing FilePatch after checks."""
    try:
        patch = RepairPatchV1.model_validate(raw)
    except ValidationError:
        raise PatchValidationError('invalid structured repair contract') from None
    if patch.base_repository_fingerprint != base_fingerprint:
        raise PatchValidationError('repair base fingerprint does not match current repository')
    if not set(patch.repaired_acceptance_ids).issubset(approved_acceptance_ids):
        raise PatchValidationError('repair mentions acceptance outside approved contract')
    if patch.requires_dependency_change and not allowed_dependency_changes:
        raise PatchValidationError('dependency changes require separate explicit policy authorization')
    files: list[FilePatch] = []
    for change in patch.changes:
        safe_patch_path(change.path, allow_tests=False, allow_dependency_changes=allowed_dependency_changes)
        if change.operation == 'DELETE':
            raise PatchValidationError('automatic file deletion requires separate approval')
        for rx in _SENSITIVE_TEXT:
            if rx.search(change.content or ''):
                raise PatchValidationError('patch contains a credential or private key signature')
        files.append(FilePatch(change.path, change.content))
    return tuple(files)


def attributed_files(repository: dict[str, str], *, stdout: str = '', stderr: str = '',
                     max_candidates: int = MAX_CANDIDATES) -> list[dict]:
    """Traceback/compile references only; ambiguous basenames are NOT guessed."""
    log = sanitized_tail((stdout or '') + '\n' + (stderr or ''), limit=20_000)
    paths = sorted(repository)
    matched: list[dict] = []
    for path in paths:
        if not path or len(path) > 320:
            continue
        if '/' in path and re.search(r'(?<![A-Za-z0-9_./-])' + re.escape(path) + r'(?![A-Za-z0-9_./-])', log):
            matched.append({'path': path, 'reason': 'exact source path in diagnostics', 'confidence': 'HIGH'})
    basename_map: dict[str, list[str]] = {}
    for path in paths:
        basename_map.setdefault(path.rsplit('/', 1)[-1], []).append(path)
    for name, candidates in sorted(basename_map.items()):
        if len(candidates) != 1:
            continue
        path = candidates[0]
        if path in {x['path'] for x in matched} or not re.search(r'(?<![A-Za-z0-9_./-])' + re.escape(name) + r'(?![A-Za-z0-9_./-])', log):
            continue
        matched.append({'path': path, 'reason': 'unique filename in diagnostics', 'confidence': 'MEDIUM'})
    return matched[:max_candidates]
