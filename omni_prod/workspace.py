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

# M4D.1: sentinel meaning "commit() should not compare against any expected
# current version -- unconditional commit," which is the behavior every
# call site had before M4D.1 and the only behavior most of them still want
# (ordinary builds have no concept of a competing candidate). `None` is not
# usable for this because it is itself a meaningful expectation ("I expect
# this project to have no version yet"). Any code that wants the atomic
# compare-and-abort passes a real version id (or None for "expect empty")
# as `expected_current_version_id`; anything else keeps working unchanged.
SKIP_VERSION_CHECK = object()


class VersionConflict(Exception):
    """Raised by `commit(..., expected_current_version_id=...)` when the
    project's actual current version does not match what the caller
    expected. Raised BEFORE any row is inserted / any version is appended --
    the compare happens inside the same lock (MemoryProjectWorkspace's
    `self._lock`) or the same advisory-locked transaction
    (PostgresProjectWorkspace, via `pg_advisory_xact_lock` + a plain SELECT
    read, both issued against the same cursor right before the INSERT) that
    would otherwise perform the write, so `current()` for this project is
    guaranteed unchanged by a call that raises this. A caller must never
    treat "the commit already happened, now let me check if it should not
    have" as equivalent to this -- that is exactly the M4D.1 bug this
    exception exists to make impossible: a conflict is detected and refused
    strictly before the mutation, not audited after it."""
    def __init__(self, *, project_id: str, expected_current_version_id, actual_current_version_id):
        self.project_id = project_id
        self.expected_current_version_id = expected_current_version_id
        self.actual_current_version_id = actual_current_version_id
        super().__init__(
            f'project {project_id!r}: expected current version '
            f'{expected_current_version_id!r}, found {actual_current_version_id!r} instead'
        )


class WorkspaceProtocol(Protocol):
    def commit(self, *, project_id: str, repository: dict[str, str], message: str,
               expected_current_version_id=SKIP_VERSION_CHECK, cur=None) -> ProjectVersion: ...
    def history(self, project_id: str) -> tuple[ProjectVersion, ...]: ...
    def current(self, project_id: str) -> ProjectVersion | None: ...
    def get(self, *, project_id: str, version_id: str) -> ProjectVersion: ...
    def restore(self, *, project_id: str, version_id: str, message: str = 'restore',
                cur=None) -> ProjectVersion: ...

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

    def commit(self, *, project_id: str, repository: dict[str, str], message: str,
               expected_current_version_id=SKIP_VERSION_CHECK, cur=None) -> ProjectVersion:
        """M4D.1: `expected_current_version_id` is checked against the real
        current parent INSIDE the same `self._lock` acquisition that
        performs the append -- there is no separate earlier read that a
        second thread could slip in behind. A mismatch raises
        VersionConflict before `bucket.append(version)` ever runs, so a
        rejected commit provably never changes `current()`/`history()`.

        `cur` is accepted for interface parity with PostgresProjectWorkspace
        (so callers like modification_repository.accept() can pass the same
        keyword to either implementation) but is unused here -- this
        in-memory workspace has no SQL connection to share; its own
        `self._lock` is already the full extent of its concurrency control.
        """
        if not project_id or not message.strip(): raise ValueError('project_id and message required')
        for path in repository: normalize_repo_path(path)
        with self._lock:
            bucket = self._versions.setdefault(project_id, [])
            parent = bucket[-1].id if bucket else None
            if expected_current_version_id is not SKIP_VERSION_CHECK and parent != expected_current_version_id:
                raise VersionConflict(project_id=project_id,
                                       expected_current_version_id=expected_current_version_id,
                                       actual_current_version_id=parent)
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

    def restore(self, *, project_id: str, version_id: str, message: str = 'restore', cur=None) -> ProjectVersion:
        target = self.get(project_id=project_id, version_id=version_id)
        return self.commit(project_id=project_id, repository=target.repository(), message=message, cur=cur)

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

    def commit(self, *, project_id: str, repository: dict[str, str], message: str,
               expected_current_version_id=SKIP_VERSION_CHECK, cur=None) -> ProjectVersion:
        """M4D.1: the expected-version compare happens INSIDE the same
        advisory-locked read that determines `parent_id` -- `_do()` below
        takes `pg_advisory_xact_lock`, reads the real current version, and
        either raises VersionConflict (no INSERT issued at all) or proceeds
        straight to the INSERT, all against one cursor with the lock held
        throughout. There is no separate earlier read a concurrent
        transaction could slip in behind, and no later "was this actually
        right" check after the row already exists -- unlike a post-commit
        check, this cannot observe a state where the conflict is detected
        but the write already landed, because the write physically cannot
        happen once the mismatch is found (same statement ordering, same
        cursor, same lock).

        `cur`: pass an existing cursor to participate in the CALLER's
        already-open transaction (e.g. modification_repository.accept()
        merging this insert with its own ModificationRequest read/update and
        the ProductSpec insert into one atomic unit) instead of this method
        opening its own connection. When `cur` is None (every pre-M4D.1
        caller), behavior is unchanged: this method owns its own connection,
        transaction and advisory lock, exactly as before.
        """
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

        def _do(active_cur):
            # Deterministic, Postgres-safe lock using SHA-256 slice (fits in 64-bit int)
            lock_id = int(sha256(project_id.encode()).hexdigest()[:15], 16)
            active_cur.execute("SELECT pg_advisory_xact_lock(%s)", (lock_id,))

            active_cur.execute("SELECT id FROM project_versions WHERE project_id = %s ORDER BY created_at DESC LIMIT 1", (project_id,))
            parent_row = active_cur.fetchone()
            parent_id = parent_row[0] if parent_row else None

            if expected_current_version_id is not SKIP_VERSION_CHECK and parent_id != expected_current_version_id:
                raise VersionConflict(project_id=project_id,
                                       expected_current_version_id=expected_current_version_id,
                                       actual_current_version_id=parent_id)

            active_cur.execute(
                "INSERT INTO project_versions(id, project_id, parent_id, repository_sha256, message, created_at, artifact_key, file_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (version_id, project_id, parent_id, checksum, message.strip(), now, artifact_key, len(repository))
            )
            return parent_id

        if cur is not None:
            parent_id = _do(cur)
        else:
            with self.pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as owned_cur:
                        parent_id = _do(owned_cur)

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

    def restore(self, *, project_id: str, version_id: str, message: str = 'restore', cur=None) -> ProjectVersion:
        target = self.get(project_id=project_id, version_id=version_id)
        return self.commit(project_id=project_id, repository=target.repository(), message=message, cur=cur)

ProjectWorkspace = MemoryProjectWorkspace
