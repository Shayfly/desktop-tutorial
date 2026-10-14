# הכנת סביבת Staging מבודדת — עדיין לא פעילה

המסמך מכין הגדרות בלבד. אין לבצע בו פריסה, migration, כתיבה ל-DB, הפעלת Worker או קריאת ספק. שמות המשאבים שלהלן נמסרו על ידי המייסד; לא אומתו מול חשבונות Neon/Upstash משום שאין בסביבת העבודה token או CLI שלהם.

## המשאבים שנמסרו

- Neon: פרויקט `148ai-db`, ענף `preview-isolated-2026-10-12`, Frankfurt.
- Upstash: Redis `148ai-preview-isolated`, Frankfurt, Free.

**ענף Neon יכול להתחיל מצילום מצב של ענף אב.** כתיבות בענף מבודדות, אך הנתונים שהיו בענף האב בזמן יצירתו יכולים להיות נגישים בו. לפני שימוש, בדוק בקונסולת Neon את ה-parent של הענף ואת ה-point-in-time ממנו נוצר. אם הוא יורש נתוני Production, אין להשתמש בו לדרישה "ללא שיתוף נתוני Production" עד שמאשרים שמדובר בנתוני בדיקה/עותק שעבר sanitization; אל תאפס או תשנה את הענף הקיים כחלק מהבדיקה.

## מסכי ספקים — אימות ידני נדרש

