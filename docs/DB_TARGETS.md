# DB_TARGETS — מסדי נתונים, זהויות, ומי מריץ מיגרציות על מה

נבדק מול `main` @ `7afaa75`, 2026-10-19. המסמך מתעד מה נצפה ומה מוסק. שום דבר כאן לא אומת מול ה-DB עצמו בסשן הזה.

## Fingerprint: איך מחשבים

`omni_prod/schema_manifest.py:14`: `sha256(f"{host}|{dbname}")[:12]`. הוא נבנה מ-host ומשם ה-DB בלבד, בלי user ובלי סיסמה.

שלושה מקומות מדפיסים אותו:
- `GET /api/v28/deployment` → `schema.db_host` ו-`schema.db_fingerprint`.
- `python -m omni_prod.migrate` → `database: host=… fingerprint=…` (`migrate.py:59`).
- `tools/deployment_verify.py:273` מאמת את הפורמט בלבד, לא ערך צפוי.

**אין בריפו ערך fingerprint צפוי לאף סביבה.** אין שום מנגנון שנכשל אם Production מצביע על DB לא נכון.

## יעדים

| יעד | host | fingerprint | מקור הראיה | מצב |
|---|---|---|---|---|
| **Production** (Vercel `148aiv28`, `VERCEL_ENV=production`) | `ep-floral-bread-b1weu1th.c-5.eu-central-1.aws.neon.tech` | `5fabb3bf756d` | `smoke/last-run.md:5`: תשובת `/api/v28/deployment` ב-commit `f53b6dd`, `environment: production`, `applied_max: 41` | **נצפה** |
| **Preview** (Vercel `148aiv28`) | ככל הנראה זהה ל-Production | ככל הנראה `5fabb3bf756d` | `STATUS.md:153` ו-`STATUS.md:282` **מדווחים** ש-`OMNI_DATABASE_URL`, ‏`OMNI_REDIS_URL` ו-`OMNI_SECRET_KEY` הם רשומת env אחת ל-production+preview. **אין בריפו ראיה שמורה לכך** (לא תשובת API, לא פלט פקודה ולא קישור לריצה) | **מוסק, לא נצפה.** אין בריפו תשובת deployment של Preview עם `db_fingerprint`. |
| **Staging / worker** (Oracle, runner `omni-worker`) | לא ידוע | **לא נצפה** | `OMNI_DATABASE_URL` מגיע מה-secret `WORKER_ENV`, **אלא אם ה-secret `WORKER_ENV_OVERRIDES` מכיל אותו**. במקרה כזה `infra/worker-host/write-env.sh:15-29` מחליף את הערך, ושני workflows של ה-worker מעבירים את שני ה-secrets. היעד בפועל הוא מה שנכתב ל-`.env` שנוצר על ה-worker. הערך לא בריפו. (`write-env.sh:30` מדפיס בלוג רק את **שמות** המשתנים שהוחלפו.) `STATUS.md:471`: אחרי ש-deploy-worker הריץ מיגרציה 036, ‏Vercel **Preview** דיווח `applied_max=36`. | **טעון אימות.** הראיה מצביעה על כך שה-DB של ה-worker הוא ה-DB של Preview. אם Preview = Production, **אין staging נפרד: ה-worker מריץ מיגרציות על Production.** |
| **`TARGET_DATABASE_URL`** (secret ידני) | לא ידוע | לא נצפה | `migrate-target.yml`. הקובץ עצמו מזהיר שהיעד לא ידוע ויש לבדוק לפני apply. | לא ידוע |
| CI זמני | `127.0.0.1` / `postgres` (קונטיינר) | משתנה, לא רלוונטי | ‏`services: postgres:16` / compose | זמני, נמחק בסוף הריצה |

### איך לסגור את השורה "Staging" (בלי לשנות כלום)

הרצה של `migrate-target` עם `apply` **לא מסומן** מריצה `migrate --check`, שקורא בלבד ומדפיס `host=… fingerprint=…`. אבל היא רצה מול `TARGET_DATABASE_URL`, לא מול ה-DB של ה-worker. ל-DB של ה-worker:
- שורת `database: host=… fingerprint=…` מופיעה בלוג של כל ריצת `deploy-worker` (שלב "Apply database migrations").
- להשוות ל-`5fabb3bf756d`. התאמה פירושה שה-worker וה-Production חולקים DB.

הלוגים של Actions לא נגישים מהסשן הזה (blob storage חסום), ולכן לא בדקתי.

## מי מריץ מיגרציות על מה

