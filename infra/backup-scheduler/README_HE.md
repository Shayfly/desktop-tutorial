# גיבוי מתוזמן שבאמת רץ

**הבעיה (מאומתת):** `backup-restore.yml` נמצא רק בענף ה-milestone. GitHub מפעיל `schedule` רק מהענף הראשי (`main`),
ולכן ה-cron `17 2 * * *` מעולם לא רץ; הריצות שקיימות הן `workflow_dispatch` ידניות.

**הפתרון המוצע:** קובץ אחד, `backup-scheduler.yml` (בתיקייה הזו, לא פעיל כאן), שיושב ב-`main`, מפעיל את
`backup-restore.yml` על ענף ה-milestone ונכשל בקול אם אין גיבוי מוצלח צעיר מ-30 שעות.

**לא הותקן.** יש שתי דרכים, וכל אחת דורשת אישור נפרד שלך:
1. PR של קובץ בודד ל-`main`. אזהרה: Vercel בונה Production מכל commit ב-`main`, ולכן זה עלול להפעיל פריסת Production
   (שינוי של קובץ workflow בלבד, אבל עדיין build). אפשר לבדוק לפני כן אם ל-Vercel מוגדר Ignored Build Step.
2. שינוי ה-default branch של המאגר ל-`milestone/pre-staging-2026-10-05` (הגדרת מאגר; גם משנה מה ש-Vercel רואה כ-Production
   אם ה-production branch לא מקובע — לבדוק קודם).

**אימות אחרי ההתקנה (חובה):** הריצה הקרובה של ה-cron האמיתי (לא dispatch ידני) חייבת להופיע כ-`schedule` ב-Actions,
ואחריה ריצת `backup-restore.yml` מוצלחת חדשה עם שחזור. עד אז הסטטוס: *מוכן, לא מאומת בשטח*.
