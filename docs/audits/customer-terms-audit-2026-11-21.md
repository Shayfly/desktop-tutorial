# Customer-facing technical terms, origin/main a77c1b85, 2026-11-21

**One line:** on `origin/main` @ `a77c1b85` a customer must understand roughly 44 texts containing technical terms to get from sign-up to a finished site, and sees about 68 more; the target is zero. The root is that the UI names the machinery (spec, verifier, credits, candidate version, gates, providers) instead of the outcome and the next step.

Read-only audit: nothing edited, committed, pushed, run or launched. All paths are under `omni_prod/` on `origin/main`.

**Counting method:** one row = one text (or one family of sibling texts) the customer sees. B = blocking (must be understood to proceed), V = visible. A term with a plain explanation or a clear next action beside it is marked ½. Row counts are exact for what I list; the list itself is my reading of the code, not a mechanical extraction, so treat totals as a floor.

## 1. Tables per route

### Route 1 — sign up / log in

| # | Text (as written) | file:line | Term(s) | B/V | Plain replacement |
|---|---|---|---|---|---|
| 1.1 | "תארו את אפליקציית הווב שלכם." | assets/index.html:43, assets/app.js:10 | אפליקציית ווב | B | "ספרו איזה אתר אתם צריכים. אנחנו נבנה אותו." |
| 1.2 | "צופים בבנייה, בודקים בתצוגה מקדימה, משנים ומורידים את הקוד." | index.html:48 | תצוגה מקדימה, קוד | V | "רואים את האתר, מבקשים שינויים, ומקבלים אותו." |
| 1.3 | "כרגע: אפליקציות ווב ו-SaaS. מובייל, משחקים ומדיה עוד לא זמינים." (shown twice) | index.html:50, :83 | SaaS, ווב, מובייל, מדיה | V | "כרגע בונים אתרים. אפליקציות לטלפון ומשחקים — בהמשך." |
| 1.4 | "valid email required" / "password must be at least 10 characters", raw English | identity_lifecycle.py:432,434 → investor_app.py:1450 → app.js:359 | English in Hebrew UI | B | "כתובת המייל לא תקינה. בדקו אותה ונסו שוב." |
| 1.5 | "בנייה לא זמינה בשרת הזה. נדרשים PostgreSQL ואחסון S3." (banner after sign-in, deployment-dependent) | app.js:90, :433 | PostgreSQL, S3, שרת | B | "כרגע אי אפשר לבנות. נודיע לכם כשזה יחזור." |
| 1.6 | "שגיאה בשרת. נסו שוב בעוד רגע; אם זה חוזר, שלחו צילום מסך." / "אין חיבור לשרת." | app.js:98, :97 | שרת; no address for the screenshot | V | "משהו השתבש אצלנו. נסו שוב בעוד דקה." plus a real contact button |
| 1.7 | "(האימייל עדיין לא אומת.)" beside the email, no action | app.js:91, :423 | אומת | V | "שלחנו לכם מייל. לחצו על הקישור שבו." plus "שלחו שוב" |

