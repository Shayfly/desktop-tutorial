from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from threading import RLock
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .store import (
    ArtifactRecord,
    BuildEventRecord,
    BuildRecord,
    ProjectRecord,
    SessionRecord,
    UserRecord,
    VersionRecord,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS live_users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    email_normalized TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    token_digest CHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL
);
CREATE TABLE IF NOT EXISTS live_projects (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    active_version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_artifacts (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    sha256 CHAR(64) NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_versions (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    artifact_id UUID NOT NULL REFERENCES live_artifacts(id) ON DELETE RESTRICT,
    prompt TEXT NOT NULL,
    parent_version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_builds (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES live_users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES live_projects(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT NULL,
    version_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS live_build_events (
    id UUID PRIMARY KEY,
    build_id UUID NOT NULL REFERENCES live_builds(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_live_projects_owner ON live_projects(owner_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_versions_project ON live_versions(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_live_versions_owner_project ON live_versions(owner_id, project_id);
CREATE INDEX IF NOT EXISTS idx_live_builds_owner_project ON live_builds(owner_id, project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_build_events_build ON live_build_events(build_id, created_at);
CREATE INDEX IF NOT EXISTS idx_live_artifacts_owner_project ON live_artifacts(owner_id, project_id);
"""


def _user(row) -> UserRecord | None:
    return None if not row else UserRecord(str(row["id"]), row["email"], row["password_hash"], row["created_at"])


def _session(row) -> SessionRecord | None:
    return None if not row else SessionRecord(str(row["id"]), str(row["user_id"]), row["token_digest"], row["created_at"], row["revoked_at"])


def _project(row) -> ProjectRecord | None:
    return None if not row else ProjectRecord(str(row["id"]), str(row["owner_id"]), row["title"], str(row["active_version_id"]) if row["active_version_id"] else None, row["created_at"], row["updated_at"])


def _artifact(row) -> ArtifactRecord | None:
    return None if not row else ArtifactRecord(str(row["id"]), str(row["owner_id"]), str(row["project_id"]), row["sha256"], row["size_bytes"], bytes(row["data"]), row["created_at"])


def _version(row) -> VersionRecord | None:
    return None if not row else VersionRecord(str(row["id"]), str(row["owner_id"]), str(row["project_id"]), str(row["artifact_id"]), row["prompt"], str(row["parent_version_id"]) if row["parent_version_id"] else None, row["created_at"])


def _build(row) -> BuildRecord | None:
    return None if not row else BuildRecord(str(row["id"]), str(row["owner_id"]), str(row["project_id"]), row["prompt"], row["stage"], row["status"], row["error"], str(row["version_id"]) if row["version_id"] else None, row["created_at"], row["updated_at"])


def _event(row) -> BuildEventRecord | None:
    return None if not row else BuildEventRecord(str(row["id"]), str(row["build_id"]), row["stage"], row["message"], row["created_at"])


class PostgresStore:
    """Durable shared state for production/serverless instances."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url
        self._schema_ready = False
        self._schema_lock = RLock()

    @contextmanager
    def _connection(self):
        with psycopg.connect(self.database_url, autocommit=True, row_factory=dict_row) as conn:
            self._ensure_schema(conn)
            yield conn

    def _ensure_schema(self, conn) -> None:
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            conn.execute(SCHEMA)
            self._schema_ready = True

    def create_user(self, email: str, password_hash: str) -> UserRecord:
        now = datetime.now().astimezone()
        uid = str(uuid4())
        normalized = email.strip().lower()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_users(id,email,email_normalized,password_hash,created_at) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                (uid, normalized, normalized, password_hash, now),
            ).fetchone()
        return _user(row)

    def get_user(self, user_id: str) -> UserRecord | None:
        with self._connection() as conn:
            return _user(conn.execute("SELECT * FROM live_users WHERE id=%s", (user_id,)).fetchone())

    def get_user_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with self._connection() as conn:
            return _user(conn.execute("SELECT * FROM live_users WHERE email_normalized=%s", (normalized,)).fetchone())

    def create_session(self, user_id: str, token_digest: str) -> SessionRecord:
        sid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_sessions(id,user_id,token_digest,created_at) VALUES (%s,%s,%s,%s) RETURNING *",
                (sid, user_id, token_digest, now),
            ).fetchone()
        return _session(row)

    def get_session_by_digest(self, token_digest: str) -> SessionRecord | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM live_sessions WHERE token_digest=%s AND revoked_at IS NULL",
                (token_digest,),
            ).fetchone()
        return _session(row)

    def revoke_session(self, token_digest: str) -> bool:
        now = datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "UPDATE live_sessions SET revoked_at=%s WHERE token_digest=%s AND revoked_at IS NULL RETURNING id",
                (now, token_digest),
            ).fetchone()
        return row is not None

    def create_project(self, owner_id: str, title: str) -> ProjectRecord:
        pid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_projects(id,owner_id,title,created_at,updated_at) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                (pid, owner_id, title, now, now),
            ).fetchone()
        return _project(row)

    def list_projects(self, owner_id: str) -> list[ProjectRecord]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM live_projects WHERE owner_id=%s ORDER BY updated_at DESC", (owner_id,)).fetchall()
        return [_project(row) for row in rows]

    def get_project(self, project_id: str, owner_id: str | None = None) -> ProjectRecord | None:
        with self._connection() as conn:
            if owner_id is None:
                row = conn.execute("SELECT * FROM live_projects WHERE id=%s", (project_id,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM live_projects WHERE id=%s AND owner_id=%s", (project_id, owner_id)).fetchone()
        return _project(row)

    def set_active_version(self, project_id: str, owner_id: str, version_id: str | None) -> ProjectRecord:
        now = datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "UPDATE live_projects SET active_version_id=%s,updated_at=%s WHERE id=%s AND owner_id=%s RETURNING *",
                (version_id, now, project_id, owner_id),
            ).fetchone()
        if not row:
            raise KeyError("project not found")
        return _project(row)

    def create_build(self, owner_id: str, project_id: str, prompt: str) -> BuildRecord:
        bid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_builds(id,owner_id,project_id,prompt,stage,status,created_at,updated_at) VALUES (%s,%s,%s,%s,'planning','running',%s,%s) RETURNING *",
                (bid, owner_id, project_id, prompt, now, now),
            ).fetchone()
        return _build(row)

    def get_build(self, build_id: str, owner_id: str | None = None) -> BuildRecord | None:
        with self._connection() as conn:
            if owner_id is None:
                row = conn.execute("SELECT * FROM live_builds WHERE id=%s", (build_id,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM live_builds WHERE id=%s AND owner_id=%s", (build_id, owner_id)).fetchone()
        return _build(row)

    def update_build(self, build_id: str, *, stage: str | None = None, status: str | None = None, error: str | None = None, version_id: str | None = None) -> BuildRecord:
        with self._connection() as conn:
            current = conn.execute("SELECT * FROM live_builds WHERE id=%s", (build_id,)).fetchone()
            if not current:
                raise KeyError("build not found")
            row = conn.execute(
                "UPDATE live_builds SET stage=%s,status=%s,error=%s,version_id=%s,updated_at=%s WHERE id=%s RETURNING *",
                (
                    stage if stage is not None else current["stage"],
                    status if status is not None else current["status"],
                    error,
                    version_id if version_id is not None else current["version_id"],
                    datetime.now().astimezone(),
                    build_id,
                ),
            ).fetchone()
        return _build(row)

    def append_build_event(self, build_id: str, stage: str, message: str = "") -> BuildEventRecord:
        eid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_build_events(id,build_id,stage,message,created_at) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                (eid, build_id, stage, message, now),
            ).fetchone()
        return _event(row)

    def get_build_events(self, build_id: str) -> list[str]:
        return [event.stage for event in self.get_build_event_records(build_id)]

    def get_build_event_records(self, build_id: str) -> list[BuildEventRecord]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM live_build_events WHERE build_id=%s ORDER BY created_at", (build_id,)).fetchall()
        return [_event(row) for row in rows]

    def create_artifact(self, owner_id: str, project_id: str, sha256: str, data: bytes) -> ArtifactRecord:
        aid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_artifacts(id,owner_id,project_id,sha256,size_bytes,data,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                (aid, owner_id, project_id, sha256, len(data), data, now),
            ).fetchone()
        return _artifact(row)

    def get_artifact(self, artifact_id: str, owner_id: str | None = None) -> ArtifactRecord | None:
        with self._connection() as conn:
            if owner_id is None:
                row = conn.execute("SELECT * FROM live_artifacts WHERE id=%s", (artifact_id,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM live_artifacts WHERE id=%s AND owner_id=%s", (artifact_id, owner_id)).fetchone()
        return _artifact(row)

    def create_version(self, owner_id: str, project_id: str, artifact_id: str, prompt: str, parent_version_id: str | None = None) -> VersionRecord:
        vid, now = str(uuid4()), datetime.now().astimezone()
        with self._connection() as conn:
            row = conn.execute(
                "INSERT INTO live_versions(id,owner_id,project_id,artifact_id,prompt,parent_version_id,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                (vid, owner_id, project_id, artifact_id, prompt, parent_version_id, now),
            ).fetchone()
        return _version(row)

    def get_version(self, version_id: str, owner_id: str | None = None) -> VersionRecord | None:
        with self._connection() as conn:
            if owner_id is None:
                row = conn.execute("SELECT * FROM live_versions WHERE id=%s", (version_id,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM live_versions WHERE id=%s AND owner_id=%s", (version_id, owner_id)).fetchone()
        return _version(row)

    def list_versions(self, project_id: str, owner_id: str) -> list[VersionRecord]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM live_versions WHERE project_id=%s AND owner_id=%s ORDER BY created_at",
                (project_id, owner_id),
            ).fetchall()
        return [_version(row) for row in rows]
