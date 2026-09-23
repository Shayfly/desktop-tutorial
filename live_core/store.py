from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    created_at: datetime


@dataclass(frozen=True)
class SessionRecord:
    id: str
    user_id: str
    token_digest: str
    created_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    owner_id: str
    title: str
    active_version_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ArtifactRecord:
    id: str
    owner_id: str
    project_id: str
    sha256: str
    size_bytes: int
    data: bytes
    created_at: datetime


@dataclass(frozen=True)
class VersionRecord:
    id: str
    owner_id: str
    project_id: str
    artifact_id: str
    prompt: str
    parent_version_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class BuildRecord:
    id: str
    owner_id: str
    project_id: str
    prompt: str
    stage: str
    status: str
    error: str | None
    version_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class BuildEventRecord:
    id: str
    build_id: str
    stage: str
    message: str
    created_at: datetime


class Store(Protocol):
    def create_user(self, email: str, password_hash: str) -> UserRecord: ...
    def get_user(self, user_id: str) -> UserRecord | None: ...
    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def create_session(self, user_id: str, token_digest: str) -> SessionRecord: ...
    def get_session_by_digest(self, token_digest: str) -> SessionRecord | None: ...
    def revoke_session(self, token_digest: str) -> bool: ...
    def create_project(self, owner_id: str, title: str) -> ProjectRecord: ...
    def list_projects(self, owner_id: str) -> list[ProjectRecord]: ...
    def get_project(self, project_id: str, owner_id: str | None = None) -> ProjectRecord | None: ...
    def set_active_version(self, project_id: str, owner_id: str, version_id: str | None) -> ProjectRecord: ...
    def create_build(self, owner_id: str, project_id: str, prompt: str) -> BuildRecord: ...
    def get_build(self, build_id: str, owner_id: str | None = None) -> BuildRecord | None: ...
    def update_build(self, build_id: str, *, stage: str | None = None, status: str | None = None, error: str | None = None, version_id: str | None = None) -> BuildRecord: ...
    def append_build_event(self, build_id: str, stage: str, message: str = "") -> BuildEventRecord: ...
    def get_build_events(self, build_id: str) -> list[str]: ...
    def get_build_event_records(self, build_id: str) -> list[BuildEventRecord]: ...
    def create_artifact(self, owner_id: str, project_id: str, sha256: str, data: bytes) -> ArtifactRecord: ...
    def get_artifact(self, artifact_id: str, owner_id: str | None = None) -> ArtifactRecord | None: ...
    def create_version(self, owner_id: str, project_id: str, artifact_id: str, prompt: str, parent_version_id: str | None = None) -> VersionRecord: ...
    def get_version(self, version_id: str, owner_id: str | None = None) -> VersionRecord | None: ...
    def list_versions(self, project_id: str, owner_id: str) -> list[VersionRecord]: ...