### Route 2 — describe what you want and approve

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 2.1 | "הפרויקט הראשון שלכם / שם הפרויקט / יצירת פרויקט" (the chat box is hidden until a project exists) | index.html:108-111; app.js:459 | פרויקט | B | Drop the step: open the conversation directly and name it from the first message |
| 2.2 | "מצב שאלון מובנה — שיחת AI אינה פעילה כרגע" / "מצב שיחת AI מוגדר — הזמינות תלויה בספק ובתקציב" | app.js:278, :1667 | AI, ספק, תקציב | V | Remove |
| 2.3 | "התשובה הזו נבנתה מכללים קבועים, בלי מודל בינה מלאכותית." | app.js:279, :1677 | מודל | V | Remove |
| 2.4 | "השיחה החכמה עוד לא מותקנת בשרת הזה (חסר עדכון מסד נתונים 036)" / "נדרש עדכון מסד הנתונים (038)" | app.js:132, :280 | מסד נתונים, migration numbers, פריסה | V | "כרגע אי אפשר לצרף תמונות. כתבו במילים." |
| 2.5 | Tabs: "דרישות · תוכנית ועלות · בנייה · שינוי · גרסאות · פרטים · המוצר" | app.js:128 | דרישות, גרסאות | V | "מה ביקשתם · מחיר · האתר שלכם · שינויים" |
| 2.6 | "שלב 1 מתוך 2 — זה המפרט שהבנתי: …" / "אשרו את המפרט ואז אכין תוכנית" / button "אישור המפרט" | intake/approval_flow.py:161-162,166; app.js:129 | מפרט | B | "זה מה שהבנתי שאתם רוצים. נכון?" button "כן, זה נכון" |
| 2.7 | "המפרט אושר. הכנתי תוכנית והמאמת בדק אותה מול המפרט." / "המאמת מצא ותיקן: {what}" | approval_flow.py:169-170 | מאמת, מפרט | V | "מעולה. הכנתי הצעה." |
| 2.8 | "התוכנית לא עברה את בדיקת המאמת ולכן לא מוצגת: {what}. …אפשר לערוך את המפרט." where {what} is the verifier's raw problem list | approval_flow.py:171; conversation/supervisor.py:874 | מאמת, raw internals | B | "לא הצלחתי להכין הצעה. לא חויבתם. כתבו שוב במשפט אחד מה הכי חשוב לכם." |
| 2.9 | "הערכת עלות: {lo}–{hi} קרדיטים." / "עלות הבנייה במסלול שלך: {c} קרדיטים." / "העלות המדויקת: …" | approval_flow.py:163,165,172 | קרדיטים, מסלול (never given in ₪) | B | "זה יעלה X ₪. נשארו לכם Y ₪ החודש." |
| 2.10 | "…לפי המסלול שלך ומורכבות התוכנית ({cx})" with the raw complexity value | approval_flow.py:173,223 | raw value | V | "המחיר גבוה ממה שאמרתי כי ביקשתם יותר דברים." |
| 2.11 | Text says "אשרו את התקציב" and 'לחצו על "אישור והתחלת בנייה"'; the actual buttons are "לאישור והתחלת בנייה", "אשר והתחל בנייה", "אשר ובנה" | approval_flow.py:176; supervisor.py:179,204; app.js:129,27,36 | תקציב; three names for one button | B | One button, one name: "מאשר/ת — תתחילו לבנות" |
| 2.12 | "חלונות באתר — סמנו כל חלון שתרצו באתר. חלון שלא מסומן לא ייבנה." | app.js:130 | חלונות | B | "תוספות לאתר — סמנו מה שתרצו." |
| 2.13 | Window labels: "מגה-תפריט", "שער גיל", "הודעת עוגיות", "פופ-אפ מבצע כניסה", "סל נשלף", "פס מבצעים", "צ'יפים", "ווידג׳ט שאלה" (each has a benefit sentence) | window_catalog.py:48-69, benefits :79-93 | all eight labels | B ½ | Lead with the benefit sentence; drop the label |
| 2.14 | "יכולות שהבנייה צריכה": "מחזור בנייה מלא: תכנון, קוד, התקנה, בנייה, בדיקות, תיקונים, תצוגה וייצוא" plus pills "בתוך הבנייה"/"ספק חיצוני"; other rows are English `c.purpose \|\| c.key` | app.js:38,42,104,829-832 | יכולות, ספק חיצוני, English | V | Remove from the customer screen |
| 2.15 | "תשתית לאפליקציה": "מסד נתונים", "התחברות וסשנים", "אחסון קבצים", "משימות מתוזמנות", "מיילים ו-webhooks" with pills "פעיל / מוגדר, לא נבדק / לא מוגדר / חסום / מובנה באפליקציה" | app.js:38,43-44,122,834 | תשתית, סשנים, webhooks | V | Remove |
| 2.16 | "קרדיטים לבנייה" / "קרדיטים שנותרו" / "תמחור: מאושר · לא ניתן לתמחר · לא מאושר" (beside the approve button) | app.js:40,44,866-871 | קרדיטים, תמחור | B | "מחיר: X ₪ · נשאר לכם: Y ₪" |
| 2.17 | Status strip: "ניתן לבקש אישור בנייה" / "מוכנות הפרויקט טרם נבדקה" | app.js:119 | מוכנות, אישור בנייה | V | "אפשר להתחיל" / hide |
| 2.18 | "האפיון יכול להיות ישים טכנית, אך אישור הבנייה חסום עד להשלמת הדרישות, הספקים, התמחור והתקציב." | app.js:120, :857 | אפיון, ספקים, תמחור | B | "עוד אי אפשר להתחיל, כי <one reason>. מה לעשות: <one step>." |
| 2.19 | "הצעת המחיר אינה מאומתת. היתרה המוצגת אינה אישור לבנייה; יש להשלים תמחור ספק או להסיר דרישה באישורכם." / "אם יכולת אינה חלק מהבקשה שלכם, ערכו את האפיון. אם היא נדרשת, יש לאמת ספק ותמחור…" / "לחלק מהדרישות אין הצעת מחיר מאומתת" | app.js:904, :121, :113 | תמחור ספק, יכולת, אפיון | B | "את <X> עוד אי אפשר לבנות. לבנות בלי זה?" [כן] [לא, אחכה] |
| 2.20 | "תקציב בדיקות אב־טיפוס — פרטי / יתרה פנימית מוערכת / מגבלת הרשאה לבנייה אחת / …לא יתרות אצל ספקי ה־AI" with $ amounts | app.js:110-112, :873-880 | אב־טיפוס, ספקי AI, $ | V | Owner-only; hide from customers |
| 2.21 | "השרת הזה לא מוגדר לבנייה. פנו למפעיל השרת." (also for infrastructure and image generation) | build_readiness.py:50-55 | שרת, מפעיל השרת, תשתית | B | "כרגע אי אפשר לבנות. זה אצלנו, לא אצלכם. נודיע כשיחזור." |
| 2.22 | "תוכנית העבודה (מחלקות ומשימות)", "היתכנות: יש היתכנות טכנית", "שלב N: <department> · ארכיטקטורה / בדיקות בסביבה מבודדת / שער שחרור / סקירת קוד", "מודל הביקורת עשוי להיות מאותו ספק של מודל הכתיבה…", "הפירוש נעשה בכללים קבועים (ללא מודל AI)" (same tab as the approve button) | app.js:132-134, 1716-1723, 1768-1777, 1801 | היתכנות, ארכיטקטורה, שער שחרור, מודל | V | Remove |
| 2.23 | Font question: "כל האפשרויות תומכות בעברית ורישיונן ידוע (Google Fonts, OFL)."; options "Heebo — נקי ומודרני", "גופן המערכת (הכי מהיר)" | discovery.py:226-229 | OFL, Google Fonts, גופן המערכת | V | "איזה כתב יותר יפה בעיניכם?" with samples only |
| 2.24 | "אתר תוכן לא נבדק על יצירה ועריכה של נתונים. אם יש טופס שנשמר, הזמנות או רשימה שמתעדכנת — ענו 'לא'." (must be answered; the question itself is plain) | discovery.py:155-157 | נתונים, טופס שנשמר | B ½ | "האם מבקרים ישאירו אצלכם פרטים, למשל הזמנה או פנייה?" |
| 2.25 | "זה קובע אם יש מאגר נתונים בכלל" / "קובע כיוון כתיבה (ימין-לשמאל), פורמט תאריכים וניסוח." | intake/gaps.py:47; discovery.py:197 | מאגר נתונים, פורמט | V | Remove the reason line |
| 2.26 | "פרסום לכתובת קבועה (בשלב זה: תצוגה מקדימה וקוד להורדה)" / "שמירת נתונים לאורך זמן — הנתונים בתצוגה המקדימה זמניים" / screens default "…אין להוסיף מסכי ניהול או CRUD שלא התבקשו" (the last probably appears as the "מסכים" value; not confirmed on screen) | discovery.py:1096,1098,526 | תצוגה מקדימה, קוד, CRUD | V | "האתר עוד לא יעלה לכתובת משלכם. תקבלו קישור לצפייה." |
| 2.27 | "התממשקות Webhook" / "חיבור למערכת חיצונית (webhook)" | discovery.py:1110; build_readiness.py:73 | Webhook | V | "חיבור לתוכנה אחרת שלכם" |
| 2.28 | "כדי להתקדם, השלימו את המפרט בלשונית המפרט ואשרו משם." (no such tab; it is called "דרישות") | supervisor.py:191; app.js:128 | מפרט, לשונית | B | A button under the message: "להשלים את הפרטים" |
| 2.29 | "הגענו לתקרת העלות של השיחה עם הסוכן…" / "מספר התורות המרבי…" / "העומס אצל ספק המודל" / "ספק המודל סירב לבקשה בגלל החשבון שלנו אצלו" | supervisor.py:183-184,195-196 | סוכן, תורות, ספק המודל | V | "אני צריך הפסקה קצרה. מה שכתבתם נשמר. נסו שוב בעוד דקה." |
| 2.30 | Answer to "כמה זה עולה": "עלות הבנייה: {credits} קרדיטים. תקרת ההוצאה על מודלים לבנייה הזו: עד ${cap} (מוחזק לפני תחילת העבודה; מחויבת העלות בפועל)." | supervisor.py:202 | קרדיטים, מודלים, $, מוחזק | B | "זה יעלה X ₪. לא תשלמו יותר מזה." |
| 2.31 | English server sentences shown as-is: "The request was changed elsewhere. Reload to continue." / "The message is empty: write something, choose an answer or attach an image." / "This plan can no longer be used. Request the plan again." / "This idempotency key was already used for a different build request or quote." / "Approve the summary and plan first." | investor_app.py:1998,2185,365,2735,2766 → app.js:355-356 | English; idempotency key | B | Hebrew, one sentence plus one button each |
| 2.32 | "אפשר לצרף רק PNG, JPEG או WebP." / "…(עד 3MB)" | assets/visual-edit.js:14 | file formats, MB | V | "את התמונה הזו לא הצלחתי לקרוא. נסו לצלם מסך ולשלוח." |
| 2.33 | "ברירת מחדל" / "הפעלתי ברירת מחדל בטוחה: …" / "5 החלטות · נשארו 3" | app.js:25,20; supervisor.py:213 | ברירת מחדל | V | "בחרתי בשבילכם: … אפשר לשנות." |
| 2.34 | "עדיין אין ניתוח תמונה אוטומטי (צריך מודל עם יכולת ראייה ואישור תקציב)" | supervisor.py:225 | מודל עם יכולת ראייה | V | "קיבלתי את התמונה. כתבו במשפט מה רואים בה." |

