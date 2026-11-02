# החלטת ממשל מוצעת — main branch protection (2026-11-02)

**סטטוס: PROPOSED / NOT APPLIED — אישור בעלים נדרש.**

## רקע
ממצא 5 בביקורת `docs/AUDIT_2026-11-02.md` (מסמך המקור לא נמצא ב-main בעת עריכת הצעה זו; יש לצרפו ולאמת את נוסחו לפני מיזוג). לפי דיווח המייסד, כיום רק `test` ו-`validate` חוסמים מיזוג, ולא שבעת השערים בפועל.

## החלטה מוצעת
ב-GitHub Settings → Branches/Rulesets עבור `main`: להגדיר required status checks בדיוק בשמות שמדווחים בפועל: `test`, `validate`, `pg`, `pg-tests`, `browser-tests`, `customer-ui`, `compose-config`; להפעיל `enforce_admins=true` (כולל מנהלים). לפני הפעלה יש לאמת check-run context + source app + event coverage לכל שם, ולשמור snapshot של הכלל הנוכחי. אין לשנות הגדרות במסגרת PR זה.

## כשל ללא השינוי
PR יכול להתמזג כש-PostgreSQL, browser, UI או compose אדומים או חסרים, כל עוד `test` ו-`validate` ירוקים; הרשאות מנהל עלולות לעקוף את השער. זה מסכן נכונות בנייה, התאמת סכימה ונתיב לקוח.

## סיכונים ותנאי הפעלה
Check שאינו נוצר על כל PR או שמדווח בשם אחר יחסום מיזוגים. יש לוודא שכל שבעת ה-checks מופיעים ב-PR ניסוי, נכשלים כמצופה במצב אדום, ושכללי bypass אינם מאפשרים עקיפה. בדיקות על merge queue, אם קיים, צריכות לתמוך ב-merge_group. `enforce_admins` לבדו אינו תחליף לבדיקה של bypass permissions, reviewer identity או מניעת self-approval. אין להפעיל עד אישור מפורש של הבעלים.

## Rollback
שמור מראש export/screenshot של הגדרות ההגנה וה-contexts; במקרה חסימה שגויה שחזר את רשימת `test`, `validate` ואת ערך `enforce_admins` הקודם. תעד מי אישר, מתי, למה ומה בוטל. אל תסיר את כלל ההגנה כולו.
