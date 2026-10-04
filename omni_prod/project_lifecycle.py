from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
import secrets

from .account_tenant import ProjectRecord
from .db import DatabasePool


class ProjectLifecycleError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProjectState:
    id: str
    owner_id: str
    title: str
    created_at: str
    updated_at: str
    archived_at: str | None = None
    deleted_at: str | None = None
    retention_until: str | None = None
    tombstone_reason: str | None = None

    @property
    def state(self) -> str:
        if self.deleted_at:
            return "DELETED"
        if self.archived_at:
            return "ARCHIVED"
        return "ACTIVE"

    def as_project_record(self) -> ProjectRecord:
        return ProjectRecord(self.id, self.owner_id, self.title, self.created_at, self.updated_at)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state": self.state,
            "archived_at": self.archived_at,
            "deleted_at": self.deleted_at,
            "retention_until": self.retention_until,
            "tombstone_reason": self.tombstone_reason,
        }


class ProjectLifecycleRepository(Protocol):
    def create(self, project: ProjectRecord) -> None: ...
    def get(self, owner_id: str, project_id: str) -> ProjectState | None: ...
    def update_title(self, owner_id: str, project_id: str, title: str, updated_at: str) -> ProjectState | None: ...
    def set_archived(self, owner_id: str, project_id: str, archived_at: str | None, updated_at: str) -> ProjectState | None: ...
    def soft_delete(self, owner_id: str, project_id: str, deleted_at: str, retention_until: str, reason: str, updated_at: str) -> ProjectState | None: ...
    def list_for_owner(self, owner_id: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]: ...
    def search_for_owner(self, owner_id: str, query: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]: ...


class MemoryProjectLifecycleRepository:
    def __init__(self) -> None:
        self._rows: dict[str, ProjectState] = {}

    def create(self, project: ProjectRecord) -> None:
        if project.id in self._rows:
            raise ValueError("project id already exists")
        self._rows[project.id] = ProjectState(
            project.id, project.owner_id, project.title, project.created_at, project.updated_at
        )

    def raw(self, project_id: str) -> ProjectState | None:
        return self._rows.get(project_id)

    def get(self, owner_id: str, project_id: str) -> ProjectState | None:
        row = self._rows.get(project_id)
        return row if row and row.owner_id == owner_id else None

    def update_title(self, owner_id: str, project_id: str, title: str, updated_at: str) -> ProjectState | None:
        row = self.get(owner_id, project_id)
        if not row:
            return None
        row = replace(row, title=title, updated_at=updated_at)
        self._rows[project_id] = row
        return row

    def set_archived(self, owner_id: str, project_id: str, archived_at: str | None, updated_at: str) -> ProjectState | None:
        row = self.get(owner_id, project_id)
        if not row:
            return None
        row = replace(row, archived_at=archived_at, updated_at=updated_at)
        self._rows[project_id] = row
        return row

    def soft_delete(self, owner_id: str, project_id: str, deleted_at: str, retention_until: str, reason: str, updated_at: str) -> ProjectState | None:
        row = self.get(owner_id, project_id)
        if not row:
            return None
        if row.deleted_at:
            return row
        row = replace(
            row,
            archived_at=None,
            deleted_at=deleted_at,
            retention_until=retention_until,
            tombstone_reason=reason,
            updated_at=updated_at,
        )
        self._rows[project_id] = row
        return row

    def list_for_owner(self, owner_id: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]:
        rows = [r for r in self._rows.values() if r.owner_id == owner_id and not r.deleted_at]
        if not include_archived:
            rows = [r for r in rows if not r.archived_at]
        return tuple(sorted(rows, key=lambda r: r.updated_at, reverse=True))

    def search_for_owner(self, owner_id: str, query: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]:
        needle = query.strip().casefold()
        rows = self.list_for_owner(owner_id, include_archived=include_archived)
        if not needle:
            return rows
        return tuple(r for r in rows if needle in r.title.casefold())


