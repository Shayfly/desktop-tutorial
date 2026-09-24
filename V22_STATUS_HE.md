# Omni Creator V22 — Autonomous Core

V22 מחזירה את מרכז הכובד לליבת המוצר.

## נוסף בפועל
- OpenAI-compatible Model Gateway שאינו תלוי בספק אחד.
- Self-hosted/local model הוא ברירת המחדל.
- Zero-Cost Mode חוסם external model calls כברירת מחדל.
- External fallback אפשרי רק עם opt-in, מספר קריאות מקסימלי ותקציב דולר קשיח.
- Product Spec קשיח עם Requirements + Acceptance Criteria.
- כל requirement חובה חייב להיות מכוסה ב-Acceptance Criterion.
- Repository patch parser עם path-traversal protection ומגבלות גודל.
- Autonomous loop: Architect -> Generate -> Execute -> Repair -> Execute -> PASS/FAIL.
- Change policy: Bug/Missing Requirement של Omni = לא billable; Feature חדש של משתמש = billable.
- תיקון חינם חייב להצביע על acceptance criteria קיימים, כדי למנוע abuse.
- HTTP integration test מול OpenAI-compatible local endpoint אמיתי.
- Generated repository חייב לכלול `.omni/project.json` עם build/verification argv.
- SandboxRepositoryExecutor מחבר repository ל-Sandbox contract וממפה test failure ל-Acceptance ID.

## מה עדיין לא נטען
- לא הורדנו/הרצנו Qwen או מודל Open-Weight אמיתי בסביבה הזו.
- ה-Executor של ה-Autonomous Core עדיין צריך להתחבר פיזית למנוע V10 / Docker sandbox.
- V10 raw source עדיין לא מוזג לתוך V22.
- External GPT/Gemini API אינו מופעל ב-Zero-Cost Mode.

## היעד הבא
לחבר AutonomousProductEngine.executor אל build/sandbox של המנוע הראשי ולהריץ benchmark של prompts אמיתיים מקצה לקצה.
