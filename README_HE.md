# Omni Creator V11 — Production Infrastructure Overlay

מטרת החבילה: להעביר את Omni Creator משכבת Technical Beta מקומית לתשתית Production ניתנת לפריסה.

> חשוב: החבילה היא Overlay עצמאי שנבנה סביב הארכיטקטורה המאומתת של V10.
> היא **לא נטענת כאילו מוזגה ל-V10**, משום שקובץ המקור של V10 לא היה נגיש לבתי הקוד בסביבת העבודה הנוכחית.
> לאחר פתיחת מקור V10, ממזגים את המתאמים וההגדרות אל נקודות האינטגרציה בפועל.

## מה יש כאן

- PostgreSQL production configuration
- Redis/RQ worker abstraction
- S3-compatible object-storage abstraction
- Isolated Docker sandbox runner contract
- Resource limits + no-network sandbox profile
- Secret/session hardening configuration
- Health/readiness contracts
- Production Docker Compose
- GitHub CI validation workflow
- Merge checklist ל-V10
- Roadmap 51–100

## Target architecture

User Prompt
→ Architect
→ Repository Generator
→ Queue
→ Isolated Build Sandbox
→ Validation / Repair
→ Artifact Store
→ Preview / Deploy
→ Web / Android / iOS

Control plane:
FastAPI + PostgreSQL + Redis + Object Storage

Execution plane:
Ephemeral sandbox containers with CPU/RAM/PID/time limits and network disabled by default.

## Production rules

1. אין להריץ קוד AI לא מהימן בתהליך ה-FastAPI הראשי.
2. אין לשמור secrets בקוד או ב-DB plaintext.
3. SQLite נשאר רק למצב local/dev.
4. Workers חייבים להיות ניתנים להחלפה ולהרצה אופקית.
5. Artifacts צריכים object storage, לא local disk.
6. Sandbox חייב להיות ephemeral, read-only ככל האפשר, עם no-new-privileges.
7. כל build מקבל correlation/build id.
8. deploy חייב להיות version-pinned.
9. billing/usage נשמרים בנפרד מלוגי build.
10. signed mobile builds דורשים credentials חיצוניים ולא מזויפים.