### Route 3 — wait for the build

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 3.1 | Steps: "תכנון · חוזה בנייה · תשתית · נכסים (אייקון ותמונות) · יצירת קוד, בנייה, בדיקות ותיקונים · בדיקות איכות, אבטחה וזכויות · תצוגה מקדימה" | app.js:45-46 | חוזה בנייה, תשתית, נכסים, קוד | V | "מכינים · מציירים תמונות · בונים · בודקים · מוכן" |
| 3.2 | "הבנייה, הבדיקות והתיקונים רצים בשלב אחד. מספר סבבי התיקון מדווח בסיום." / "סבבי תיקון: N" | app.js:47-48 | סבבי תיקון | V | "זה לוקח בערך N דקות." |
| 3.3 | "ממתין בתור: 2 עבודות לפני הבנייה שלך" | app.js:48 | תור, עבודות | V ½ | "יש שניים לפניכם. מתחילים בעוד בערך N דקות." |
| 3.4 | Log: "בודק את התוכנית והחוזה שאושרו", "מכין את התשתית של המוצר", "מכין תמונות ונכסים", "מתחיל לכתוב את הקוד, להריץ בדיקות ולתקן" | job_repository.py:29-33 | חוזה, תשתית, נכסים, קוד | V | "מכינים את התמונות", "בונים את העמודים", "בודקים שהכול עובד" |
| 3.5 | Log: "מתכנן את מבנה המוצר והבדיקות", "כותב את הקוד", "בודק איכות (QA) את הקוד", "שולח בקשה למודל" | build_control.py:37-42,116 | QA, קוד, מודל | V | as above |
| 3.6 | Log: "סבב בדיקות {n}: {k} נכשלו — {reason}. מתקן." where {reason} is the first failure's raw message, up to 180 characters | build_control.py:146-148 | raw technical text; "נכשלו" mid-build | V | "מצאנו משהו לתקן ומתקנים. אין צורך לעשות דבר." |
| 3.7 | Log: "סבב תיקון {i} החמיר את המוצר ונזרק; ממשיכים מהגרסה הטובה ביותר." | worker_tasks.py:160 | סבב תיקון, גרסה | V | Remove |
| 3.8 | "ממתין לשרת הבנייה…" | app.js:53 | שרת | V | "מתחילים…" |
| 3.9 | Chat status line: "הבנייה רצה · GENERATING · 3 הושלם" (raw English phase) | app.js:1695-1697 | raw phase name | V | "בונים את האתר שלכם (שלב 3 מתוך 5)" |
| 3.10 | "פרטים טכניים: מי עושה מה (מהרישום בשרת) · 3/15" with department, "בדיקות בסביבה מבודדת", "שער שחרור", "חישוב עלות", "בתיקון", "לא נרשם" (collapsed) | app.js:134-135, 1774-1777, 1794-1797 | whole board | V | Remove for customers |
| 3.11 | "לעצור את הבנייה? נחויב רק על מה שכבר נוצל, והגרסה לא תיווצר." | app.js:51 | גרסה; charge amount unknown | V | "לעצור? תשלמו עד X ₪ על מה שכבר נעשה, והאתר לא יהיה מוכן." |
| 3.12 | Answer to "מה המצב": "הבנייה האחרונה: {status}{phase}. משימות: {done} הושלמו, {running} בתהליך…" (raw status) | supervisor.py:206 | raw status, משימות | V | "האתר שלכם באמצע הבנייה. עוד בערך N דקות." |
| 3.13 | "מאמתים אישור ותקציב — הבנייה עדיין לא התחילה." | app.js:54 | מאמתים, תקציב | V | "רגע, מתחילים…" |

