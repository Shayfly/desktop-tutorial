# ייצוא ראיות מבנייה שנכשלה (קריאה בלבד)

**מצב:** לא הצלחתי לשחזר את הבנייה של „חגית” מכאן — אין לי גישה לרשומת ה-job, ל-DB או ללוגים של Actions.
לכן A2/A4/A5 ו-responsive **אינם מוצגים כפגמי מוצר או כפגמי בדיקה** — אין שחזור.

## מה מוכן
- `python -m omni_prod.evidence_export bld_<hex>` — טרנזקציית READ ONLY אחת, בלי כתיבה, בלי מודל, בלי עלות.
  מוציא JSON מצונזר: שורת הבנייה, סיבת עצירה, **פירוט כל סבב תיקון** (אילו צעדים נכשלו, אילו קריטריונים לא כוסו, אילו סוגים NOT_REQUIRED),
  שימוש במודלים והוצאה, הבריף המאושר (revision + fingerprint + שדות), החוזה המאושר (+ ה-scope שהקוד מחשב ממנו עכשיו),
  קריטריוני ה-ProductSpec (A1…), גרסאות מיגרציה, commit של ה-runtime ודגלים **מרשימה לבנה בלבד** (בלי סודות).
- `.github/workflows/evidence-export.yml` — מפעיל את זה על ה-worker (workflow_dispatch, קלט: `build_id`) ומפרסם את הפלט כ-annotations.
- הקבצים שנוצרו: workflow ‏`build-evidence.yml` הקיים (קלט `version_id`, `file_path`) מפרסם קובץ מגרסה.

## איך לייצא — חד-פעמי, בלי מיזוג ובלי פריסת worker
דורש אישורך: זו קריאה מה-DB החי (READ ONLY, בלי כתיבה, בלי עלות). אני לא מריץ אותה.
על מארח ה-worker, בתוך checkout של הענף הזה (או רק הקובץ `omni_prod/evidence_export.py` שהועתק), מתוך `infra/worker-host`:

```
docker compose run --rm --no-deps -T worker python - bld_<hex> < /path/to/omni_prod/evidence_export.py > evidence.json
```
התמונה שרצה כבר מכילה `psycopg` ו-`omni_prod`, והקובץ נקרא מ-stdin, לכן אין תלות במיזוג או בפריסה. ה-id של הבנייה נמצא במסך הפרויקט
(או `build-evidence` בלי קלט מציג את האחרונה). אפשר להריץ עם משתמש DB לקריאה בלבד; הטרנזקציה בכל מקרה READ ONLY.
העתק אליי את `evidence.json`. אין בו סודות (צנזור + רשימת דגלים לבנה); הבריף והחוזה מכילים את טקסט הלקוח.

**אישור שייך לבנייה:** הייצוא משתמש רק באישור ש-`used_by_build_id` שלו הוא בדיוק הבנייה הזו. אם אין כזה — `approval_status: MISSING` והבריף/חוזה
לא מדווחים (לא מוחלף באישור אחר); אם יש כמה — `AMBIGUOUS`. הקורא רואה את האישורים האחרים של הפרויקט בנפרד, לא בשימוש.

(`.github/workflows/evidence-export.yml` הוא נוחות לעתיד, אחרי מיזוג; לא נדרש לייצוא הזה.)

## אחרי הייצוא — מה אפרק
(a) היקף שגוי → `acceptance_scope_now` מול `defaults_applied`; (b) מיפוי חסר → `missing_acceptance_ids` מול `product_spec_acceptance` והצעדים הכשלים;
(c) באג נתונים/HTTP → `verification_failures` ו-`failed_steps`; (d) responsive → האם הצעד נכשל או שלא נכתב;
(e) תקיעה → האם `failed_steps` זהה בין הסבבים. רק אז תוצג מסקנה.

## עדכון 2026-10-11 (שלב ב)
הייצוא כולל עכשיו גם: הקבצים שנוצרו (`.omni/project.json`, רשימה עם sha256, טקסט מצונזר; `--files-dir` לחילוץ גולמי), הצעדים שנכשלו עם הראיות, שריון הקרדיט. ניתוח לא מקוון: `python -m omni_prod.failure_replay`.
פירוט ומה שחסר להרצה: `docs/DEPLOY_RECOVERY_REHEARSAL_HE.md` סעיף 4.
