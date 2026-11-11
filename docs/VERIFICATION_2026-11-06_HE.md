# אימות ממצאים — 2026-11-06

**מי בדק:** Claude, לבקשת עובדיה. כל שורה כאן נבדקה מול GitHub API, יומני Actions, Vercel או Neon. לא נשענתי על דוחות קודמים.

## תיקונים לדוחות קודמים

| נאמר | בפועל | ראיה |
|---|---|---|
| ל-#246 יש 6 commits | **7 commits**, 6 קבצים | ה-GitHub API של PR #246 מחזיר `commits=7`. ה-commit האחרון הוא `0c9d643` ("align M5 settle mock with explicit contribution kwargs") |
| ה-workflow של הגיבוי (C17) מושבת | **פעיל** ורץ כל יום | ל-`backup-restore.yml` יש `state: active`. בריצה `42002340022` (5.11) רצו `pg_restore … (0 error lines)`, `verified: true` ו-`migrations_equal: true`, כלומר נעשתה עבודה אמיתית. הריצה האחרונה היא `42194235767` (6.11), והיא הצליחה |
| ה-worker נפרס בכל push | **לא.** ה-trigger של push כלל רק את `milestone/pre-staging-2026-10-05` ואת `codex/148ai-verified-intake-2026-10-12` | ב-`deploy-worker.yml` על `57ac533`. הפריסה האחרונה שהצליחה היא 148 (`41473898964`), שהורצה ידנית ב-2.11 על `ef9d156`. מאז זה, main התקדם 50 commits, וביניהם שינויים ב-`worker_tasks.py`, `subscription_store.py`, `schema_manifest.py` ו-`autonomous_core.py` |

## למה V11 אדום

`registry_lint: R3 C17: drill overdue since 2026-11-04 (weekly; last run 2026-10-28)`. הבדיקה קוראת את `CONTROLS.json`, ושם רשומה הרצה אחרונה של C17 בתאריך 28.10 (`40640783568`). הגיבוי עצמו רץ כל יום. מה שחסר הוא הרישום ב-`CONTROLS.json`, לא הגיבוי.

**תוקן ב-7.11 (בהוראת עובדיה):** ל-`drills_run` נוספה רשומה של C17: `2026-11-06`, ‏`PASS`, ריצה `42194235767` (schedule על main `57ac533`). הראיות הועתקו מהיומן: `pg_restore … (0 error lines)`, ‏`migrations_equal: true`, ‏`verified: true`, ו-21 מתוך 21 קבצים שוחזרו. הבדיקה ב-`tests/test_registry_lint.py` הניחה שהרשומה האחרונה היא מ-28.10, ולכן היא מסננת עכשיו את הרשומות המאוחרות יותר. נוספה בדיקה שמוודאת שהרשומה החדשה מזיזה את המועד הבא ל-13.11.

**שימו לב:** הגיבוי רץ כל יום, אבל הרישום ידני. בלי רישום חדש עד 13.11, V11 יהיה שוב אדום ב-14.11.

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
| worker | Oracle `148ai-worker-01`, runner `self-hosted,omni-worker`, **על `cedcc43` (main)** מ-7.11 | פריסה 155 (`42405765412`, push). לפני כן: 154 על `57ac533`, ו-148 על `ef9d156` |
| מסד של ה-worker | אותו מסד כמו הפרודקשן (`57afb09577d6`) | פריסה 148 ו-db-identity |
| Redis | Upstash (אינטגרציה מותקנת ב-Vercel). הערך עצמו לא קריא | Vercel integrations |
| אחסון | Cloudflare R2, בצד ה-worker | `storage-probe … host_suffix=r2.cloudflarestorage.com` |

## אחרי המיזוג (7.11)

| שלב | תוצאה | ראיה |
|---|---|---|
| C17 ב-`CONTROLS.json` | נרשם: `2026-11-06`, `PASS`, `42194235767` | commit `9543021`; ‏`registry_lint: 31 controls … 0 violation(s)` |
| CI על #248 | הכל ירוק, כולל V11 (`validate`) | head `9543021` |
| כשל ביניים ב-pg | `test_5_an_oom_kill…` נכשל פעמיים ועבר בהרצה השלישית, בלי שינוי בקוד | ריצה `42404222487`. ה-OOM לא קרה, וה-job נהרג במועד של 60 שניות (`exit 137`). הבדיקה עברה על `4cd1b67` 8 דקות קודם. השינוי (CONTROLS.json, בדיקת lint, docs) לא נוגע ב-drain. **בדיקה לא יציבה, פתוח לטיפול** |
| מיזוג #248 | **`cedcc434b9bd242671509fd9d6caa80a79361d19`** | merge commit ב-main |
| פריסה אוטומטית מה-push | **155** (`42405765412`), ‏`event=push`, הצליחה | `ref=main sha=cedcc434…`. ה-drain אומת, כל ה-PASS עברו, וה-worker הריץ job מ-`omni-builds`. ה-trigger החדש עובד |
| #246 | הבסיס הוחלף ל-main (19 commits, 12 קבצים) | commits של #245 הם ancestors של `0c9d643`. ‏`omni_prod/` ו-`docs/` זהים ל-#244 |
| #244, #245 | נסגרו כ-superseded, עם הערה בכל אחד | אפשר לפתוח מחדש |

