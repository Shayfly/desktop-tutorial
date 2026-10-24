# MAP — מפת תיקיות 148AI

**עדכון אחרון:** 2026-10-24 (Asia/Jerusalem). **בסיס נתונים:** GitHub `main` `9f9ccfbb58a2c3f4b77053fe5aebb31aa1f0d967`; מצב PR/runs נבדק ב-2026-10-24.

כל שורה מתארת תיקייה מוכרת לפי נתיבי הקוד שנבדקו; זו **מפת ניווט**, לא טענה לסריקה מלאה של כל תיקיות הריפו.

| תיקייה | תפקיד |
|---|---|
| `/` | קובצי תצורה, מטריצות אמת, רג׳יסטרים, הנחיות ותיעוד ראשי. |
| `.github/` | תצורת GitHub והגדרות האוטומציה. |
| `.github/workflows/` | CI, verification, פריסת Worker, דיאגנוסטיקה וראיות ריצה. |
| `omni_prod/` | שירותי הליבה, API, מתזמר הבנייה, מודלים, gates ותפעול. |
| `omni_prod/agent_os/` | הגדרות סוכנים/סקילים, audit, meta, סטטוסים ומטריצת אמת. |
| `omni_prod/intake/` | קליטת דרישות שיחה וניתוב משימות Intake. |
| `omni_prod/planning/` | ארכיטקטורה, תכנון וייצוג יכולות. |
| `omni_prod/intelligence/` | בריאות ספקים/יכולות intelligence. |
| `omni_prod/providers/` | מתאמי שירותים/ספקי מדיה ומודלים. |
| `omni_prod/assets/` | נכסי חזית סטטיים של המוצר. |
| `infra/` | הגדרות תשתית ותפעול מחוץ ללוגיקת המוצר. |
| `infra/worker-host/` | Docker Compose, Bootstrap, snapshot, rollback, recover וסודות סביבת Worker. |
| `infra/sandbox/` | ביצוע מבודד ותצורת sandbox. |
| `infra/sandbox-runner/` | שירות הרצת sandbox. |
| `infra/browser-sandbox/` | הרצות ובדיקות דפדפן מבודדות. |
| `infra/preview-worker/` | קונטיינר וניהול הרצת Preview. |
| `infra/postgres/` | מיגרציות סכמת PostgreSQL. |
| `infra/staging/` | Bootstrap והכנות סביבת staging. |
| `tests/` | בדיקות יחידה, אינטגרציה, חוזה, בקרה חיובית/שלילית ו־E2E. |
| `tests/customer_flow_browser.cjs` | קובץ בדיקות זרימת לקוח בתוך `tests` (לא תיקייה נפרדת). |
| `tools/` | כלים להפעלה, diagnostics, verification ופעולות מפתחים. |
| `tools/qa_postdeploy/` | כלי אימות לאחר פריסה. |
| `tools/ui_visual_edit/` | כלי בדיקה/עריכה של ממשק חזותי. |
| `docs/` | החלטות, תוכניות, דוחות ארכיטקטורה, הנדסה ואימות. |
| `docs/evidence/` | ראיות ותיעוד ניסויים וביקורות. |
| `smoke/` | סיכומי בדיקות smoke ודוחות ריצה שמורים. |

**חסר:** עבור רשימה מלאה של *כל* תיקיות הריפו יש לבצע `find . -type d` ב־checkout. המפה כוללת תיקיות שלהן נתיבים מזוהים ב־GitHub, ללא המצאה של תיקיות חדשות.
