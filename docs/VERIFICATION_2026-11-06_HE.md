# אימות ממצאים — 2026-11-06

**מי בדק:** Claude, לבקשת עובדיה. כל שורה כאן נבדקה מול GitHub API, יומני Actions, Vercel או Neon. לא נשענתי על דוחות קודמים.

## תיקונים לדוחות קודמים

| נאמר | בפועל | ראיה |
|---|---|---|
| ל-#246 יש 6 commits | **7 commits**, 6 קבצים | ה-GitHub API של PR #246 מחזיר `commits=7`. ה-commit האחרון הוא `0c9d643` ("align M5 settle mock with explicit contribution kwargs") |
| ה-workflow של הגיבוי (C17) מושבת | **פעיל** ורץ כל יום | ל-`backup-restore.yml` יש `state: active`. בריצה `42002340022` (5.11) רצו `pg_restore … (0 error lines)`, `verified: true` ו-`migrations_equal: true`, כלומר נעשתה עבודה אמיתית. הריצה האחרונה היא `42194235767` (6.11), והיא הצליחה |
| ה-worker נפרס בכל push | **לא.** ה-trigger של push כלל רק את `milestone/pre-staging-2026-10-05` ואת `codex/148ai-verified-intake-2026-10-12` | ב-`deploy-worker.yml` על `57ac533`. הפריסה האחרונה שהצליחה היא 148 (`41473898964`), שהורצה ידנית ב-2.11 על `ef9d156`. מאז זה, main התקדם 50 commits, וביניהם שינויים ב-`worker_tasks.py`, `subscription_store.py`, `schema_manifest.py` ו-`autonomous_core.py` |

## למה V11 אדום

`registry_lint: R3 C17: drill overdue since 2026-11-04 (weekly; last run 2026-10-28)`. הבדיקה קוראת את `CONTROLS.json`, ושם רשומה הרצה אחרונה של C17 בתאריך 28.10 (`40640783568`). הגיבוי עצמו רץ כל יום. מה שחסר הוא הרישום ב-`CONTROLS.json`, לא הגיבוי. העדכון של `CONTROLS.json` לא נכלל בתיקון הזה.

## למה db-identity נכשל שלוש פעמים

הריצות `40786272189` (28.10), `40831828711` (29.10) ו-`41235131447` (31.10) מדדו את המסד כמו שצריך. ב-29.10 וב-31.10 המדידה הראתה `ep-delicate-wind-b9cgx8fb`, עם טביעה `57afb09577d6`, כמו בפרודקשן. הכשל קרה בשלב שמנסה לכתוב את `smoke/db-identity.md` ל-main: `GH006: Protected branch update failed for refs/heads/main … 2 of 2 required status checks are expected`. ההגנה על main חוסמת push ישיר, כמו שהיא אמורה. **תוקן:** הדוח נכתב עכשיו ל-annotations ול-job summary בלבד, והריצה משווה את ה-endpoint לזה של הפרודקשן. אם ה-endpoint שונה, הריצה נכשלת.

## למה פריסה 149 נעצרה (6.11)

הריצה `42209069046` הייתה ידנית, על main ב-`57ac533`. היא נעצרה בשלב "Write environment file" עם השגיאה `OMNI_REDIS_URL is wrapped in quotes`. הערך מגיע מה-**secret הייעודי `OMNI_REDIS_URL`**, שמחליף את הערך מ-`WORKER_ENV`. הודעת השגיאה הפנתה ל-`WORKER_ENV`, וזו הפניה שגויה. **תוקן:** כל שורה בהודעה מציינת עכשיו את ה-secret שממנו הערך הגיע.

**ה-worker לא הושפע.** הריצה נעצרה לפני ה-drain ולפני הבנייה, כך שה-worker המשיך לרוץ על `ef9d156`.

## איך ה-worker הגיע ל-main (7.11)

| פריסה | Run ID | תוצאה | סיבה |
|---|---|---|---|
| 150–152 | `42214443331`, `42215277287`, `42216121365` | נעצרו ב-Write environment file | ה-secret `OMNI_REDIS_URL` עדיין עטוף במרכאות. העדכון לא נשמר |
| 153 | `42225161840` | נעצרה ב-Drain, בבטחה | `redis: AuthenticationError`. שער ה-drain סירב לעצור משהו, וה-rollback אישר שהצרכנים לא נגעו |
| **154** | **`42403347277`** | **הצליחה, כל השלבים** | הכתובת הועתקה מחדש מ-Upstash `148ai-redis` (`sharp-satyr-200692`), עם `rediss://` (TLS) |

ראיות מפריסה 154, על `ref=main sha=57ac5336d0dd7869bef761e31c142afc68ac2be5`:
- `verified quiet; draining is safe`. כל הצרכנים נעצרו אחרי 2 שניות. היו 4, והתמונות הקודמות נשמרו ל-rollback.
- שלב המיגרציות עבר, והמסד נשאר `COMPATIBLE 42/42`.
- `PASS` לבדיקות האלה: sandbox בלי רשת, browser sandbox, preview edge (`*.151-145-89-132.sslip.io`), שמירת נתוני preview אחרי restart ואחרי גרסה חדשה, ו-R2.
- `PASS job 2e19d60c-… enqueued on omni-builds was executed by worker … on this host`. ה-worker החדש צורך את תור הבנייות מאותו Redis שה-API משתמש בו.

**לקח:** בכתובת ש-Upstash מציג (`redis-cli --tls -u redis://…`), ההצפנה נקבעת על ידי הדגל `--tls`. כשמעבירים את הכתובת לבד, צריך לכתוב `rediss://`.

## חפיפה בין #244, #245 ו-#246

- הקוד ב-`omni_prod/` וב-`docs/` **זהה** בין הראש של #244 (`3031c9c`) לבין הראש של #246 (`0c9d643`). ההבדלים ביניהם הם רק ב-6 קבצי בדיקה.
- #244 ו-#245 יוצאים מאותו בסיס (`030e7be`), ונבדלים ב-2 commits של בדיקות בכל צד.
- ב-CI, בדיקות v24 ו-pg נכשלו גם על #244 וגם על #245. על #246 הן עברו: 2559 בדיקות ב-v24 ו-283 ב-pg.
- **המלצה (טרם בוצעה, ממתינה לאישור):** #246 נשאר, והבסיס שלו מוחלף ל-main. כך הוא יכיל את כל ה-commits של #245, ועוד 7 commits משלו. #244 ו-#245 נסגרים כ-superseded. אפשר יהיה לפתוח אותם מחדש.

## מצב אחרי האימות

| רכיב | מצב | ראיה |
|---|---|---|
| API | Vercel, `148aiv28`, פרודקשן על `57ac533` | `dpl_9kRr52sjPvcF35KHYRePnAyU6s5t`, `/api/v28/deployment` |
| מסד | Neon `ep-delicate-wind-b9cgx8fb`, `COMPATIBLE 42/42` | `/api/v28/deployment` |
| worker | Oracle `148ai-worker-01`, runner `self-hosted,omni-worker`, **על `57ac533` (main)** מ-7.11 | פריסה 154 (`42403347277`). לפני כן: `ef9d156` (פריסה 148) |
| מסד של ה-worker | אותו מסד כמו הפרודקשן (`57afb09577d6`) | פריסה 148 ו-db-identity |
| Redis | Upstash (אינטגרציה מותקנת ב-Vercel). הערך עצמו לא קריא | Vercel integrations |
| אחסון | Cloudflare R2, בצד ה-worker | `storage-probe … host_suffix=r2.cloudflarestorage.com` |