**הערה:** השלב "Verify maintenance services use 1800-second intervals" רץ רק ב-`workflow_dispatch`, ולכן ב-155 הוא דולג. זה לפי ההגדרה ב-workflow, לא כשל.

## הוראות עובדיה, 7.11 בערב

| שלב | מצב | ראיה |
|---|---|---|
| מיזוג #249 (docs) | **מוזג** | `309df93044115dd3f2a39abae181f963b8aaa3f7`. הוא לא הפעיל פריסת worker, כי השינוי הוא docs בלבד. ה-worker נשאר על `cedcc43` |
| CI ל-#246 מול main | **ירוק** | main מוזג לענף (`update-branch`), head `90890c8`. כל הבדיקות עברו, כולל V11, pg, v24 ו-deployment-verify (`42406715305`) |
| מיזוג #246 | **ממתין** | בלי מסלול קרדיטים (ראו בהמשך) |
| OOM (`test_5_an_oom_kill`) | **PR #250, ממתין למיזוג. שורש הבעיה לא אומת** | פירוט בהמשך |
| deployment-verify, `conversation_turn` | **PR #251, CI ירוק, ממתין למיזוג** | פירוט בהמשך |
| בדיקה מקצה לקצה דרך `/` | **לא בוצעה. חסומה מכאן** | פירוט בהמשך |

### מסלול הקרדיטים (נבדק בקוד של main `309df93`)

1. **הלקוח רואה את העלות לפני הבנייה: כן.** `POST /api/v28/projects/{id}/build-contracts` מחזיר `credits_required` ו-`allowance.credits_remaining`. בדף `/`, הקובץ `omni_prod/assets/app.js:705-707` מציג את שניהם לפני כפתור האישור. השלב הזה לא שומר קרדיטים.
2. **מסלול להוסיף קרדיט: אין.**
   - אין רכישה חד-פעמית של קרדיטים. `POST /api/v28/billing/checkout` יוצר רק **מנוי** (`mode: subscription`) לאחד המסלולים basic, pro או business.
   - **אין ב-Vercel אף משתנה `STRIPE_*`.** לכן ה-checkout מחזיר 503 (`STRIPE_SECRET_KEY is not configured`).
   - **ב-UI אין כפתור** שקורא ל-checkout.
   - כשנגמרים הקרדיטים, השרת מחזיר `402 build_allowance_exhausted` עם ההודעה "Add credits or build a smaller project", אבל אין לאן ללכת.
   - שמות המסלולים ב-Stripe (BASIC/PRO/BUSINESS) לא תואמים את החלטות 21 ו-22 (Free/Amateur/Pro/Studio).
3. **חסרים ארבעה דברים:**
   - חבילות קרדיט ומחירים. זו החלטת בעלים.
   - checkout חד-פעמי ב-Stripe (`mode: payment`), עם webhook שמזכה את ה-ledger בדיוק פעם אחת.
   - כפתור "הוסף קרדיטים" במקום שבו מוצגים העלות וההודעה על 402.
   - מפתחות Stripe ב-Vercel. זה עניין של הבעלים.

### OOM

- **ממצא:** ב-4 ריצות על #248 הבדיקה עברה 2 פעמים ונכשלה 2 פעמים, באותו קוד. בכל הכשלים מופיע `preview-worker exit=137 oom=false`, כלומר המנוע לא סימן OOM.
- **PR #250:** ב-`drain.sh`, כשיש exit 137 בלי הדגל, הסקריפט קורא שוב את `State.OOMKilled` במשך עד 3 שניות, ובודק אם יש `docker events --filter event=oom` לאותו container. כל אחד מהם מספיק כדי לסמן OOM. בנוסף, הריגה בגלל OOM כבר לא מדווחת גם כהריגה בגלל המגבלה.
- **תוצאות:** על `ba26bad` היו 3 הצלחות ו-1 כשל, ובכשל גם הבדיקה החוזרת לא מצאה סימן ל-OOM. על `e41c001` היו **6 הצלחות מתוך 6** (ריצה `42408564062`, ניסיונות 1 עד 6).
- **מה לא אומת:** שורש הבעיה. ההשערה הראשונה, מרוץ בין אירוע ה-OOM לאירוע היציאה, לא הסבירה את הכשל השלישי. לכן נוספו ל-`e41c001` נתוני אבחון לכל כשל עתידי: משך העצירה, `State` המלא, האירועים של ה-container, שורות OOM מה-kernel, וגרסאות המנוע וה-cgroup. הגדלת ההקצאה לא נעשתה: ה-allocator כבר מבקש 64MiB מתוך מגבלה של 48MiB בלי swap, ואין ראיה שההקצאה היא הבעיה.

