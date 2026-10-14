# Omni Creator V15 — Acceptance Harness

V15 מוסיפה בדיקת אינטגרציה deterministic של חוזי ה-production בלי לטעון שחיבורי ענן חיצוניים נבדקו.

ה-harness מריץ מסלול:
Build created → RUNNING → transient retry / code repair → immutable artifact → READY → version-pinned promotion.

בנוסף:
- artifact keys מוגנים מ-path traversal.
- logs עוברים redaction בסיסי ל-secrets.
- canary policy נבדקת ל-advance/rollback.

זו שכבת בדיקה. היא אינה תחליף לבדיקת PostgreSQL/Redis/S3/Docker אמיתית בסביבת staging.
