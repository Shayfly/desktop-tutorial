"""Apply pending SQL migrations from infra/postgres to OMNI_DATABASE_URL.

    python -m omni_prod.migrate            # apply pending, print versions
    python -m omni_prod.migrate --check    # list pending only, change nothing
    python -m omni_prod.migrate --accept-newer 38[,39]   # code rollback: this package is OLDER than the database

--accept-newer (or OMNI_ACCEPT_NEWER_MIGRATIONS) names the exact versions a NEWER release already applied. Only those
exact versions, only if newer than every migration in this package, are tolerated; nothing is dropped, nothing is
hidden (the database keeps reporting its real version) and every other check stays: an unnamed unknown version, a gap
and checksum drift still abort.

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
from .schema_manifest import db_identity

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'infra' / 'postgres'


def parse_accept_newer(argv: list[str], env=None) -> frozenset[int]:
    env = os.environ if env is None else env
    raw = argv[argv.index('--accept-newer') + 1] if '--accept-newer' in argv and argv.index('--accept-newer') + 1 < len(argv) \
        else ('' if '--accept-newer' not in argv else None)
    if raw is None:
        raise ValueError('--accept-newer needs exact versions, e.g. 38')
    raw = raw or env.get('OMNI_ACCEPT_NEWER_MIGRATIONS', '')
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    if not all(p.isdigit() for p in parts):
        raise ValueError(f'--accept-newer takes exact integer versions, got {raw!r}')
    return frozenset(int(p) for p in parts)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        accept = parse_accept_newer(argv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    url = os.getenv('OMNI_DATABASE_URL', '').strip()
    if not url:
        print('OMNI_DATABASE_URL is not set', file=sys.stderr)
        return 2
    import psycopg
    migrations = discover_migrations(MIGRATIONS_DIR)
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            applied = _load_applied(cur)
        ident = db_identity(conn)
        print(f"database: host={ident['db_host']} fingerprint={ident['db_fingerprint']}")
        pending = pending_migrations(migrations, applied, accept)
        ahead = sorted(v for v in applied if v not in {m.version for m in migrations})
        if ahead:
            print(f'::warning title=migrate::database is AHEAD of this code at versions {ahead} (accepted explicitly); nothing was changed or hidden')
        print('pending migrations:', [m.version for m in pending] or 'none')
        if '--check' in argv or not pending:
            return 0
        run = apply_migrations(conn, migrations, accept)
        print('applied migrations:', list(run.applied_versions))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
