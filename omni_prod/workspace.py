from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import uuid
import threading
import zipfile
from typing import Protocol, Callable
from .repository_patch import normalize_repo_path

@dataclass(frozen=True)
class ProjectVersion:
    id: str
    project_id: str
    parent_id: str | None
    created_at: str
    message: str
    checksum: str
    _repository_loader: Callable[[], dict[str, str]] | None = None
    artifact_key: str | None = None
    file_count: int = 0

    @property
    def files(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self.repository().items()))

    def repository(self) -> dict[str, str]:
        if self._repository_loader is None:
            raise RuntimeError("Repository content not loaded in this context")
        return self._repository_loader()

class WorkspaceProtocol(Protocol):
    def commit(self, *, project_id: str, repository: dict[str, str], message: str) -> ProjectVersion: ...
    def history(self, project_id: str) -> tuple[ProjectVersion, ...]: ...
    def current(self, project_id: str) -> ProjectVersion | None: ...
    def get(self, *, project_id: str, version_id: str) -> ProjectVersion: ...
    def restore(self, *, project_id: str, version_id: str, message: str = 'restore') -> ProjectVersion: ...

def _checksum(repo: dict[str, str]) -> str:
    h = sha256()
    for path, content in sorted(repo.items()):
        h.update(path.encode()); h.update(b'\0')
        h.update(content.encode()); h.update(b'\0')
    return h.hexdigest()

class MemoryProjectWorkspace(WorkspaceProtocol):
    """Legacy/Test in-memory workspace. Retained for V28 compatibility."""
    def __init__(self):
        self._versions: dict[str, list[ProjectVersion]] = {}
        self._lock = threading.RLock()

    def commit(self, *, project_id: str, repository: dict[str, str], message: str) -> ProjectVersion:
        if not project_id or not message.strip(): raise ValueError('project_id and message required')
        for path in repository: normalize_repo_path(path)
        with self._lock:
            bucket = self._versions.setdefault(project_id, [])
            parent = bucket[-1].id if bucket else None
            vid = f'{project_id}-v{len(bucket)+1:05d}'
            captured_repo = dict(repository)
            version = ProjectVersion(id=vid, project_id=project_id, parent_id=parent, created_at=datetime.now(timezone.utc).isoformat(), message=message.strip(), checksum=_checksum(repository), file_count=len(repository), _repository_loader=lambda: dict(captured_repo))
            bucket.append(version)
            return version

    def history(self, project_id: str) -> tuple[ProjectVersion, ...]:
        with self._lock: return tuple(self._versions.get(project_id, ()))

    def current(self, project_id: str) -> ProjectVersion | None:
        with self._lock:
            items = self._versions.get(project_id, ())
            return items[-1] if items else None

    def get(self, *, project_id: str, version_id: str) -> ProjectVersion:
        with self._lock:
            target = next((v for v in self._versions.get(project_id, ()) if v.id == version_id), None)
            if target is None: raise KeyError(version_id)
            return target

    def restore(self, *, project_id: str, version_id: str, message: str = 'restore') -> ProjectVersion:
        target = self.get(project_id=project_id, version_id=version_id)
        return self.commit(project_id=project_id, repository=target.repository(), message=message)

class PostgresProjectWorkspace(WorkspaceProtocol):
    """Production concurrent workspace with S3 content-addressed artifacts."""
    def __init__(self, pool, artifact_store):
        self.pool = pool
        self.storage = artifact_store

    def _zip_repo(self, repo: dict[str, str]) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path, content in repo.items(): zf.writestr(path, content)
        return out.getvalue()

    def _unzip_repo(self, zip_data: bytes) -> dict[str, str]:
        repo = {}
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
            for name in zf.namelist(): repo[name] = zf.read(name).decode('utf-8')
        return repo

    def commit(self, *, project_id: str, repository: dict[str, str], message: str) -> ProjectVersion:
        if not project_id or not message.strip(): raise ValueError('project_id and message required')
        for path in repository: normalize_repo_path(path)

        checksum = _checksum(repository)
        now = datetime.now(timezone.utc).isoformat()

        version_id = f"v_{uuid.uuid4().hex[:16]}"
        artifact_key = f"repositories/{checksum}.zip"

        try:
            self.storage.get_bytes(artifact_key, verify=False)
        except Exception:
            self.storage.put_bytes(artifact_key, self._zip_repo(repository))

        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    # Deterministic, Postgres-safe lock using SHA-256 slice (fits in 64-bit int)
                    lock_id = int(sha256(project_id.encode()).hexdigest()[:15], 16)
                    cur.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))

                    cur.execute("SELECT id FROM project_versions WHERE project_id = %s ORDER BY created_at DESC LIMIT 1", (project_id,))
                    parent_row = cur.fetchone()
                    parent_id = parent_row[0] if parent_row else None

                    cur.execute(
                        "INSERT INTO project_versions(id, project_id, parent_id, repository_sha256, message, created_at, artifact_key, file_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (version_id, project_id, parent_id, checksum, message.strip(), now, artifact_key, len(repository))
                    )

        captured_repo = dict(repository)
        return ProjectVersion(id=version_id, project_id=project_id, parent_id=parent_id, created_at=now, message=message.strip(), checksum=checksum, artifact_key=artifact_key, file_count=len(repository), _repository_loader=lambda: dict(captured_repo))

    def _get_loader(self, artifact_key: str):
        def loader():
            zip_bytes = self.storage.get_bytes(artifact_key, verify=False)
            return self._unzip_repo(zip_bytes)
        return loader

    def history(self, project_id: str) -> tuple[ProjectVersion, ...]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, parent_id, created_at, message, repository_sha256, artifact_key, file_count FROM project_versions WHERE project_id = %s ORDER BY created_at ASC", (project_id,))
                rows = cur.fetchall()
        return tuple(ProjectVersion(id=r[0], project_id=project_id, parent_id=r[1], created_at=r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2]), message=r[3], checksum=r[4], artifact_key=r[5], file_count=r[6], _repository_loader=self._get_loader(r[5])) for r in rows)

    def current(self, project_id: str) -> ProjectVersion | None:
        history = self.history(project_id)
        return history[-1] if history else None

    def get(self, *, project_id: str, version_id: str) -> ProjectVersion:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT parent_id, created_at, message, repository_sha256, artifact_key, file_count FROM project_versions WHERE id = %s AND project_id = %s", (version_id, project_id))
                row = cur.fetchone()
        if not row: raise KeyError(version_id)
        return ProjectVersion(id=version_id, project_id=project_id, parent_id=row[0], created_at=row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]), message=row[2], checksum=row[3], artifact_key=row[4], file_count=row[5], _repository_loader=self._get_loader(row[4]))

    def restore(self, *, project_id: str, version_id: str, message: str = 'restore') -> ProjectVersion:
        target = self.get(project_id=project_id, version_id=version_id)
        return self.commit(project_id=project_id, repository=target.repository(), message=message)

ProjectWorkspace = MemoryProjectWorkspace