### Route 4 — a build that fails

Every row below except 4.8, 4.11, 4.12 and 4.23 offers no next step.

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 4.1 | "הבנייה נכשלה: הקוד שנוצר לא עבר את הבדיקות האוטומטיות גם אחרי סבבי תיקון." | app.js:49,56 | קוד, סבבי תיקון | B | "לא הצלחנו לבנות את האתר הפעם. לא חויבתם. [לנסות שוב] [לפשט את הבקשה]" |
| 4.2 | "המוצר לא סומן כמוכן: אחת הבדיקות המחייבות (הפעלה, בדיקת התנהגות, בדיקת דפדפן או סקירת איכות) לא עברה או לא רצה. הפירוט בפרטים הטכניים." | app.js:58 | all check names; "פרטים טכניים" as the next step | B | same as 4.1 |
| 4.3 | "הקוד עבד, אבל לא עמד ברף האיכות הנדרש גם אחרי סבבי תיקון." | app.js:59 | רף האיכות | B | "האתר נבנה אבל לא יצא מספיק טוב, אז לא נתנו לכם אותו. [לנסות שוב]" |
| 4.4 | "הקוד עבר את הבדיקות, אבל האתר לא עלה בהפעלת ניסיון ולכן לא אושר." | app.js:60 | הפעלת ניסיון | B | same as 4.1 |
| 4.5 | "נמצאה בעיית אבטחה בקוד שנוצר, ולכן הוא לא אושר." | app.js:61 | אבטחה בקוד | B | same as 4.1 |
| 4.6 | "הגרסה נשמרה, אבל חסר אישור זכויות לפני פרסום." | app.js:62 | אישור זכויות, גרסה | B | "האתר מוכן, אבל יש בו תמונה או שם שאולי שייכים למישהו אחר. <what> — [להחליף] [זה שלי]" |
| 4.7 | "הקוד ביקש ספרייה חיצונית שעדיין לא נתמכת בפלטפורמה." | app.js:63 | ספרייה חיצונית, פלטפורמה | B | same as 4.1 |
| 4.8 | "הבנייה הפסיקה להגיב ושוחררה. לא חויבו קרדיטים. אפשר לנסות שוב." | app.js:64 | שוחררה, קרדיטים | V ½ | "הבנייה נתקעה. לא חויבתם. [לנסות שוב]" |
| 4.9 | "עוד לא ברור כמה נוצל, ולכן הסכום שמור עד שהחיוב יתברר." | app.js:66 | סכום שמור | V | "נעדכן אתכם עד מחר כמה חויבתם, אם בכלל." |
| 4.10 | "אירעה תקלה פנימית במהלך הבנייה. הצוות קיבל את הפרטים." | app.js:67 | no next step at all | B | "…אנחנו בודקים. [לנסות שוב]" |
| 4.11 | "הבנייה הגיעה לתקרת העלות שנקבעה לה ונעצרה… אפשר לנסות שוב." | app.js:68 | תקרת העלות | V | "הבקשה גדולה מדי למחיר הזה. [לפשט] [לאשר מחיר גבוה יותר]" |
| 4.12 | "ספקי ה־AI לא היו זמינים כרגע (עומס או מכסה). אפשר לנסות שוב בעוד כמה דקות." | app.js:69 | ספקי AI, מכסה | V | "יש עומס אצלנו. נסו שוב בעוד כמה דקות." |
| 4.13 | "לפחות ספק AI אחד דיווח שנגמרה המכסה או יתרת הקרדיטים. אין כרגע ספק חלופי… בדקו את הספק שמופיע בהמשך." followed by the raw route name | app.js:70, :1258-1262 | ספק AI, מכסה; customer told to check a provider | B | same as 4.12 |
| 4.14 | "מדיניות השימוש במודלים לא אפשרה את הבנייה בסביבה הזו." | app.js:71 | מדיניות, מודלים, סביבה | B | same as 4.10 |
| 4.15 | "יכולת נדרשת (למשל יצירת תמונות) לא אומתה, ולכן הבנייה לא אושרה." | app.js:72 | יכולת, אומתה | B | "לא הצלחנו ליצור את התמונות. [לבנות בלי תמונות] [לנסות שוב]" |
| 4.16 | "…זו גרסת בדיקה בלי תור בנייה. הקרדיטים הוחזרו." / "…שרת הבנייה לא מצא אותה… פנו אלינו." (no contact channel in the UI) | app.js:56 | תור בנייה, שרת | V | add a real contact button |
| 4.17 | Nine "התיקון האוטומטי נעצר: …" lines, e.g. "…נגמר באותו כשל בדיוק כמו הסבב שלפניו", "אותו ערך צפוי בבדיקה תוקן פעמיים, ולכן הבנייה הועברה לבדיקה ידנית", "אף מודל לא החזיר תיקון תקין (תשובה שאינה בפורמט, תשובה שנקטעה, או ספק בלי יתרה)" | app.js:87, :1235-1241 | סבב, כשל, פורמט, מודל | V | Remove for customers |
| 4.18 | Unknown stop reason: "התיקון האוטומטי נעצר: <raw_code>" | app.js:1240 | raw code | V | Remove |
| 4.19 | "בדיקות שלא רצו: הפעלת ניסיון, בדיקת התנהגות, בדיקת דפדפן, סוקר שאינו הכותב, עקביות בין הקבצים, ספריות מאושרות…"; an unknown check prints its raw key | app.js:84-85, :1229-1230 | every check name | V | Remove for customers |
| 4.20 | "פרטים טכניים" with the raw `error_message` (collapsed) | app.js:1114 | raw English | V | Owner-only |
| 4.21 | Codes with no customer text print the raw English exception as the reason ("הבנייה נכשלה: <English>"): `infrastructure_not_configured`, `capability_not_configured`, `gate_escalation`, `attempt_ledger_unavailable`, `plan_violation` | app.js:1275; worker_tasks.py:1323,1351,1298,425-427 | raw English | B | A default Hebrew line plus [לנסות שוב]; never the raw text |
| 4.22 | "פרטים" tab: "פרטים טכניים ועדויות": "בדיקות: אימות: ✓, איכות: ✗…", literal "billing", "capabilities: …", raw JSON of `build_contract` / `infrastructure` | index.html:149; app.js:1455-1461 | all of it | V | Owner-only |
| 4.23 | In the chat: "הבנייה נכשלה. לא חויבתם — הקרדיטים הוחזרו. אפשר לנסות שוב." with button "לנסות לבנות שוב" | build_announcement.py:21-23; app.js:276,1655 | קרדיטים | V | Good shape; say ₪ and add "מה לשנות כדי שיצליח" |
| 4.24 | "פתח את הטיוטה בתצוגה (לא עברה את כל הבדיקות)" (owner drafts) | app.js:50, :1116 | טיוטה, בדיקות | V | — |