class PostgresProjectLifecycleRepository:
    def __init__(self, pool: DatabasePool):
        self._pool = pool

    @staticmethod
    def _state(row) -> ProjectState | None:
        if not row:
            return None
        return ProjectState(
            id=str(row[0]), owner_id=str(row[1]), title=str(row[2]),
            created_at=_iso(row[3]), updated_at=_iso(row[4]),
            archived_at=_iso(row[5]) if row[5] else None,
            deleted_at=_iso(row[6]) if row[6] else None,
            retention_until=_iso(row[7]) if row[7] else None,
            tombstone_reason=str(row[8]) if row[8] is not None else None,
        )

    def create(self, project: ProjectRecord) -> None:
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO creator_projects(id,owner_id,title,created_at,updated_at) VALUES(%s,%s,%s,%s,%s)",
                            (project.id, project.owner_id, project.title, project.created_at, project.updated_at),
                        )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise ValueError("project id already exists") from exc
            raise

    def get(self, owner_id: str, project_id: str) -> ProjectState | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason FROM creator_projects WHERE id=%s AND owner_id=%s",
                    (project_id, owner_id),
                )
                return self._state(cur.fetchone())

    def _returning_update(self, sql: str, params: tuple) -> ProjectState | None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return self._state(cur.fetchone())

    def update_title(self, owner_id: str, project_id: str, title: str, updated_at: str) -> ProjectState | None:
        return self._returning_update(
            "UPDATE creator_projects SET title=%s,updated_at=%s WHERE id=%s AND owner_id=%s AND deleted_at IS NULL RETURNING id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason",
            (title, updated_at, project_id, owner_id),
        )

    def set_archived(self, owner_id: str, project_id: str, archived_at: str | None, updated_at: str) -> ProjectState | None:
        return self._returning_update(
            "UPDATE creator_projects SET archived_at=%s,updated_at=%s WHERE id=%s AND owner_id=%s AND deleted_at IS NULL RETURNING id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason",
            (archived_at, updated_at, project_id, owner_id),
        )

    def soft_delete(self, owner_id: str, project_id: str, deleted_at: str, retention_until: str, reason: str, updated_at: str) -> ProjectState | None:
        # COALESCE preserves the first tombstone timestamp/retention window so retry is idempotent.
        return self._returning_update(
            "UPDATE creator_projects SET archived_at=NULL,deleted_at=COALESCE(deleted_at,%s),retention_until=COALESCE(retention_until,%s),tombstone_reason=COALESCE(tombstone_reason,%s),updated_at=CASE WHEN deleted_at IS NULL THEN %s ELSE updated_at END WHERE id=%s AND owner_id=%s RETURNING id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason",
            (deleted_at, retention_until, reason, updated_at, project_id, owner_id),
        )

    def list_for_owner(self, owner_id: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]:
        predicate = "owner_id=%s AND deleted_at IS NULL"
        if not include_archived:
            predicate += " AND archived_at IS NULL"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason FROM creator_projects WHERE {predicate} ORDER BY updated_at DESC",
                    (owner_id,),
                )
                return tuple(self._state(row) for row in cur.fetchall())  # type: ignore[misc]

    def search_for_owner(self, owner_id: str, query: str, *, include_archived: bool = False) -> tuple[ProjectState, ...]:
        predicate = "owner_id=%s AND deleted_at IS NULL AND title ILIKE %s"
        if not include_archived:
            predicate += " AND archived_at IS NULL"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id,owner_id,title,created_at,updated_at,archived_at,deleted_at,retention_until,tombstone_reason FROM creator_projects WHERE {predicate} ORDER BY updated_at DESC",
                    (owner_id, f"%{query.strip()}%"),
                )
                return tuple(self._state(row) for row in cur.fetchall())  # type: ignore[misc]


class ProjectLifecycleService:
    RETENTION = timedelta(days=30)

    def __init__(self, repository: ProjectLifecycleRepository, *, now_fn: Callable[[], datetime] = _utc_now):
        self._repo = repository
        self._now_fn = now_fn

    def _now(self) -> datetime:
        value = self._now_fn()
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _title(title: str) -> str:
        normalized = " ".join(title.split()).strip()
        if not normalized:
            raise ValueError("title required")
        return normalized[:120]

    def create_project(self, *, owner_id: str, title: str) -> ProjectRecord:
        now = self._now().isoformat()
        record = ProjectRecord("prj_" + secrets.token_urlsafe(10), owner_id, self._title(title), now, now)
        self._repo.create(record)
        return record

    def project_state(self, *, owner_id: str, project_id: str) -> ProjectState:
        row = self._repo.get(owner_id, project_id)
        if not row:
            raise PermissionError("project not found or access denied")
        return row

    def require_project(self, *, owner_id: str, project_id: str) -> ProjectRecord:
        row = self.project_state(owner_id=owner_id, project_id=project_id)
        if row.deleted_at:
            raise ProjectLifecycleError("project deleted")
        if row.archived_at:
            raise ProjectLifecycleError("project archived")
        return row.as_project_record()

    def list_projects(self, *, owner_id: str, include_archived: bool = False) -> tuple[ProjectRecord, ...]:
        return tuple(r.as_project_record() for r in self._repo.list_for_owner(owner_id, include_archived=include_archived))

    def search_projects(self, *, owner_id: str, query: str, include_archived: bool = False) -> tuple[ProjectRecord, ...]:
        return tuple(r.as_project_record() for r in self._repo.search_for_owner(owner_id, query, include_archived=include_archived))

    def rename_project(self, *, owner_id: str, project_id: str, title: str) -> ProjectRecord:
        current = self.project_state(owner_id=owner_id, project_id=project_id)
        if current.deleted_at:
            raise ProjectLifecycleError("project deleted")
        row = self._repo.update_title(owner_id, project_id, self._title(title), self._now().isoformat())
        if not row:
            raise PermissionError("project not found or access denied")
        return row.as_project_record()

    def archive_project(self, *, owner_id: str, project_id: str) -> ProjectState:
        current = self.project_state(owner_id=owner_id, project_id=project_id)
        if current.deleted_at:
            raise ProjectLifecycleError("project deleted")
        if current.archived_at:
            return current
        now = self._now().isoformat()
        row = self._repo.set_archived(owner_id, project_id, now, now)
        if not row:
            raise PermissionError("project not found or access denied")
        return row

    def unarchive_project(self, *, owner_id: str, project_id: str) -> ProjectState:
        current = self.project_state(owner_id=owner_id, project_id=project_id)
        if current.deleted_at:
            raise ProjectLifecycleError("project deleted")
        if not current.archived_at:
            return current
        row = self._repo.set_archived(owner_id, project_id, None, self._now().isoformat())
        if not row:
            raise PermissionError("project not found or access denied")
        return row

    def delete_project(self, *, owner_id: str, project_id: str, reason: str = "user_request") -> ProjectState:
        current = self.project_state(owner_id=owner_id, project_id=project_id)
        if current.deleted_at:
            return current
        now = self._now()
        row = self._repo.soft_delete(
            owner_id,
            project_id,
            now.isoformat(),
            (now + self.RETENTION).isoformat(),
            (reason.strip() or "user_request")[:200],
            now.isoformat(),
        )
        if not row:
            raise PermissionError("project not found or access denied")
        return row
