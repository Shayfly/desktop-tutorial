# שער פריסה, חזרה לקוד קודם, חזרה מכשל ובידוד סביבות (2026-10-11)

מסמך תפעולי. כל הפעולות שמצוינות כ„דורש אישור" **לא בוצעו**; מה שנבדק נבדק מקומית (ראו „מה הוכח”).

## 1. שער הפריסה (`python -m omni_prod.active_jobs`) — נכשל סגור
| קוד יציאה | משמעות |
|---|---|
| 0 | אומת שקט: אף צרכן לא מריץ דבר. מותר לנקז |
| 3 | יש עבודה רצה (אחרי ההמתנה אם ביקשו) |
| 2 | **אי אפשר לאמת**: אין/נכשל חיבור ל-DB או ל-Redis, חסר `OMNI_REDIS_URL`, טבלה או שאילתה נכשלו, ארגומנטים שגויים |

חוסם: `build_jobs.status='running'` **בלי קשר ל-heartbeat** (heartbeat ישן אינו הוכחה שהעבודה הסתיימה; רק מפעיל שבדק job מסוים משחרר אותו ידנית עם
`--acknowledge-stale <id מדויק>` והוורקפלו אף פעם לא מעביר את הדגל), `modification_requests RUNNING`, `intake_reservations CLAIMED/EXECUTING` (גם עם lease שפג),
`project_previews STARTING`, כל job ב-`StartedJobRegistry` של **כל** תור RQ (כולל `omni-intake` ותורי `omni-preview-host-*` שאינם רשומים עדיין), וכל worker של RQ במצב `busy`.
עבודה בתור (queued) מדווחת ואינה חוסמת — הצרכן החדש ייקח אותה.