### Route 5 — see the result (preview, enlarge, share)

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 5.1 | "מפעילים תצוגה מקדימה…" / "התצוגה המקדימה פגה. אפשר להפעיל אותה מחדש." button "הפעלת תצוגה מקדימה" | app.js:74-77, :1184 | תצוגה מקדימה, פגה | B ½ | "האתר שלכם נרדם. [להעיר אותו]" or wake it automatically |
| 5.2 | "הגרסה הזאת לא ניתנת להצגה מקדימה: " plus raw reason, e.g. "repository has no .omni/project.json" | app.js:75, :1134, :1173; preview_runtime.py:134-191; investor_app.py:3052 | raw English, repository | B | "את האתר הזה אי אפשר להציג כרגע. [לבנות מחדש]" |
| 5.3 | "תצוגה מקדימה לא זמינה בשרת הזה: " / "התצוגה המקדימה נכשלה: " plus raw `error_message` | app.js:75-76, :1174-1175 | שרת, raw text | B | "לא הצלחנו להציג את האתר. [לנסות שוב]" |
| 5.4 | Address bar with the raw preview URL | index.html:174; app.js:1153 | raw URL | V | "האתר שלכם" plus [העתק קישור] |
| 5.5 | "רענון" / "פתיחה בלשונית חדשה" | index.html:176-177 | רענון, לשונית | V | "טען מחדש" / "פתח במסך מלא" |
| 5.6 | "נתונים זמניים: מה שתזינו יימחק כשהתצוגה תיעצר." / "…נשמרים גם אחרי הפעלה מחדש ובגרסה הבאה (אין עדיין גיבוי)." | app.js:99-100 | נתונים זמניים, גיבוי, גרסה | V | "זה אתר לניסיון: מה שתמלאו בו לא יישמר." |
| 5.7 | Sharing: "כולם (ציבורי)" shows no link at all; the link box appears only for "כל מי שיש לו קישור שיתוף" | app.js:100, :1210-1212 | ציבורי; no address to send | B | Always show: "זה הקישור לשלוח: … [העתק] [שלח בוואטסאפ]" |
| 5.8 | "הורדת קוד המקור (ZIP)" | index.html:198 | קוד מקור, ZIP | V | Move under "מתקדם" |
| 5.9 | Button "פרסום" → "הפרסום לאוויר עוד לא מוגדר בשרת הזה. אפשר להוריד את הקוד ולבדוק בתצוגה המקדימה." / "פרסום בכתובת קבועה עדיין אינו זמין. קיימות תצוגה פרטית והורדת קוד." | index.html:199; app.js:32, :1474, :1767 | פרסום לאוויר, שרת, קוד | B | See worst #1 |
| 5.10 | "גרסה נוכחית: `<12-char id>` · date · N קבצים" | app.js:1304-1305 | גרסה, raw id, קבצים | V | "עודכן לאחרונה: <date>" |
| 5.11 | Version name falls back to internal messages when there is no title: "148AI async live build bld_…", "148AI PREVIEW ONLY build … — בדיקה קריטית הושעתה… פרסום לפרודקשן חסום", "rollback from workspace", "accepted in workspace", "undo visual edit". Which versions lack a title is not confirmed. | app.js:1299,1316,1322,1399; worker_tasks.py:807-813,290-291; visual-edit.js:~305 | English, bld_ id, פרודקשן | V | "האתר כפי שנבנה ב-<date>" / "אחרי השינוי: <customer's words>" |
| 5.12 | "גרסאות / נוכחית / שחזור לגרסה הזו / שוחזר. נוצרה גרסה חדשה." with id | app.js:79, :1316 | גרסה, שחזור | V | "חזרה לאתר כפי שהיה ב-<date>" |
| 5.13 | Page a visitor sees: "התצוגה הזאת פרטית… רק מתוך סביבת העבודה של 148AI, או בקישור שיתוף…" | preview_router.py:71-75 | תצוגה, סביבת העבודה | V ½ | "האתר הזה עוד לא פתוח לכולם. בקשו מבעל האתר קישור." |
| 5.14 | On success: "הבנייה הסתיימה בהצלחה." followed by "בדיקות שלא רצו: …" | app.js:1107 | check names | V | "האתר שלכם מוכן!" |

