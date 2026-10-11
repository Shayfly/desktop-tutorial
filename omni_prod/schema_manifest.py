"""Database schema version this code requires (Continuous Verification P0.4).

A Python constant, not a directory scan: serverless bundles (Vercel) trace
Python imports and do not necessarily ship infra/postgres/*.sql.
tests/test_deployment_verification.py fails if this drifts from the newest
migration file, so adding a migration forces updating it in the same change.
"""
REQUIRED_MIGRATION = 36
# Every migration version shipped in infra/postgres (022-025 were never used).
EXPECTED_VERSIONS = tuple(range(1, 22)) + tuple(range(26, 37))
REQUIRED_MIGRATION_NAME = '036_intelligence_plane'
