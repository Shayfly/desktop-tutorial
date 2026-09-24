# Omni Creator V21 — Gemini Audit Remediation

## תוקן בפועל
- PostgreSQL connection pool abstraction.
- pool sizing/timeouts via environment.
- no automatic retry of arbitrary DB transactions.
- hardened Redis connection settings.
- S3 adapter supports byte interface + checksum verification.
- Production adapter factory with fail-closed environment check.
- Memory adapter production guard.
- Distributed Redis circuit breaker.
- Stronger Docker sandbox command.
- Opt-in live integration suite for PostgreSQL / Redis / S3.
- External audit response with corrected factual record.

## חשוב
Memory adapters נשארו בכוונה ל-unit/acceptance harness.
הם לא נמחקו כי test doubles הם כלי נכון.
הבעיה שנפתרה היא מניעת שימוש בהם כ-production wiring.

## עדיין דורש תשתית חיצונית
- `OMNI_RUN_LIVE_INTEGRATION=1` מול services אמיתיים.
- Docker malicious-code isolation suite.
- load/concurrency tests.
- merge עם V10.
