from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import threading
from .repository_patch import normalize_repo_path

@dataclass(frozen=True)
class ProjectVersion:
    id: str
    project_id: str
    parent_id: str | None
    files: tuple[tuple[str, str], ...]
    created_at: str
    message: str
    checksum: str
    def repository(self) -> dict[str, str]: return dict(self.files)

class ProjectWorkspace:
    """Thread-safe immutable version store used by reviewer/local runtime.

    Production may back the same semantics with PostgreSQL, but version IDs and
    parent relationships must remain atomic under concurrent requests.
    """
    def __init__(self):
        self._versions: dict[str, list[ProjectVersion]] = {}
        self._lock=threading.RLock()

    @staticmethod
    def _checksum(repo: dict[str, str]) -> str:
        h=sha256()
        for path,content in sorted(repo.items()): h.update(path.encode());h.update(b'\0');h.update(content.encode());h.update(b'\0')
        return h.hexdigest()

    def commit(self, *, project_id: str, repository: dict[str, str], message: str) -> ProjectVersion:
        if not project_id or not message.strip(): raise ValueError('project_id and message required')
        for path in repository: normalize_repo_path(path)
        with self._lock:
            bucket=self._versions.setdefault(project_id,[]); parent=bucket[-1].id if bucket else None
            version=ProjectVersion(id=f'{project_id}-v{len(bucket)+1:05d}',project_id=project_id,parent_id=parent,
                files=tuple(sorted(repository.items())),created_at=datetime.now(timezone.utc).isoformat(),message=message.strip(),checksum=self._checksum(repository))
            bucket.append(version); return version

    def history(self, project_id: str) -> tuple[ProjectVersion, ...]:
        with self._lock: return tuple(self._versions.get(project_id,()))
    def current(self, project_id: str) -> ProjectVersion | None:
        with self._lock:
            items=self._versions.get(project_id,()); return items[-1] if items else None
    def get(self, *, project_id: str, version_id: str) -> ProjectVersion:
        with self._lock:
            target=next((v for v in self._versions.get(project_id,()) if v.id==version_id),None)
            if target is None: raise KeyError(version_id)
            return target
    def restore(self, *, project_id: str, version_id: str, message: str = 'restore') -> ProjectVersion:
        with self._lock:
            target=next((v for v in self._versions.get(project_id,()) if v.id==version_id),None)
            if target is None: raise KeyError(version_id)
            repo=target.repository()
        return self.commit(project_id=project_id,repository=repo,message=message)
