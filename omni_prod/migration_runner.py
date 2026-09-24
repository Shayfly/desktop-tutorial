from __future__ import annotations
from dataclasses import dataclass
from .migrations import Migration, verify_applied

_LOCK_ID = 781234991

@dataclass(frozen=True)
class MigrationRun:
    applied_versions: tuple[int, ...]

def _load_applied(cursor) -> dict[int, str]:
    cursor.execute("SELECT version, sha256 FROM schema_migrations ORDER BY version")
    return {int(row[0]): str(row[1]) for row in cursor.fetchall()}

def apply_migrations(conn, migrations: list[Migration]) -> MigrationRun:
    applied_now: list[int] = []
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_ID,))
            applied = _load_applied(cur)
            verify_applied(migrations, applied)
            for migration in migrations:
                if migration.version in applied:
                    continue
                cur.execute(migration.sql)
                cur.execute(
                    """
                    INSERT INTO schema_migrations(version, name, sha256)
                    VALUES (%s, %s, %s)
                    """,
                    (migration.version, migration.name, migration.sha256),
                )
                applied_now.append(migration.version)
    return MigrationRun(tuple(applied_now))
