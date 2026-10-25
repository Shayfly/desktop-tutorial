"""Database schema version this code requires (Continuous Verification P0.4).

A Python constant, not a directory scan: serverless bundles (Vercel) trace
Python imports and do not necessarily ship infra/postgres/*.sql.
tests/test_deployment_verification.py fails if this drifts from the newest
migration file, so adding a migration forces updating it in the same change.
"""
REQUIRED_MIGRATION = 41
# Every migration version shipped in infra/postgres (022-025 were never used).
EXPECTED_VERSIONS = tuple(range(1, 22)) + tuple(range(26, 42))
REQUIRED_MIGRATION_NAME = '041_company_loss_ledger'


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


def database_failure(exc: BaseException) -> dict:
    """Public, secret-safe diagnosis; never return provider exception text/DSNs.

    PostgreSQL wire errors have no HTTP status. An explicit provider quota
    refusal is normalized to 402, with its basis recorded rather than pretending
    it came from an HTTP response. Generic pool/network failures remain unknown.
    """
    current, seen = exc, set()
    quota_markers = ('exceeded the quota', 'exceeded the compute time quota',
                     'compute time quota exceeded', 'data transfer quota exceeded')
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        response = getattr(current, 'response', None)
        status = (getattr(current, 'status_code', None) or getattr(current, 'status', None)
                  or getattr(response, 'status_code', None))
        basis = 'http_status' if status == 402 else (
            'provider_quota_message' if any(m in str(current).lower() for m in quota_markers) else None)
        if basis:
            return {'status': 'QUOTA_EXCEEDED', 'compatible': False, 'error': type(exc).__name__,
                    'error_code': 'DATABASE_QUOTA_EXCEEDED', 'provider_status': 402,
                    'provider_status_basis': basis}
        current = current.__cause__ or current.__context__
    return {'status': 'UNREACHABLE', 'compatible': False, 'error': type(exc).__name__,
            'error_code': 'DATABASE_UNREACHABLE'}