### Route 6 — ask for a change

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 6.1 | "בחירת רכיב לעריכה" (hint: 'לחצו "בחירת רכיב" ואז על החלק בתצוגה שתרצו לשנות') | index.html:197,214-215; visual-edit.js:17,20 | רכיב | B ½ | "הצביעו על מה שתרצו לשנות" |
| 6.2 | "מצב בחירה: … Esc לביטול." | visual-edit.js:17 | Esc | V | "לחצו שוב כדי לבטל" |
| 6.3 | "נמצא בקוד: `file:line`" | visual-edit.js:24, ~333 | קוד, file path | V | Remove |
| 6.4 | "הרכיב מופיע בכמה מקומות. באיזה מהם מדובר?" with options "בקובץ X" and a "פרטים טכניים" block of file:line and code | visual-edit.js:25,35, ~336-343 | רכיב, קובץ, code | B | Highlight each candidate in the page: "זה? או זה?" |
| 6.5 | "בחירה ישירה בתצוגה עדיין לא זמינה בשרת התצוגות הזה…" | visual-edit.js:19 | שרת התצוגות | V ½ | "כרגע אי אפשר להצביע. כתבו במילים מה לשנות." |
| 6.6 | "השינוי נשלח. בונים גרסה מועמדת ובודקים אותה…" → "הגרסה המועמדת עברה את הבדיקות. מה תרצו לעשות?" [אישור השינוי] [דחייה] | app.js:80-81; visual-edit.js:28 | גרסה מועמדת | B | "השינוי מוכן. הסתכלו. [לשמור] [לא, להחזיר]" |
| 6.7 | "סיווג: {classification}" (raw value) | app.js:82, :1418 | סיווג, raw value | V | Remove |
| 6.8 | "השינוי נכשל: " / "השינוי לא הצליח: " plus raw `error_message`, `classification_reason`, or the raw status (CONFLICT, NEEDS_CLARIFICATION) | app.js:1423; visual-edit.js:29, ~365 | raw English | B | "לא הצלחתי לעשות את השינוי. האתר נשאר כמו שהיה. כתבו אותו אחרת, או [נסו שוב]." |
| 6.9 | Log: "מסווג את בקשת השינוי", "כותב את השינוי", "מתחיל לעבד את בקשת השינוי" | build_control.py:41-42; worker_tasks.py:1664 | מסווג | V | "עובדים על השינוי…" |
| 6.10 | "אשרו ואשלח את השינוי לצנרת השינויים (תוצג עלות לפני ביצוע)." I found no cost display before the change is sent (app.js:1657-1658). | supervisor.py:207 | צנרת השינויים | V | "לעשות את השינוי? זה יעלה X ₪. [כן]" |
| 6.11 | "לחזור לגרסה שלפני השינוי? תיווצר גרסה חדשה זהה לה." | visual-edit.js:30 | גרסה | V | "להחזיר את האתר לאיך שהיה לפני השינוי?" |
| 6.12 | "צילום המסך נשמר בפרויקט ונשלח עם השינוי כהקשר (בלי ניתוח תמונה אוטומטי)." | visual-edit.js:32 | הקשר, ניתוח תמונה | V | "קיבלנו את הצילום." |
| 6.13 | "לעצור את השינוי? נחויב רק על מה שכבר נוצל." | app.js:51 | charge amount unknown | V | state the amount |

