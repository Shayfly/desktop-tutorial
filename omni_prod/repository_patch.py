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
    result = dict(repo)
    for patch in patches:
        if patch.content is None:
            result.pop(patch.path, None)
        else:
            result[patch.path] = patch.content
    if len(result) > max_files:
        raise PatchValidationError('repository file limit exceeded')
    if sum(len(x) for x in result.values()) > max_total_chars:
        raise PatchValidationError('repository size limit exceeded')
    return result
