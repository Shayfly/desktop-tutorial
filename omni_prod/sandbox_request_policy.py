"""Fail-closed request validation for the EXISTING HMAC-authenticated Docker sandbox.

No new process runner, model provider or billing path. Strict argv allowlisting
remains feature-flagged until verified against the actual Docker QA commands.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
import re

from .repository_patch import normalize_repo_path, PatchValidationError

MAX_BODY_BYTES = 26_000_000
MAX_RESPONSE_BYTES = 512_000
MAX_REPO_FILES = 5_000
MAX_REPO_BYTES = 25_000_000
MAX_ARGC = 64
MAX_ARG_BYTES = 16_384
MAX_ARGV_BYTES = 128_000
MAX_PATH_BYTES = 1_024
MAX_TREE_DEPTH = 24
_BUILD_ID = re.compile(r'^[A-Za-z0-9._-]{1,120}$')
_HIDDEN_OR_PRIVATE = {'.git', '.ssh', '.aws', '.config', '.venv', 'node_modules', '__pycache__'}
_PRIVATE_FILE = re.compile(r'(^|/)(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials(?:\..*)?|[^/]+\.(?:pem|key|p12|pfx))$', re.I)
_ALLOWED_STRICT_EXECUTABLES = {'python', 'python3', 'pytest', 'node', 'npm', 'pnpm', 'yarn'}


class SandboxRequestRejected(ValueError):
    """Private input policy detail; do not echo raw args/paths over HTTP."""


def _bad(reason: str) -> None:
    raise SandboxRequestRejected(reason)


def validate_snapshot(repository: Mapping[str, str]) -> None:
    if not isinstance(repository, Mapping) or not repository or len(repository) > MAX_REPO_FILES:
        _bad('invalid repository inventory')
    total = 0
    files: set[str] = set()
    for path, content in repository.items():
        if not isinstance(path, str) or not isinstance(content, str):
            _bad('repository must contain text paths and text content')
        try:
            normalized = normalize_repo_path(path)
        except (PatchValidationError, TypeError):
            _bad('unsafe repository path')
        if (path != normalized or path in ('', '.') or path.endswith('/') or '\\' in path or
                len(path.encode('utf-8')) > MAX_PATH_BYTES or len(PurePosixPath(path).parts) > MAX_TREE_DEPTH or
                any(ord(c) < 32 or ord(c) == 127 for c in path)):
            _bad('noncanonical repository path')
        parts = PurePosixPath(path).parts
        if any(part.casefold() in _HIDDEN_OR_PRIVATE for part in parts) or (
                _PRIVATE_FILE.search(path) and parts[-1] not in ('.env.example', '.env.sample', '.env.template')):
            _bad('private or generated files not allowed inside build snapshot')
        if '\x00' in content:
            _bad('binary content forbidden in text-only snapshot')
        total += len(path.encode('utf-8')) + len(content.encode('utf-8'))
        if total > MAX_REPO_BYTES:
            _bad('repository byte budget exceeded')
        files.add(path)
    for path in files:
        bits = path.split('/')
        for depth in range(1, len(bits)):
            if '/'.join(bits[:depth]) in files:
                _bad('file/directory collision in repository')


def validate_command(argv: Sequence[str], *, build_id: str, strict: bool = False,
                     repository: Mapping[str, str] | None = None,
                     profile: str = 'default') -> None:
    if not isinstance(build_id, str) or not _BUILD_ID.fullmatch(build_id):
        _bad('invalid build id')
    if profile not in ('default', 'browser'):
        _bad('unknown sandbox profile')
    if (not isinstance(argv, (list, tuple)) or not argv or len(argv) > MAX_ARGC or
            any(not isinstance(arg, str) or not arg or '\x00' in arg or
                '\n' in arg or '\r' in arg or len(arg.encode('utf-8')) > MAX_ARG_BYTES for arg in argv)):
        _bad('invalid command arguments')
    if sum(len(arg.encode('utf-8')) for arg in argv) > MAX_ARGV_BYTES:
        _bad('command too large')
    if strict:
        if profile != 'default' or repository is None:
            _bad('strict mode requires supported default-profile manifest')
        from .project_manifest import ProjectManifest
        try:
            manifest = ProjectManifest.from_repository(dict(repository))
        except (TypeError, ValueError):
            _bad('strict mode requires valid manifest')
        allowed = set(manifest.build) | {tuple(check.argv) for check in manifest.verify}
        if tuple(argv) not in allowed:
            _bad('command not authorized by project manifest')
        exe = argv[0].rsplit('/', 1)[-1]
        if exe not in _ALLOWED_STRICT_EXECUTABLES:
            _bad('executable not allowlisted in strict manifest mode')
        if exe in ('python', 'python3', 'node') and len(argv) > 1 and argv[1] in ('-c', '-e', '--eval'):
            _bad('inline executable payload denied in strict manifest mode')