### Route 7 — account, plan, credits/billing

There is no account, plan or billing screen. The UI calls only `/api/v28/me` (app.js:440); `/api/v28/billing/checkout` exists on the server (investor_app.py:1421) but nothing in app.js or visual-edit.js calls it.

| # | Text | file:line | Term(s) | B/V | Replacement |
|---|---|---|---|---|---|
| 7.1 | "הבנייה הזו לא כלולה במסלול שלך. אפשר לשדרג מסלול." / "נגמר התקציב או הקרדיטים. אפשר להוסיף קרדיטים או לבנות פרויקט קטן יותר." / "שדרגו את המסלול, או צמצמו את הבקשה." (no upgrade or add-credits control exists) | app.js:95; build_readiness.py:46-47 | מסלול, קרדיטים, לשדרג | B | "זה יעלה X ₪ יותר ממה שנשאר לכם. [להוסיף X ₪] [לבנות אתר קטן יותר]" |
| 7.2 | "אין מספיק קרדיטים או שהמסלול לא מאפשר זאת: " plus a raw English reason, e.g. "monthly credits exhausted" | app.js:94, :352; investor_app.py:1746,1824,3230,3751; subscription_store.py:185-188 | English | B | as 7.1 |
| 7.3 | "קרדיטים" is never defined or converted to money anywhere; the plan name and what it includes are never shown | app.js:40, :866-870 | קרדיטים, מסלול | B | Show ₪ only |
| 7.4 | "הגעתם למכסת הפרויקטים הפעילים (3/3). ניתן לארכב פרויקט קיים או לשנות תוכנית. זו אינה בעיית קרדיטים." | app.js:342 | מכסה, לארכב, "תוכנית" used to mean the plan | B ½ | "אפשר להחזיק עד 3 אתרים. [להעביר אתר ישן לארכיון]" |
| 7.5 | "המסלול שלך לא כולל בנייה בגודל הזה." / "הקרדיטים החודשיים נגמרו." / "תקציב הבנייה של המסלול לחודש הזה נגמר." (no action attached) | app.js:109; build_readiness.py:61-63 | מסלול, קרדיטים חודשיים | B | "נגמר מה ששילמתם עליו החודש. יתחדש ב-<date>. [להוסיף עכשיו]" |
| 7.6 | Three money units on the same journey: "N ₪ הערכה" on the proposal card, "קרדיטים" in the chat and plan, "$" in the cost answer and budget block | app.js:747, :868, :712; supervisor.py:202 | units | V | One unit: ₪ |
| 7.7 | "העברה לארכיון" / "ניהול פרויקט" | index.html:255-259 | ארכיון | V | "להסתיר את האתר הזה" |

## 2. Counts

| Route | Blocking rows | Visible rows | Weighted (B / V) |
|---|---|---|---|
| 1. Sign up / log in | 3 | 4 | 3 / 4 |
| 2. Conversation and approval | 15 | 19 | 14 / 19 |
| 3. Waiting | 0 | 13 | 0 / 12.5 |
| 4. Failure | 12 | 12 | 12 / 11.5 |
| 5. Result / share | 5 | 9 | 4.5 / 8.5 |
| 6. Change | 4 | 9 | 3.5 / 8.5 |
| 7. Account / billing | 5 | 2 | 4.5 / 2 |
| **Total** | **44** | **68** | **41.5 / 66** → 112 rows, 107.5 weighted |

- Distinct technical terms across those rows: about 75 (estimate; I did not de-duplicate mechanically).
- Recurring core terms: מפרט, מאמת, קרדיטים, מסלול, גרסה / גרסה מועמדת, תצוגה מקדימה, בנייה, קוד, שרת, ספק, מודל, סבב תיקון, רכיב, פרויקט, תשתית, יכולת, דרישות, אפיון, תמחור.
- "בנייה" itself appears in most of the UI; I did not count it per occurrence.

## 3. The five worst