**המרוץ בין השער לניקוז:** `drain.sh` מריץ את השער שוב *מיד לפני* `docker compose stop` (עבודה שהתחילה בינתיים → סירוב, שום דבר לא נעצר, `recover.sh` לא נוגע בכלום
בזכות הסמן `not-stopped`), ושוב *אחרי* העצירה. אחרי שכל הצרכנים נעצרו שום עבודה חדשה לא יכולה להתחיל; מה שהשער עדיין רואה רץ/לא ניתן לאימות נקטע או ננטש →
הפריסה נכשלת וההתאוששות מחזירה את ה-workers הקודמים. עבודה שהתחילה אחרי הבדיקה האחרונה ולפני SIGTERM מסיימת בשלום (warm shutdown) בתוך ה-deadline; אם לא — 137 → נכשל.
**נשאר סיכון שלא ניתן לסגור בלי עצירת קבלת עבודה בצד ה-API:** job שהתחיל בשבריר שבין הבדיקה ל-SIGTERM ורץ מעבר ל-deadline (25 דק') ייקטע ויידווח, לא יוסתר.

## 2. חזרה לקוד קודם אחרי מיגרציה 038 — בלי DROP, בלי מחיקת קבצים מצורפים, בלי הסתרת גרסת ה-DB
- **שחזור קונטיינרים (`recover.sh`)** — לא מריץ מיגרציות ולא נוגע ב-DB; ה-worker הישן (2a2bba6) **הורץ מקומית** מול DB בגרסה 38 ו-Redis: עולה ומאזין (`Listening on omni-builds`).
- **פריסה חוזרת של קוד ישן דרך ה-workflow** נשברת בצעד `migrate` של הקוד הישן (`applied migration missing from package: 38`) — נבדק מקומית עם הקוד הישן. הקוד הישן לא ניתן לשינוי.
  לכן בענף הזה: `python -m omni_prod.migrate --accept-newer 38` (או קלט `accept_newer_migrations` ב-`deploy-worker.yml` ב-dispatch). החריג צר: גרסאות **במפורש**, רק אם הן **חדשות מכל מיגרציה בחבילה**;
  גרסה לא ברשימה, חור בהיסטוריה ו-checksum drift עדיין נעצרים; שום דבר לא נכתב; ה-DB ממשיך לדווח את גרסתו האמיתית (אזהרה מודפסת). מכסה רק קוד שנבנה מענף זה ואילך.
- **אין מסלול חזרה לקוד שלפני הענף הזה דרך ה-workflow** — רק דרך תמונות ההחזרה (`recover.sh`) ובלי מיגרציה. זה הפער שנשאר.
- ה-DROP TABLE שבהערת 038 **לא** משמש: טבלת `conversation_attachments` וה-objects נשארים.

## 3. בדיקת Docker אמיתי (`tests/test_real_docker_drain_recovery.py`)
מריצה את `drain.sh` ו-`recover.sh` **כמות שהם** מול Docker/`docker compose` אמיתיים, ארבעה צרכנים תחליפיים, מסד PostgreSQL מבודד וחד-פעמי ו-Redis אמיתי.
8 תרחישים: פריסה נקייה; job פעיל; כשל Redis/DB/חסר URL; כשל שמירת תמונת שחזור (הזרקת תקלה סביב docker אמיתי — מסומן); timeout→137; OOM אמיתי (דגל OOMKilled של המנוע);
כשל מיגרציה (checksum drift אמיתי); כשל עלייה של הגרסה החדשה. בכל תרחיש נבדק שכל ארבעת השירותים רצים שוב ושהתמונה היא של הגרסה הקודמת.
**מה זה לא מוכיח:** את מארח Oracle, התמונות והקובץ `docker-compose.yml` האמיתיים, ה-`.env`, הרשאות ה-runner. זה דורש חזרה מבוקרת על המארח (דורשת אישור; אין להריץ בזמן בנייה פעילה).
הרצה: `OMNI_TEST_REDIS_URL=redis://… M4D2_DATABASE_URL=postgresql://…/<db> python -m pytest tests/test_real_docker_drain_recovery.py` (ללא daemon → SKIP עם הסיבה BLOCKED).

## 4. ייצוא ראיות „חגית" (חד-פעמי, קריאה בלבד) — מה חסר
לא הורץ. נדרש: **(א) מזהה הבנייה `bld_<hex>`** של „חגית"; **(ב) מישהו עם גישה למארח ה-worker** (או למשתמש DB לקריאה בלבד ול-`OMNI_S3_*` של Production) שיריץ:
```
cd infra/worker-host && docker compose run --rm --no-deps -T worker python - bld_<hex> --files-dir /tmp/hagit-files < /path/to/omni_prod/evidence_export.py > evidence.json
```
(`--files-dir` מחלץ את הקבצים שנוצרו, **לא מצונזרים**, לשחזור לא מקוון — לשמור את התיקייה פרטית.) הפלט כולל: הבריף והחוזה המאושרים (רק אישור עם `used_by_build_id` = הבנייה המדויקת, אחרת `MISSING`/`AMBIGUOUS`),
קריטריוני ה-ProductSpec (A1…), הצעדים שנכשלו בכל סבב עם הראיות (HTTP וכו') והקריטריונים שהם מכסים, היסטוריית התיקונים, עלות ושריון קרדיט, `.omni/project.json`, רשימת הקבצים עם sha256 וטקסט מצונזר.
אם אין `artifact_key` או אין `OMNI_S3_*` — הדוח אומר זאת במפורש (`MISSING: …`).
**ניתוח (ללא מודל, ללא רשת, ללא עלות):** `python -m omni_prod.failure_replay evidence.json --files-dir /tmp/hagit-files` — מפריד **דרישת CRUD שגויה** / **כיסוי קריטריון חסר** / **פגם responsive אמיתי** (אותות סטטיים הם חיזוק בלבד).
הוא מסווג ארטיפקטים שמורים; הוא לא מריץ מחדש את האפליקציה ולא מצהיר „תוקן".

## 5. בידוד סביבות (`python -m omni_prod.isolation_check`)
קורא קובצי env מקומיים שהמפעיל הפיק, בלי להתחבר לשירותים ובלי לבצע כתיבה. הפלט כולל רק host/port ושמות DB, מספר Redis, bucket ופסק ISOLATED / SHARED / UNKNOWN; סיסמאות וטוקנים אינם מודפסים. אותה PostgreSQL instance נחשבת SHARED גם אם שם ה-DB שונה; אותה Redis instance נחשבת SHARED גם אם מספר ה-DB שונה, כי תורים ואחריות לזיכרון/זמינות עדיין משותפים.

כדי לבדוק את היעד החדש מול שתי הסביבות הקיימות:
```
python -m omni_prod.isolation_check --env-file staging.env --label staging --env-file production.env --label production --env-file preview.env --label preview
```
הקובץ הראשון חייב לכלול `OMNI_ENV=staging`; כל שלושת הקבצים חייבים להישמר מקומית ולא להיכנס ל-Git. הפקודה חייבת להחזיר `all_isolated=true` ויציאה 0. היא בודקת הבדלי endpoints, אך DNS aliases עלולים להסתיר משאב מנוהל משותף: לפני כל פעולה יש לאמת בנפרד בקונסולת הספק שמזהי ה-PostgreSQL וה-Redis Staging הם משאבים/פרויקטים ייעודיים, שונים מ-Production ומ-Preview. `UNKNOWN`, ערכים חסרים/סותרים או endpoint משותף הם NO-GO. גם אחרי PASS אין לבצע כתיבה, restore, migration או קריאה בתשלום לפני אישור מפורש ליעד ולפעולה.

**הראיה הקיימת עדיין מזהה את Production ואת Preview כמשתפים את רשומות `OMNI_DATABASE_URL`, `OMNI_REDIS_URL` ו-`OMNI_SECRET_KEY`.** בדיקת Staging החדשה טרם רצה: אין כאן קובצי env חדשים או משאבי Staging. אין להעתיק ערכי Preview/Production ל-Staging.

## 6. ביקורת מיגרציות 001–038 — סקירה סטטית בלבד
ב-34 קובצי SQL (גרסאות 001–021 ו-026–038) לא נמצאו statements פעילים של `DROP TABLE`, `DROP COLUMN`, `DELETE FROM` או `TRUNCATE`. נמצאו החלפה של constraints (015, 033), יצירת טבלאות/אינדקסים/עמודות, וב-037 הסרת `NOT NULL` מ-`intake_messages.cost_usd`; 038 מוסיפה טבלת attachments ואינדקס. זו אינה הוכחת תאימות ל-DB חי: מצב היעד, הנתונים וגודל הטבלאות אינם ידועים, ומסלול CI של DB ריק אינו תחליף ל-rehearsal על שחזור מדויק של היעד.

אין להריץ מיגרציה עד שמשאב Staging עצמאי אומת מול שתי הסביבות הקיימות, גיבוי של אותו יעד שוחזר בהצלחה לסביבה חד-פעמית, והוכח שאין פעולת נתונים/DDL הרסנית לא מאושרת. מיגרציה 038 לבדה additive, אך אין להסיק מכך שכל השרשרת תואמת למצב הקיים.

## 7. גיבוי ושחזור ל-Staging המבודד — לא הוכן/לא הורץ
`backup-restore.yml` הקיים רץ על runner ה-worker הקיים, קורא את `infra/worker-host/.env`, מעלה עותקים ל-object storage ומוחק גיבויים מעבר למדיניות retention. הוא מכוון לתשתית הקיימת, ולכן **אין להפעיל אותו עבור בדיקת Staging החדשה**. גיבוי/שחזור מאומת אחרון שנמצא הוא run [38139880170](https://github.com/Shayfly/desktop-tutorial/actions/runs/38139880170), מ-11 באוקטובר 2026, ברמת migration 37; הוא אינו גיבוי של יעד Staging חדש ואינו מכסה migration 38. נדרש runner/worker מבודד ושער גיבוי-שחזור שמכוון במפורש ל-DSN של Staging בלבד, שומר ומאמת את ה-stamp, ומחזיר את המשאב הזמני למצב נקי. עד להקמתם ואימותם לא מריצים migration או E2E שכותב ל-DB. יש להעדיף שירותים חינמיים שכבר זמינים בחשבונות המייסד; לא נבחר ספק/תוכנית, לא נוצר משאב, ולא תופעל תוכנית בתשלום ללא אישור נוסף.
