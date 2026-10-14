# Omni Creator V16 — Release Safety Gate

## מה נוסף ב-V16

- Migration discovery עם versioning + SHA-256.
- חסימת checksum drift למיגרציה שכבר יושמה.
- Audit log עם hash-chain לזיהוי שינוי היסטוריה.
- Secret scanner ל-credentials בעלי entropy/מבנה אמיתי.
- Release manifest עם checksum לכל קובץ.
- אימות manifest וגילוי שינוי/חוסר/קובץ נוסף.
- Canary controller עם advance / hold / rollback / complete.
- Staging simulation:
  Build → transient retry → artifact → deployment → canary → complete.
- SQL schema ל-schema migrations, audit events ו-release records.
- Clean-extract validation.

## מה V16 עדיין לא טוענת

לא נבדק Live מול:
- PostgreSQL server אמיתי.
- Redis server אמיתי.
- S3/MinIO אמיתי.
- Docker daemon אמיתי.
- HTTPS/DNS ציבורי.
- Android private signing key.
- Apple signing/TestFlight.

אלה נשארים Production Live Gate ולא יסומנו PASS עד להרצה בפועל.
