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

## איך לייצא (דורש אישורך — זו קריאה מה-DB החי)
1. מצא את ה-id של הבנייה (`bld_…`) במסך הפרויקט, או הרץ `build-evidence` בלי קלט (מציג את האחרונה).
2. Actions → ‏Evidence export (read-only) → Run workflow על `milestone/pre-staging-2026-10-05` עם ה-`build_id`.
   (הקובץ יהיה זמין להפעלה רק אחרי שהענף יידחף וימוזג — לכן זה תלוי באישור ה-push.)
3. העתק את ה-annotations (`evidence 1/N`…) אליי. אין בהם סיסמאות; בריף/חוזה מכילים את טקסט הלקוח עצמו.

## אחרי הייצוא — מה אפרק
(a) היקף שגוי → `acceptance_scope_now` מול `defaults_applied`; (b) מיפוי חסר → `missing_acceptance_ids` מול `product_spec_acceptance` והצעדים הכשלים;
(c) באג נתונים/HTTP → `verification_failures` ו-`failed_steps`; (d) responsive → האם הצעד נכשל או שלא נכתב;
(e) תקיעה → האם `failed_steps` זהה בין הסבבים. רק אז תוצג מסקנה.
