# גיבוי מתוזמן שבאמת רץ

**הבעיה (מאומתת):** `backup-restore.yml` נמצא רק בענף ה-milestone. GitHub מפעיל `schedule` רק מהענף הראשי (`main`),
ולכן ה-cron `17 2 * * *` מעולם לא רץ; הריצות שקיימות הן `workflow_dispatch` ידניות.

**הפתרון המוצע:** קובץ אחד, `backup-scheduler.yml` (בתיקייה הזו, לא פעיל כאן), שיושב ב-`main`, מפעיל את
`backup-restore.yml` על ענף ה-milestone ומחכה שהריצה **החדשה** תסתיים ב-`success`. שיגור אינו גיבוי: המתזמן מדווח בנפרד DISPATCHED/STARTED/SUCCEEDED, ורק הצלחת הריצה החדשה מצבעת אותו בירוק; גיבוי ישן אינו נחשב.

**לא הותקן ולא פעיל.** הדרך היחידה שמוצעת: PR של קובץ בודד ל-`main`, באישור נפרד שלך. *שינוי ה-default branch אינו מוצע ולא יבוצע כפתרון.*
אזהרה: Vercel בונה Production מכל commit ב-`main`, ולכן גם שינוי של קובץ workflow בלבד עלול להפעיל build; לפני כן לבדוק Ignored Build Step ב-Vercel.

**אימות אחרי ההתקנה (חובה):** הריצה הקרובה של ה-cron האמיתי (לא dispatch ידני) חייבת להופיע כ-`schedule` ב-Actions,
ואחריה ריצת `backup-restore.yml` מוצלחת חדשה עם שחזור. עד אז הסטטוס: *מוכן, לא מאומת בשטח*.
