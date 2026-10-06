"""Apply pending SQL migrations from infra/postgres to OMNI_DATABASE_URL.

    python -m omni_prod.migrate            # apply pending, print versions
    python -m omni_prod.migrate --check    # list pending only, change nothing

Uses the existing checksum-verified runner: an applied migration whose file
changed aborts the run (checksum drift) instead of silently diverging.
Prints versions only; never prints the connection string.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .migrations import discover_migrations, pending_migrations
from .migration_runner import apply_migrations, _load_applied

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'infra' / 'postgres'


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    url = os.getenv('OMNI_DATABASE_URL', '').strip()
    if not url:
        print('OMNI_DATABASE_URL is not set', file=sys.stderr)
        return 2
    import psycopg
    migrations = discover_migrations(MIGRATIONS_DIR)
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            applied = _load_applied(cur)
        pending = pending_migrations(migrations, applied)
        print('pending migrations:', [m.version for m in pending] or 'none')
        if '--check' in argv or not pending:
            return 0
        run = apply_migrations(conn, migrations)
        print('applied migrations:', list(run.applied_versions))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
