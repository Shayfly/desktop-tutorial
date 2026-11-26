"""Database schema version this code requires (Continuous Verification P0.4).

A Python constant, not a directory scan: serverless bundles (Vercel) trace
Python imports and do not necessarily ship infra/postgres/*.sql.
tests/test_deployment_verification.py fails if this drifts from the newest
migration file, so adding a migration forces updating it in the same change.
"""
REQUIRED_MIGRATION = 48
# Every migration version shipped in infra/postgres (022-025 were never used; 046 and 047 are taken on other branches,
# social login and rate limits, and join this tuple when they merge).
EXPECTED_VERSIONS = tuple(range(1, 22)) + tuple(range(26, 46)) + (48,)
REQUIRED_MIGRATION_NAME = '048_unknown_cost_nullable'

# 047 (rate limits, 2026-11-26) is added on lines of its own, so it merges with 046 (social sign-in, another branch) in
# either order without touching the lines above: whichever of the two lands first, the values stay true.
EXPECTED_VERSIONS = tuple(sorted(EXPECTED_VERSIONS + (47,)))   # in file order, whichever of 046/047/048 merged first
# The newest migration is the one required: when 048 (unknown cost, 2026-11-26) merged first, 047 must not lower it.
if REQUIRED_MIGRATION < 47:
    REQUIRED_MIGRATION, REQUIRED_MIGRATION_NAME = 47, '047_rate_limits'


def db_fingerprint(host, dbname) -> str:
    """Comparable identity of a database without exposing a URL: host and
    database name only, never user or password."""
    import hashlib
    return hashlib.sha256(f'{host or ""}|{dbname or ""}'.encode('utf-8')).hexdigest()[:12]


def db_identity(conn) -> dict:
    """{'db_host', 'db_fingerprint'} for an open psycopg connection."""
    host = getattr(getattr(conn, 'info', None), 'host', None)
    dbname = conn.execute('SELECT current_database()').fetchone()[0]
    return {'db_host': host, 'db_fingerprint': db_fingerprint(host, dbname)}


def compatibility(applied) -> dict:
    """Required (code) vs applied (database) migration versions -- the single rule
    used by GET /api/v28/deployment (Vercel, no .sql files in the bundle) and by
    postdeploy_checks stage=free (worker host)."""
    applied = sorted({int(v) for v in applied})
    missing = [v for v in EXPECTED_VERSIONS if v not in set(applied)]
    unknown = [v for v in applied if v not in set(EXPECTED_VERSIONS)]     # DB ahead of this code
    return {'required': REQUIRED_MIGRATION, 'required_name': REQUIRED_MIGRATION_NAME,
            'applied_max': applied[-1] if applied else None, 'missing': missing, 'unknown_applied': unknown,
            'status': 'COMPATIBLE' if not missing else 'MIGRATIONS_PENDING', 'compatible': not missing}
