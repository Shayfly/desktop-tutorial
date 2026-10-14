from __future__ import annotations
from dataclasses import dataclass
from .migrations import Migration, verify_applied

_LOCK_ID = 781234991

@dataclass(frozen=True)
class MigrationRun:
    applied_versions: tuple[int, ...]

# Same definition as infra/postgres/005_release_engineering.sql. Migrations
# 001-004 run before 005 creates it, so on an empty database the runner must
# create it first or the very first bookkeeping INSERT fails.
SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def _load_applied(cursor) -> dict[int, str]:
    cursor.execute("SELECT to_regclass('schema_migrations') IS NOT NULL")
    if not cursor.fetchone()[0]:
        return {}
    cursor.execute("SELECT version, sha256 FROM schema_migrations ORDER BY version")
    return {int(row[0]): str(row[1]) for row in cursor.fetchall()}

class MigrationFailed(RuntimeError):
    """A migration's SQL raised. Names the version, so the log is never silent
    about which file broke the run."""

    def __init__(self, version: int, name: str, cause: BaseException):
        super().__init__(f'migration {version:03d}_{name} failed: {cause}')
        self.version = version
        self.name = name
        self.cause = cause


def _detach_from_callers_transaction(conn) -> None:
    """The caller may already be inside an implicit transaction (migrate.py
    reads schema_migrations before calling us). psycopg would then implement
    our block as a SAVEPOINT, and a migration file carrying its own
    BEGIN/COMMIT destroys that savepoint -- failing on RELEASE with
    InvalidSavepointSpecification and masking whatever really happened.
    Commit first, so this block is a real transaction with no savepoint."""
    info = getattr(conn, 'info', None)
    status = getattr(info, 'transaction_status', None)
    if status is not None and int(status) != 0:      # pq.TransactionStatus.IDLE == 0
        conn.commit()


def apply_migrations(conn, migrations: list[Migration], accept_newer: frozenset[int] = frozenset()) -> MigrationRun:
    _detach_from_callers_transaction(conn)
    applied_now: list[int] = []
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_ID,))
            cur.execute(SCHEMA_MIGRATIONS_DDL)
            applied = _load_applied(cur)
            verify_applied(migrations, applied, accept_newer)
            for migration in migrations:
                if migration.version in applied:
                    continue
                try:
                    cur.execute(migration.sql)
                    cur.execute(
                        """
                        INSERT INTO schema_migrations(version, name, sha256)
                        VALUES (%s, %s, %s)
                        """,
                        (migration.version, migration.name, migration.sha256),
                    )
                except Exception as exc:
                    raise MigrationFailed(migration.version, migration.name, exc) from exc
                applied_now.append(migration.version)
    return MigrationRun(tuple(applied_now))