class MemoryStore:
    """Local/test store. Never selected implicitly in production."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.users: dict[str, UserRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self.projects: dict[str, ProjectRecord] = {}
        self.builds: dict[str, BuildRecord] = {}
        self.events: dict[str, list[BuildEventRecord]] = {}
        self.artifacts: dict[str, ArtifactRecord] = {}
        self.versions: dict[str, VersionRecord] = {}

    def create_user(self, email: str, password_hash: str) -> UserRecord:
        normalized = email.strip().lower()
        with self._lock:
            if self.get_user_by_email(normalized):
                raise ValueError("email already exists")
            record = UserRecord(str(uuid4()), normalized, password_hash, utcnow())
            self.users[record.id] = record
            return record

    def get_user(self, user_id: str) -> UserRecord | None:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        return next((u for u in self.users.values() if u.email == normalized), None)

    def create_session(self, user_id: str, token_digest: str) -> SessionRecord:
        with self._lock:
            record = SessionRecord(str(uuid4()), user_id, token_digest, utcnow())
            self.sessions[record.id] = record
            return record

    def get_session_by_digest(self, token_digest: str) -> SessionRecord | None:
        return next((s for s in self.sessions.values() if s.token_digest == token_digest and s.revoked_at is None), None)

    def revoke_session(self, token_digest: str) -> bool:
        with self._lock:
            for sid, session in self.sessions.items():
                if session.token_digest == token_digest and session.revoked_at is None:
                    self.sessions[sid] = replace(session, revoked_at=utcnow())
                    return True
        return False

    def create_project(self, owner_id: str, title: str) -> ProjectRecord:
        now = utcnow()
        record = ProjectRecord(str(uuid4()), owner_id, title, None, now, now)
        with self._lock:
            self.projects[record.id] = record
        return record

    def list_projects(self, owner_id: str) -> list[ProjectRecord]:
        return sorted((p for p in self.projects.values() if p.owner_id == owner_id), key=lambda p: p.updated_at, reverse=True)

    def get_project(self, project_id: str, owner_id: str | None = None) -> ProjectRecord | None:
        project = self.projects.get(project_id)
        if project and owner_id is not None and project.owner_id != owner_id:
            return None
        return project

    def set_active_version(self, project_id: str, owner_id: str, version_id: str | None) -> ProjectRecord:
        with self._lock:
            project = self.get_project(project_id, owner_id)
            if not project:
                raise KeyError("project not found")
            updated = replace(project, active_version_id=version_id, updated_at=utcnow())
            self.projects[project_id] = updated
            return updated

    def create_build(self, owner_id: str, project_id: str, prompt: str) -> BuildRecord:
        now = utcnow()
        record = BuildRecord(str(uuid4()), owner_id, project_id, prompt, "planning", "running", None, None, now, now)
        with self._lock:
            self.builds[record.id] = record
            self.events[record.id] = []
        return record

    def get_build(self, build_id: str, owner_id: str | None = None) -> BuildRecord | None:
        build = self.builds.get(build_id)
        if build and owner_id is not None and build.owner_id != owner_id:
            return None
        return build

    def update_build(self, build_id: str, *, stage: str | None = None, status: str | None = None, error: str | None = None, version_id: str | None = None) -> BuildRecord:
        with self._lock:
            build = self.builds.get(build_id)
            if not build:
                raise KeyError("build not found")
            updated = replace(
                build,
                stage=stage if stage is not None else build.stage,
                status=status if status is not None else build.status,
                error=error,
                version_id=version_id if version_id is not None else build.version_id,
                updated_at=utcnow(),
            )
            self.builds[build_id] = updated
            return updated

    def append_build_event(self, build_id: str, stage: str, message: str = "") -> BuildEventRecord:
        if build_id not in self.builds:
            raise KeyError("build not found")
        event = BuildEventRecord(str(uuid4()), build_id, stage, message, utcnow())
        with self._lock:
            self.events.setdefault(build_id, []).append(event)
        return event

    def get_build_events(self, build_id: str) -> list[str]:
        return [event.stage for event in self.events.get(build_id, [])]

    def get_build_event_records(self, build_id: str) -> list[BuildEventRecord]:
        return list(self.events.get(build_id, []))

    def create_artifact(self, owner_id: str, project_id: str, sha256: str, data: bytes) -> ArtifactRecord:
        record = ArtifactRecord(str(uuid4()), owner_id, project_id, sha256, len(data), bytes(data), utcnow())
        with self._lock:
            self.artifacts[record.id] = record
        return record

    def get_artifact(self, artifact_id: str, owner_id: str | None = None) -> ArtifactRecord | None:
        artifact = self.artifacts.get(artifact_id)
        if artifact and owner_id is not None and artifact.owner_id != owner_id:
            return None
        return artifact

    def create_version(self, owner_id: str, project_id: str, artifact_id: str, prompt: str, parent_version_id: str | None = None) -> VersionRecord:
        record = VersionRecord(str(uuid4()), owner_id, project_id, artifact_id, prompt, parent_version_id, utcnow())
        with self._lock:
            self.versions[record.id] = record
        return record

    def get_version(self, version_id: str, owner_id: str | None = None) -> VersionRecord | None:
        version = self.versions.get(version_id)
        if version and owner_id is not None and version.owner_id != owner_id:
            return None
        return version

    def list_versions(self, project_id: str, owner_id: str) -> list[VersionRecord]:
        return sorted((v for v in self.versions.values() if v.project_id == project_id and v.owner_id == owner_id), key=lambda v: v.created_at)