| מי | טריגר | פקודה | יעד | משנה DB? |
|---|---|---|---|---|
| `deploy-worker.yml` | `push` ל-`milestone/pre-staging-2026-10-05`, `codex/148ai-verified-intake-2026-10-12` (נתיבי `omni_prod/**`, `infra/postgres/**` ועוד), או ידני | `python -m omni_prod.migrate` (שורות 104–114) | ה-DB של ה-worker (`WORKER_ENV`) | **כן, אוטומטית ב-push** |
| `internal-entitlement.yml` | ידני (grant/revoke/list), **וגם `push` ל-`milestone/pre-staging-2026-10-05`** כשהקובץ עצמו משתנה (אז `ACTION=list`) | `python -m omni_prod.migrate` (שורה 50) | ה-DB של ה-worker | **כן, גם אוטומטית ב-push.** שלב המיגרציה (שורה 50) רץ בלי תנאי, לפני ה-action. |
| `migrate-target.yml` | ידני | `--check` כברירת מחדל; `apply` מריץ apply | `TARGET_DATABASE_URL` | רק עם `apply`. **ברירת המחדל של `ref` מצביעה על ענף ישן** (`fix/financial-journal-recovery-20261014`). ההערה בקובץ אומרת להחליף ל-`main` אחרי המיזוג, וזה לא נעשה. |
| `intake-budget-pg.yml` | כל `push`/`pull_request` | `python -m omni_prod.migrate` (שורה 46) | קונטיינר `postgres:16` זמני | כן, זמני בלבד |
| `neon-bootstrap-ci.yml` | `push`/`pull_request` | `psql -f infra/staging/bootstrap_neon_empty.sql` | קונטיינר `postgres:16` זמני | כן, זמני בלבד |
| `v11-overlay-ci.yml` | `push`/`pull_request` | `docker compose … config` בלבד (שורה 37) | **אין** | **לא.** לא מרים שירותים ולא מתחבר ל-DB. (תוקן: קודם נכתב כאן שזה כותב ל-DB זמני.) |
| `financial-fault-experiment.yml` | `pull_request` | — | קונטיינר זמני | כן, זמני בלבד |
| `backup-restore.yml` | cron יומי `17 2 * * *` + ידני | `pg_dump` ואז שחזור לקונטיינר | **קורא** מה-DB של ה-worker, כותב לקונטיינר זמני | לא, ליעד האמיתי |
| `build-evidence.yml`, `t01-private-prototype-contract-audit.yml` | build-evidence: ידני **+ `push`** ל-`milestone/pre-staging-2026-10-05` (path-filtered). t01: **`push` בלבד** ל-`fix/148ai-t01-ci-recovery-2026-10-13`, בלי `workflow_dispatch` | `psycopg.connect` (t01 עם `default_transaction_read_only=on`) | ה-DB של ה-worker | build-evidence: קריאה בלבד לפי הקוד; t01: read-only מפורש |
| Vercel runtime (Production/Preview) | — | **לא מריץ מיגרציות.** אין קריאה ל-`apply_migrations` ב-`omni_prod` מחוץ ל-`migrate*.py`. | — | לא. רק מדווח תאימות ב-`/api/v28/deployment`. |

## ממצאים (לא מוכרעים כאן)

1. **ייתכן שאין הפרדה בין staging ל-Production.** לפי `STATUS.md:282`, ‏Preview ו-Production חולקים רשומת env. **זה דיווח בלי ראיה שמורה בריפו.** ה-worker כתב מיגרציה שנראתה ב-Preview (`STATUS.md:471`). יחד, `push` לענף pre-staging מריץ מיגרציות על ה-DB שמשרת Production. זה מוסק, לא נצפה. האימות הוא השוואת fingerprint כמתואר למעלה.
2. **אין fingerprint צפוי בקוד.** `deployment_verify` בודק פורמט, לא זהות. Production שמצביע בטעות על DB אחר **שהוא schema-compatible ותומך במסלול המאומת** יעבור את הבדיקות, כי הזהות לא מוצמדת. DB בלי המיגרציות ייכשל ב-`schema_compatible`.
3. **`internal-entitlement` מריץ מיגרציות** בכל הפעלה, כולל `list`, **וגם אוטומטית ב-push לענף pre-staging.**
4. **ברירת המחדל של `migrate-target` מיושנת.** מי שמריץ עם `apply` בלי לשנות `ref` מריץ מיגרציות מענף ישן.
5. `db_host` של Production חשוף ב-`/api/v28/deployment`. **הוכרע (CEO, 2026-10-19): host אינו סודי.** מקור: הנחיית המייסד בצ'אט עם Claude (2026-10-19, 00:52 Asia/Jerusalem). זו לא רשומה שניתן לאמת בריפו, ונדרש comment של `@Shayfly` על PR #49.

## ⚠ אזהרת הפרדת סביבות — ראיות CI מ־2026-10-19

`smoke/db-identity.md` (run `39208780505`; מ-2026-10-21 הקובץ נכתב לענף `bot-reports`, לא ל-`main`) מדווח ש־worker הרץ משתמש ב־host `ep-floral-bread-b1weu1th-pooler.c-5.eu-central-1.aws.neon.tech`, מסד `neondb`, endpoint `ep-floral-bread-b1weu1th`; Production מדווח host ישיר `ep-floral-bread-b1weu1th.c-5.eu-central-1.aws.neon.tech`, עם אותו endpoint. **אין בידוד Neon endpoint בין ה־worker לבין Production**. fingerprints טקסטואליים שונים (`d2eb0b8c775f` מול `5fabb3bf756d`) בגלל הסיומת `-pooler`, ולכן אין להשתמש בהשוואתם המילולית כהוכחת הפרדה. אימות DB מלא כולל שם מסד וענף Neon; עד לקבלת הוכחת בידוד יש להתייחס למיגרציות worker כעלולות לשנות את מסד Production. אין להריץ מיגרציות Staging בהנחה שהוא מבודד.
