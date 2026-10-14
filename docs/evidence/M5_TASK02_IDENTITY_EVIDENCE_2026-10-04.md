# M5 Task 2 — Durable Identity Lifecycle Evidence

Date: 2026-10-04
Implementation commit: `1483fb3f74d703a3f86adc763706a1df17a0b25e`

## Implemented

- Additive migration `018_identity_lifecycle.sql` adds durable creator sessions, hashed one-time identity tokens, consent records, privacy requests, account status and email verification state.
- `IdentityService` supports register/login/logout/revoke-session/list-sessions/email verification/password reset/consent/data-export/account-deletion flows.
- Session JWTs carry immutable session IDs; only SHA-256 token hashes are stored at rest.
- Email verification and password reset tokens are stored only as hashes and are one-time/expiring.
- Password reset revokes every existing durable session.
- Account deletion request moves the account to `DELETION_PENDING` and revokes sessions.
- `PostgresAccountService` delegates authentication to the durable identity lifecycle, so revoked sessions fail account/project access in the production Postgres path.
- V28 auth routes were added without changing existing register/login response shapes.
- Password-reset request API is enumeration-safe and never returns the raw reset token.

## Local verification

- Targeted identity/auth/V28 regression: 35 tests, 0 failures.
- Fresh whole-suite regression before commit: 683 tests, 0 failures, 0 errors, 50 skips.
- `python -m omni_prod.truth_lock --check`: PASS.
- `python -m omni_prod.requirement_ledger --check`: PASS before ledger promotion.

## External gate

`tests/integration/test_v28_creator_persistence.py::V28CreatorPersistenceLiveTests::test_session_revocation_survives_service_instance_change` requires migrated live PostgreSQL plus `OMNI_RUN_V28_CREATOR_POSTGRES=1`. It is kept gated instead of being represented as live production proof.

## Truth boundary

Task 2 is verified locally. Live PostgreSQL session-revocation proof and outbound delivery of email-verification/password-reset messages remain external/configuration gates; neither is inferred from local tests.
