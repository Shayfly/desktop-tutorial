> **היסטורי — לא המצב הנוכחי.** הוחלף על ידי `CURRENT_TRUTH_V27_HE.md`, `CURRENT_TRUTH_V28_HE.md`, ולאחר מכן `STATUS.md`. ראו `GOVERNANCE.md`.

# מצב אמת — V26

## מוכח בסביבה הזו
- 194 tests PASS; 9 integration/live tests SKIPPED במכוון.
- Production HTTP acceptance: creator signup, private project, build, cross-user denial=403, history, ZIP export, deploy, generated-app unauth=401, first generated-app user=admin, authenticated CRUD.
- V10 behavior parity tests נשמרים ועוברים בתוך הסוויטה המצטברת.
- חשבונות יוצר עם PBKDF2, signed tokens ובעלות פרויקט.
- בידוד פרויקטים באמצעות owner-scoped internal keys.
- Build, patch, restore, history, export, promote.
- Workspace commits thread-safe.
- Creative Director מתכנן image/icon/audio/music/voice/video/model3d/texture עם rights/accessibility gate.
- Media Gateway self-hosted HTTP contract נבדק מול שרת מקומי מזויף ומחזיר bytes אמיתיים; ספק GPU אמיתי לא הורץ כאן.
- V26 live autonomous route מחייב explicit enable + model + sandbox ונכשל סגור אחרת.
- Secret scan: 0 findings.

## עדיין לא מוכח/לא מחובר פיזית כאן
- Qwen/Open-Weight GPU אמיתי.
- ספקי image/audio/video/3D אמיתיים על GPU.
- Docker hostile runtime live.
- PostgreSQL/Redis/S3 live integration.
- persistence של Creator Accounts/Unified Workspace ב-PostgreSQL: V26 reviewer runtime עדיין משתמש ב-memory implementation; יש להחליף באדפטר production לפני public launch.
- signed Android AAB / signed iOS IPA / App Store & Play Store delivery.
- live payment checkout/webhooks.
- public domain, TLS, CDN/WAF, email verification/password recovery.
- translations מלאות של ממשק Omni לכל 12 locales; כרגע Control Center הוא EN/HE והארכיטקטורה תומכת locale contracts נוספים.

לכן: REVIEWER/ENGINEERING RELEASE — כן. Public worldwide launch — עדיין לא.