1. **There is no finish (5.9).** The "פרסום" button answers "הפרסום לאוויר עוד לא מוגדר בשרת הזה. אפשר להוריד את הקוד…" (app.js:32, :1474). The customer's goal, a site on an address they can give people, has no path. *Missing next action:* how the site becomes public — at minimum a permanent share link with [העתק] / [שלח בוואטסאפ]. Related: choosing "כולם (ציבורי)" shows no link at all (app.js:1212).
2. **Approval: three vocabularies and a button that does not exist (2.6, 2.9, 2.11, 2.16).** The customer approves "המפרט", then "התקציב", priced in undefined "קרדיטים" beside a ₪ estimate. The text tells them to press "אישור והתחלת בנייה", while the real buttons are "לאישור והתחלת בנייה" → "אשר והתחל בנייה", or "אשר ובנה" on the proposal card. *Missing:* one price in ₪ and one button whose label matches the sentence.
3. **A failed build explains the machinery and stops (4.1-4.7, 4.10, 4.13-4.15, 4.21).** For example "…אחת הבדיקות המחייבות (הפעלה, בדיקת התנהגות, בדיקת דפדפן או סקירת איכות) לא עברה או לא רצה. הפירוט בפרטים הטכניים." (app.js:58). Five codes fall through to the raw English exception (app.js:1275). *Missing:* what the customer can do differently; the only action is "לנסות לבנות שוב" (same request, same approval screen), and "פנו אלינו" / "פנו לתמיכה" / "פנו למפעיל השרת" / "שלחו צילום מסך" have no contact channel anywhere in the UI.
4. **Money walls with no door (7.1-7.5).** "אפשר לשדרג מסלול" and "אפשר להוסיף קרדיטים" (app.js:95), but no screen, link or button does either; the 402 path appends raw English (app.js:352). *Missing:* any way to pay, see the plan, or learn when credits renew.
5. **Dead-end pointers during the conversation and the change (2.28, 2.8, 6.4, 6.8).**
   - "השלימו את המפרט בלשונית המפרט ואשרו משם" (supervisor.py:191): no tab has that name.
   - "התוכנית לא עברה את בדיקת המאמת… {raw problems}… אפשר לערוך את המפרט": it does not say what to edit.
   - The visual editor asks the customer to choose between files and code snippets.
   - "השינוי נכשל: CONFLICT". *Missing:* a single button under each message that performs the step.

Also notable: a new customer must create a "פרויקט" before the chat box appears (2.1), and the live log prints "N נכשלו — <raw failure text>" while the build is still succeeding (3.6).

## 4. What the code cannot show, and how to measure it

| Runtime text | Why code is not enough | How to measure |
|---|---|---|
| The conversation agent's replies and question wording (`OMNI_INTAKE_AGENT`; models in intake/conversation_agent.py: `openai-gpt-6-luna`, `claude-sonnet-5-5`) | Free model text; only the fixed fallback lines in section 1 are in code | Run the `Conversation rehearsal` workflow (.github/workflows/conversation-rehearsal.yml). It prints `CONVERSATION {json}` with a `transcript` per scenario (conversation_rehearsal.py:301,362) and `::notice title=conversation <scenario> turn N::`. Count terms per assistant turn against the list in section 2. For production, read the assistant rows of the stored conversation, read-only. |
| The spec summary `{summary}` at step 1, the goal, "כלול / לא כלול", `semantic_review` labels | Composed from the brief and model interpretation | Same transcript, at the turn where `gate == 'spec'`; plus the JSON of `GET /api/v28/projects/{id}/conversation`. |
| Proposal card rows, `generic_reason`, `price.basis`, `facts[].source_ref` | Built per request (first_agent/structure.py, price_v0.py) | `GET /api/v28/projects/{id}/proposal` in a rehearsal project. |
| Plan panel: `product.summary`, `user_roles`, `data_requirements`, `required_integrations`, capability `purpose`, task `department` | Architect and planner output; `purpose` is English in capability_planner.py; I did not confirm whether `department` is a key or an English name | Response of `POST …/build-contracts` and `GET …/builds/{id}/plan` from a golden rehearsal. |
| `{reason}` in "סבב בדיקות N: k נכשלו — {reason}" and `error_message` under "פרטים טכניים" | Raw verifier and exception text | The build events table (`GET …/builds/{id}/events`) for the builds listed in `smoke/rehearsal-builds.jsonl`; the `Golden build rehearsal` output (`rehearsal.out`). |
| Modification `classification`, `classification_reason`, `error_message` | Model and classifier output | `GET …/modifications/{id}` and its `/events` after a rehearsal change. |
| `blocked_reason.message/next` with interpolated capability names; 409/422 `detail.message` from `str(exc)` | Many are exception strings; I listed only the literal ones | Grep production logs for 4xx bodies on `/api/v28/projects/*`, or force each blocker in a rehearsal. |
| Version titles, summaries, features in "המוצר" | From the stored ProductSpec; which versions fall back to internal messages (5.11) is not confirmed | `GET /api/v28/projects/{id}/history` on a project that has a rollback and an accepted change. |
| The generated site itself | Out of scope here | The `he_*` and `copy_*` skill-unit probes. |

## מה עוד פתוח

- **Not tested:** nothing was run or rendered. Every row is from source on `origin/main` @ `a77c1b85`; whether a given conditional text appears for a given account or flag (rows 1.5, 2.4, 2.20, 4.24, 5.11) is not confirmed on screen.
- **English and Arabic UI strings** were not counted. The `en` table (app.js:137-266) mirrors the Hebrew one with the same terms (spec, gates, credits, candidate version, provider quota).
- **`omni_prod/assets/app.css`** was not scanned for `content:` strings.
- **`replicate-test.html`, `/r2-diagnostics` and `/hosted/v2x` pages** were treated as non-customer and not audited.
- **`ui_translations.py`** (the `UI_COPY` for 20 locales, including "זכויות ו-IP", "מוכנות גלובלית") is not referenced by `assets/app.js`. I did not confirm whether any customer page still uses it.
- **Row 6.10:** the chat promises "תוצג עלות לפני ביצוע" for a change, and I found no cost display before `sendModification`. This looks like a product gap, not only wording; worth confirming.
- **The distinct-term count (about 75) is an estimate.** A mechanical count would need an agreed term list as a file.
- Scratch copies of the audited files are under `/tmp/claude-0/-home-user-desktop-tutorial/ef722132-a1de-581a-aa3a-c4e5105bcddd/scratchpad/audit/` (outside the repository; safe to delete).
- No merge, no SHA to approve: this was a read-only audit.