### deployment-verify, `conversation_turn`

- **ממצא:** כשל אחד מתוך 60 הריצות האחרונות (`42099576142`, 5.11). באותה ריצה `conversation_persists` עבר מיד אחרי, כלומר השרת סיים את התור, אבל הלקוח כבר ויתר אחרי 15 שניות. בענף ה-preview ב-Neon (`br-shy-surf-b9il6jys`) אין reservation של intake, כך שהעיכוב לא נבע מהמתנה למודל.
- **מדידה:** אחרי התיקון, בריצה תקינה (`42407163938`), `conversation_turn` לקח **11,522ms**. שאר הבקשות לקחו בין 0.15 ל-4.6 שניות. כלומר, מגבלה של 15 שניות משאירה מרווח קטן מדי.
- **PR #251:**
  - ל-`conversation_turn` מוקצות 45 שניות. זה פחות מ-`maxDuration: 60`, כך ששרת תקוע עדיין יחזיר TIMEOUT.
  - שאר הבקשות נשארות על 15 שניות.
  - כל בדיקת HTTP רושמת `elapsed_ms`.

### בדיקה מקצה לקצה דרך `/`

לא בוצעה, משתי סיבות. אין לי מכאן גישה לרשת אל `148aiv28.vercel.app` (ה-proxy מחזיר 403), ואין דפדפן מחובר. אפשרויות:
- הבעלים מריץ את הבדיקה מהטלפון ב-`/`, ואני מאמת מהצד של השרת: Neon, תור ה-worker ו-artifacts.
- workflow שמריץ את הבדיקה מ-runner של GitHub עם חשבון בדיקה. זה דורש אישור, כי זו כתיבה לפרודקשן ויש לה עלות.

## מיזוגים באישור מפורש (עובדיה, 7.11, 22:51)

| PR | נושא | SHA של המיזוג | פריסת worker |
|---|---|---|---|
| #250 | drain: זיהוי OOM שמגיע באיחור, ונתוני אבחון | `cc4df55e467dace230861c6c82e680417b921c60` | 156 (`42413104173`), push. נבנתה על `2836b11` (main כבר כלל את #251), הצליחה. `drain: consumers stopped after 1s` |
| #251 | deployment-verify: מגבלה של 45 שניות ל-`conversation_turn`, ו-`elapsed_ms` | `2836b1123dd9dde0d62887d758fec9284118efe3` | נכלל ב-156 |
| #252 | docs: ביקורת מסלול הקרדיטים, OOM ו-verify | `c807fc43187f11b3bcbb5cbb7fc5ee5943e4a6f6` | docs בלבד |
| #246 | Hard Cap ב-LIGHT/STANDARD, ואישור חובה בבנייה async (מחליף את #244 ו-#245) | **`65488f693def35295f61ee3fc04f5cce658c04ec`** | **157** (`42413848957`), push, הצליחה |

- **CI של #246 לפני המיזוג:** הענף עודכן מ-main אחרי המיזוגים של #250 עד #252 (head `dc75072`), וכל הבדיקות היו ירוקות. אין חפיפה בקבצים בין #246 לבין #250 ו-#251.
- **ה-worker על הקוד הממוזג:** בפריסה 157 נרשם `ref=main sha=65488f6…`, ונרשמו ההודעות `verified quiet; draining is safe` ו-`all consumers stopped cleanly after 2s`. כל בדיקות ה-PASS עברו: sandbox, דפדפן, preview edge, שמירה אחרי restart, R2, ו-`PASS job … enqueued on omni-builds was executed by worker … on this host`.
- **ה-API:** `GET /api/v28/deployment` מחזיר `source_commit=65488f6…` ו-`schema COMPATIBLE 42/42`, על אותו מסד (`57afb09577d6`). ה-API וה-worker רצים על אותו commit.
- **החלטה #24** ב-`DECISIONS_LOG.md` היא עכשיו Hard Cap ב-LIGHT ($0.35) וב-STANDARD ($1.60), באישור הבעלים.
- **משימת הקרדיטים:** issue #253. היקף המשימה: checkout חד-פעמי, webhook שמזכה פעם אחת בדיוק, וכפתור "הוסף קרדיטים". המשימה ממתינה לשני דברים מהבעלים: חבילות ומחירים, ומפתחות Stripe ב-Vercel.
