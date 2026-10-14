"""Database schema version this code requires (Continuous Verification P0.4).

A Python constant, not a directory scan: serverless bundles (Vercel) trace
Python imports and do not necessarily ship infra/postgres/*.sql.
tests/test_deployment_verification.py fails if this drifts from the newest
migration file, so adding a migration forces updating it in the same change.
"""
REQUIRED_MIGRATION = 39
# Every migration version shipped in infra/postgres (022-025 were never used).
EXPECTED_VERSIONS = tuple(range(1, 22)) + tuple(range(26, 40))
REQUIRED_MIGRATION_NAME = '039_conversation_preferences'


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
