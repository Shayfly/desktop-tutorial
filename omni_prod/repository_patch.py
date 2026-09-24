from __future__ import annotations
from dataclasses import dataclass
from pathlib import PurePosixPath

@dataclass(frozen=True)
class FilePatch:
    path: str
    content: str | None

class PatchValidationError(ValueError):
    pass

def normalize_repo_path(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or '..' in p.parts or '\\' in path or '\x00' in path:
        raise PatchValidationError(f'unsafe repository path: {path!r}')
    normalized = p.as_posix()
    if normalized.startswith('.git/') or normalized == '.git':
        raise PatchValidationError('cannot patch .git')
    return normalized

def parse_patch(payload: dict) -> tuple[FilePatch, ...]:
    raw = payload.get('files')
    if not isinstance(raw, list) or not raw:
        raise PatchValidationError('patch files must be non-empty list')
    out = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            raise PatchValidationError('patch entry must be object')
        path = normalize_repo_path(str(item.get('path', '')))
        if path in seen:
            raise PatchValidationError(f'duplicate patch path: {path}')
        seen.add(path)
        content = item.get('content')
        if content is not None and not isinstance(content, str):
            raise PatchValidationError('content must be string or null')
        out.append(FilePatch(path, content))
    return tuple(out)

def apply_patch(repo: dict[str, str], patches: tuple[FilePatch, ...], *,
                max_files: int = 2000, max_total_chars: int = 8_000_000) -> dict[str, str]:
    # M2 Revision 4 (native adaptation): normalize every patch path here too,
    # not only in parse_patch(). parse_patch() already runs each incoming
    # path through normalize_repo_path() -- the same pure lexical POSIX
    # normalizer used here -- which rejects absolute paths, NUL bytes and any
    # literal '..' component. But apply_patch() itself is also called
    # directly with hand-built FilePatch objects that bypass parse_patch()
    # (see omni_prod/v27_platform.py's build()/`_refresh_rights_manifest()
    # call sites), so re-validating inside apply_patch() closes that gap for
    # every caller uniformly instead of relying on each call site to have
    # pre-validated. Re-normalizing an already-normalized path is a no-op, so
    # existing callers are unaffected.
    result = dict(repo)
    for patch in patches:
        safe_path = normalize_repo_path(patch.path)
        if patch.content is None:
            result.pop(safe_path, None)
        else:
            result[safe_path] = patch.content
    if len(result) > max_files:
        raise PatchValidationError('repository file limit exceeded')
    if sum(len(x) for x in result.values()) > max_total_chars:
        raise PatchValidationError('repository size limit exceeded')
    return result
