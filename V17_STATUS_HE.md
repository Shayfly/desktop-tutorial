# Omni Creator V17 — Production Preflight

V17 מוסיפה שער Production שנכשל בצורה סגורה (fail-closed).

## נוסף
- בדיקת secrets, PostgreSQL URL, Redis URL, HTTPS origins ו-S3 credentials.
- בדיקת dependencies בפועל: psycopg, redis, RQ, boto3, Docker/Podman, Java, Node, Gradle.
- Migration runner עם PostgreSQL advisory transaction lock.
- Artifact checksum verification.
- FastAPI diagnostics app.
- Live HTTP acceptance.
- `/_omni/health/live` חייב לענות 200 כשה-process חי.
- `/_omni/health/ready` חייב לענות 503 כאשר PostgreSQL/Redis לא מחוברים.
- `/_omni/preflight` מציג את החסמים במקום להעמיד פנים שהמערכת מוכנה.

## לא מסומן PASS בלי הרצה אמיתית
- PostgreSQL
- Redis/RQ
- S3/MinIO
- Docker sandbox
- Android signing
- iOS signing