1. [Neon Console — Projects](https://console.neon.tech/app/projects): פתח `148ai-db` → Branches → `preview-isolated-2026-10-12`. אשר את ה-parent, branch ID, endpoint/host ואת נקודת יצירת הנתונים. השווה את branch ID וה-host לענף Production מתוך חשבון Neon; אל תשלח connection string או צילום מסך שמציג סוד.
2. [Upstash Console — Redis](https://console.upstash.com/redis): פתח `148ai-preview-isolated`. אשר Region Frankfurt, תוכנית Free, Database ID ו-endpoint. השווה את Database ID וה-endpoint למסד שמשמש את Production; namespace או Redis DB number שונים באותו Upstash database אינם בידוד.
3. [GitHub Actions secrets](https://github.com/Shayfly/desktop-tutorial/settings/secrets/actions) ו-[Environments](https://github.com/Shayfly/desktop-tutorial/settings/environments): כרגע שמות ה-secrets שנראים ב-repository הם ספקי AI, `VERCEL_AUTOMATION_BYPASS_SECRET`, `WORKER_ENV`, ו-`WORKER_ENV_OVERRIDES`; לא נמצא secret/Environment ייעודי ל-Staging. `WORKER_ENV` הקיים משמש נתיב Worker משותף — אין לשנותו או להשתמש בו ל-Staging. יצירת Environment/Secrets חדשים תידחה עד שיוכח יעד Worker נפרד.
4. [Vercel Dashboard](https://vercel.com/dashboard): אין בסביבת העבודה Vercel CLI/token, ולכן הגדרות Vercel לא נקראו. יש לבדוק אם קיים פרויקט/יעד Staging נפרד. אל תוסיף משתני DB/Redis לסביבת Preview או Production של הפרויקט הקיים. אם אין פרויקט נפרד, נדרשת הקמה/הקצאה שלו במסך Vercel ואישור שהמסלול אינו משנה deployment של Production; אל תפעיל deploy.

## קובץ הגדרות מקומי

העתק `infra/staging/.env.example` אל `infra/staging/.env.local` ומלא בו מקומית בלבד:

- `OMNI_DATABASE_URL`: URL של branch Neon שאומת כ-Staging.
- `OMNI_REDIS_URL`: URL של Upstash database שאומת כ-Staging.
- `OMNI_SECRET_KEY` ו-`OMNI_SANDBOX_SHARED_SECRET`: ערכים חדשים, ייחודיים ל-Staging.
- `OMNI_S3_*`: יישארו ריקים עד שיאומת bucket/prefix נפרד. אל תכוון אל bucket Production.
- Provider keys נשארים ריקים; intake model/worker והתקציב מוגדרים כבויים/אפס.
- OpenRouter אינו מחובר לנתיב Vercel: שיחות AI מורשות רק דרך Worker מבודד עם reservation. המפתח שדווח ב-Vercel Preview אינו עובר ל-Worker. ב-Staging ייעודי בלבד יש להגדיר `OPENROUTER_API_KEY` ב-secret store של ה-Worker ואת `OMNI_MODEL_CATALOG_JSON` הזהה ב-API וב-Worker; `OMNI_OPENROUTER_ENABLED=0` נשאר כבוי עד אישור מפורש. אין להוסיף את המפתח ל-`WORKER_ENV` המשותף או להפעיל את workflow הקיים.

קובץ `.env.local` נכלל בכלל `.gitignore` של `.env.*`. אין לצרף, להדפיס, להעלות ל-GitHub או לשלוח אותו בצ'אט.

## סדר שערי בטיחות — אין לעקוף

1. בעל החשבון מאמת במסכי Neon/Upstash את resource IDs, parent lineage, endpoint ו-owner, ומשווה אותם ל-Production. Names שונים ב-DNS בלבד אינם ראיה מספקת.
2. שמור קובצי env רגישים מקומיים בלבד. לאחר ש-Vercel CLI הוגדר אצל מפעיל מורשה, אפשר למשוך את ערכי Preview/Production לקבצים מקומיים בלי להדפיס אותם. אחרי אימות ידני, השווה:
   ```
   python -m omni_prod.isolation_check --env-file infra/staging/.env.local --label staging --env-file infra/staging/production.env --label production --env-file infra/staging/preview.env --label preview --fingerprints
   ```
   הפלט מציג SHA-256 fingerprints בלבד במקום hosts ושמות DB. PASS דורש `all_isolated=true`; UNKNOWN/SHARED הוא NO-GO. כלי זה בודק endpoints ולא יכול להוכיח ש-DNS aliases אינם מפנים לאותו resource; הצלבה מול ה-resource IDs בקונסולות הספק נדרשת בנוסף.
3. אין כרגע backup workflow מבודד: `.github/workflows/backup-restore.yml` משתמש ב-worker וב-`.env` הקיימים ומבצע גם pruning. אסור להריץ אותו עבור היעד הזה. יש להשיג snapshot/export של ה-branch המאומת ולהחזירו ל-PostgreSQL חד-פעמי ומבודד, בלי לשנות את ה-branch המקורי. פלט backup ו-restore חייב להראות התאמת schema, migration history ושימור נתוני snapshot. אין לבצע migrations כחלק מהשלב הזה.
4. רק אחרי שהבידוד ושחזור הגיבוי הוכחו, יש לבקש אישור מפורש נפרד לפני migration 001–038. אין להפעיל Worker או deploy עד אישור נוסף והקמת מסלול Worker מבודד.

## ממצאי הסביבה הנוכחית

- GitHub repository Environments שנמצאו: `Preview`, `Preview – 148ai`, `Preview – 148aiv28`, `Production`, `Production – 148ai`, `Production – 148aiv28`; אין `Staging`.
- לא נמצאו Actions Variables; לא נראים secrets בשם Neon/Upstash/Staging. קיימים `WORKER_ENV` ו-`WORKER_ENV_OVERRIDES`, אך ערכיהם לא נקראו ואסור להסיק מהם או להדפיס אותם.
- לא מותקנים `neonctl`, `upstash`, `vercel`, `docker`, `psql` או `redis-cli`; אין API tokens/DSNs בסביבה המקומית.
- לכן לא נבדק בפועל שהמשאבים שמסר המייסד אינם משמשים את Production, לא הורץ checker מול חיבור אמיתי, ולא נעשו backup/restore, migrations, worker deploy או E2E.
