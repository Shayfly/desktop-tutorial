# 148AI — הוראת ביצוע ראשית מעודכנת

גרסה: 1.0 | תאריך: 09.10.2026 | בעל המוצר: שי | יעד: Partner Review Candidate

## 0. סמכות המסמך ומה צריך לבצע עכשיו

Claude: זהו מסמך הביצוע המאוחד. הוא מחליף הנחיות קודמות שסותרות אותו, במיוחד הגבלת שאלות האפיון לחוסרים קריטיים בלבד, עבודה לא מתואמת בענף הפעיל וסימון תפקיד שלם כמאומת על בסיס בנייה אחת.

אין להתחיל את המערכת מחדש. יש לבדוק את הקיים, להשתמש בו, להשלים את החסר ולמסור מוצר עובד עם ראיות. תחילת המשימה מחדש משמעותה תוכנית מאוחדת ומעודכנת, לא מחיקת העבודה הקיימת.

המטרה היא חברת תוכנה ויצירה מנוהלת בתוך מוצר: הבנת לקוח, אפיון, עיצוב, תכנון, ביצוע, בדיקה, תיקון, תצוגה, שינוי ומסירה. הלקוח צריך לקבל ייעוץ מקצועי, שליטה בהחלטות ותוצר אמין. מספר אג׳נטים אינו מדד להצלחה.

אי אפשר להבטיח אפס טעויות במערכת AI. הדרישה היא מניעה ככל האפשר, זיהוי שיטתי, התאוששות מבוקרת והימנעות מהצגת הצלחה כשהתוצאה אינה מוכחת.

## 1. פרטי עבודה מחייבים ומניעת התנגשויות

| רכיב | יעד מחייב |
|---|---|
| מאגר פרטי | `Shayfly/desktop-tutorial` |
| ענף בסיס פעיל | `milestone/pre-staging-2026-10-05` |
| main | ישן; לא בסיס העבודה ולא יעד שילוב |
| צוות Vercel | `shayflys-projects` |
| פרויקט הפלטפורמה | `148aiv28` |
| פרויקט ישן | `148ai` — להתעלם, לא לשנות ולא למחוק |
| סביבת העבודה | https://148aiv28-git-milestone-pre-staging-2026-10-05-shayflys-projects.vercel.app |

קרא קודם את `STATUS.md`, `docs/AGENT_SKILL_STATUS.md`, `docs/AGENT_OS_SKILLS_RUNTIME_SPEC_HE.md` ואת הוראות המאגר החלות. מסמכי סטטוס הם טענות שיש להשוות למימוש ולראיות.

כללים:

- ChatGPT מתחיל בקריאה בלבד. שינוי שלו נעשה בענף `chatgpt/...` ו־PR אל הענף הפעיל, ללא דחיפה ישירה.
- Claude מרכז את השילוב. גם עבודה חדשה שלו תתבצע בענף משימה מבודד; שילוב לענף הפעיל רק לאחר בדיקות ובחלון בטוח.
- לפני שילוב ודא שאין בנייה או שינוי פעילים. דחיפה לענף הפעיל עלולה לפרוס ולהחליף worker ולעצור עבודה.
- בדוק גם workflows של ענף משימה: ענף נפרד אינו בידוד אם push אליו מפעיל פריסה ל־worker המשותף. אין להריץ עליו פריסת worker משותפת ללא תיאום.
- רשום בעלות על רכיבים, SHA של בסיס, HEAD בזמן הבדיקה ומצב הרצות פעילות. אל תדרוס קוד שהתחדש מאז תחילת העבודה.
- שמור בדיקות וראיות של ה־merge candidate; לאחר שילוב אמת את פריסת הווב ואת גרסת ה־worker התואמת.
- אין force push, מחיקת ענפים/פרויקטים, הדפסת סודות או בקשת מפתחות בצ׳אט. השתמש בהפניות לסודות הקיימים ובהרשאות מוגבלות.
- פרויקט הפלטפורמה `148aiv28` אינו אוטומטית יעד הפרסום של כל מוצר לקוח. מוצר שנוצר דורש release ויעד נפרדים; אסור שידרוס את 148AI.
- הרשאה חסרה מסומנת BLOCKED. המשך עבודה מקומית שאינה תלויה בה. אל תחליף צוות, חשבון או סביבת יעד בשקט.

## 2. בסיס הראיות שנקרא בעת הכנת המסמך

נקודת צילום הענף: `b0a0cfac46b4ad632769c9feb5d68cd9ca9d9631`. זו נקודת קריאת מסמכים, לא הוראה לחזור לקומיט ולא אישור שהקוד בו תקין. בדוק HEAD מחדש לפני ביצוע.

שלושת הקבצים נשלפו מהענף הנכון. עדכוני STATUS והרישום מציינים:

- מסלול אמיתי אחד: התחברות, פרויקט, תכנון/תמחור, worker, Gemini, קוד, sandbox, תיקון, R2, גרסה, Preview, שינוי וייצוא ZIP. זו ראיה מתועדת, לא הרצה עצמאית חדשה של ChatGPT.
- הרישום מציג 49 תפקידי אג׳נטים: 15 VERIFIED, שניים CONNECTED ו־32 DEFINED; שש חבילות הנחיות ווב מסומנות VERIFIED.
- באותו רישום מפורטים פערים: אין בירור בשיחה; נוצרות דרישות התחברות נגד בקשה; זיהוי משחק לפי מילות מפתח; QA בעיקר קורא קוד; עיצוב נבדק באמצעות heuristic; נתוני מוצר ב־/tmp; אין גרף משימות, cancel או resume מלא; Release Agent אינו ממומש.
- 49 Skills ישנים מסומנים PARTIAL ללא מסלול ביצוע מאומת: תשעה integration, 32 media ושמונה target.
- חלק מהתפקידים משותפים באותה מחלקת קוד. מותר להשתמש במימוש משותף, אך אין להסיק שהאחריות המלאה של כל תפקיד הוכחה.

עלות ומצב ספקים במסמכים הם נתונים היסטוריים. אמת יתרה והרשאות לפני קריאה חיצונית. אין להסיק זמינות מקריאת משתנה סביבה או ממבחן ישן.

## 3. יעד המסירה והגדרה של מוצר ראוי לשותף

יעד נוכחי: `PARTNER_REVIEW_CANDIDATE`. אין להציגו כמוצר מוכן להשקה ציבורית או כתמיכה מוכחת בכל משפחות המוצרים.

אדם שאינו מכיר את הקוד צריך להיות מסוגל לתאר צורך בעברית, לקבל שאלות מקצועיות, לבחור או להאציל החלטות, לאשר מפרט ותקציב, לקבל מוצר, להשתמש בו, לבקש שינוי, לבדוק אותו ולייצא אותו.

תנאי הליבה: שיחה + עיצוב + אישור שרת + בנייה אמיתית + נתונים מתאימים + בדיקת דפדפן + שינוי + גרסאות + ייצוא + חשבון עלויות אמין. יעד פרסום ציבורי של מוצר נבדק בנפרד; אם חסום, ההדגמה מסומנת READY_FOR_PRIVATE_REVIEW עם חסם הפרסום, ולא כ״מסלול פרסום מלא״.

אין להרחיב עכשיו הכול במקביל. בנה תשתית משותפת ורישום מלא, הוכח מסלול ווב, ואז הוסף מסלולי מוצר עצמאיים לפי שערי קבלה. אין להוריד תחומים מהחזון; אין להציגם כפעילים לפני הוכחה.

## 4. מחלקת מוצר ואפיון — שיחה של איש מקצוע

זרימה: בקשה → שיחה מקצועית → המלצות/דוגמאות → סיכום הבנה → תמחור ותקרה → אישור → ביצוע → שימוש ובדיקות → שינוי → מסירה.

שאל גם שאלות פשוטות: צבעים, פונט, סגנון, לוגו, קהל, תוכן ורפרנסים. אל תיישם את ההנחיה הישנה ״לשאול רק על חוסרים קריטיים״. גם החלטה שאינה קריטית יכולה להיות חשובה ללקוח.

כל שאלה קשורה לשדה במפרט וכוללת רלוונטיות, אפשרויות, ערך מומלץ אם יש, ואפשרות ״אין לי העדפה — בחרו עבורי״ כשאפשר להאציל. שאלה על הרשאה או שימוש במידע אינה נפתרת באמצעות המצאת הסכמה.

הצע מסלול מודרך ומסלול שבו המערכת ממליצה ובוחרת. אלה שני מצבי אותו אפיון; שניהם מסתיימים בסיכום ובאישור.

שאל קבוצות קטנות; העמק לפי התשובות; אל תשאל שוב מידע ידוע; אל תקבע מספר שאלות קשיח לכל פרויקט. אפשר חזרה, דילוג על העדפה, שינוי תשובה, עצירה וחידוש. שינוי תשובה מעדכן החלטות תלויות.

| תחום | אפיון מקצועי נדרש |
|---|---|
| אתר | מטרה, קהל, פעולה מרכזית, עמודים, תוכן, מיתוג, SEO בסיסי, שפות, טפסים וחיבורים |
| מערכת עסקית | תהליך נוכחי, תפקידים, נתונים, הרשאות, דוחות, יבוא/יצוא, עומס צפוי |
| משחק | ז׳אנר, גיל, פלטפורמה, שליטה, לולאת משחק, קושי, שלבים, שמירה, רשת וסגנון |
| תמונה | שימוש, יחס וגודל, סגנון, נושא, קומפוזיציה, צבע, טקסט, references וזכויות ידועות |
| וידאו/אודיו | קהל, מסר, משך, פורמט, תסריט, קול, מוזיקה, כתוביות, ערוץ פרסום ומגבלות |
| אוטומציה | trigger, תדירות/אזור זמן, תנאים, שירותים, חשבונות, כשל, כפילות ואישור פעולות |
| סוכן AI ללקוח | מטרות, ידע, כלים, קול המותג, זיכרון, הרשאות, הסלמה ומדדי הצלחה |
| מובייל/Desktop | מערכות יעד, offline, התקנה, התראות, מכשירים ודרישות הפצה |

נושאים לדוגמה: ״בלי התחברות״ יחד עם נתוני לקוחות מחייב הבחנה בין כלי פנימי לאתר ציבורי; ״משחקי כדורגל״ יכול להיות ניהול תוצאות ולא משחק מחשב; שנת 2356 נדחית לפי כלל עסקי של טווח הזמנה, לא לפי מספר קסום גורף לכל מוצר.

לכל פרויקט שמור `ProjectBrief` גרסאי: דרישה, מקור, תשובה, הנחה/בחירה מואצלת, ביטחון, תלויות, קריטריון קבלה והחלטת המשתמש. מקור יכול להיות הודעה, מסמך או בחירה; תשובת מודל אינה הופכת לעובדה מאושרת.

## 5. אישור ובקרת היקף

הצג את התוצר המתוכנן בשפה פשוטה: מטרה, משתמשים, מסכים, פעולות, עיצוב, נתונים, חיבורים, מה כלול, מה אינו כלול, הנחות, חסמים, קריטריוני קבלה, אומדן ותקרת הוצאה.

פעולות: ״עדכן את הבקשה״ ו־״אשר והתחל בנייה״. אישור נאכף בשרת, קשור למשתמש, project, brief revision, plan fingerprint, budget revision ותקופת תוקף מוגדרת. בקשה ישירה ל־API אינה עוקפת אותו.

רענון אינו מאבד אישור; לחיצה כפולה אינה יוצרת שתי בניות; שינוי משמעותי מבטל אישור ישן. בדוק race שבו brief משתנה בין אישור לשמירת job.

בזמן הביצוע: החלטה רגילה בתוך ההיקף מאושרת מראש; שינוי תפקוד, עלות מעל התקרה, פרסום, שירות חיצוני חדש או שינוי משמעותי בעיצוב מחייבים בירור לפי ההרשאה. אין לייצר הפתעות.

שיחה יכולה לצרוך מודל לפני בנייה; מדוד והגבל אותה בנפרד, והסבר ללקוח את מודל הקרדיטים. אין חיוב עסקי חדש ללא מדיניות מאושרת.

## 6. מקורות אמת ואימות לפי יכולת

Master Agents Registry ו־Master Skills Registry יהיו versioned וניתנים להפעלה. התקן אינו רשימת שמות.

Agent fields: key/version, role, responsibilities, triggers, input/output schemas, allowed skills/tools, forbidden actions, permissions, budget/provider/memory/retry/escalation policies, success criteria, tests, observability, implementation binding, status ומידע אימות.

Skill fields: key/version, purpose, kind, product families, schemas, dependencies, targets, tools/providers, permissions, side effects, implementation, cost/timeout/retry/idempotency/compensation policies, constraints, tests, metrics, evidence וגרסת אימות.

הבחן בין Skill מסוג INSTRUCTION, EXECUTABLE, VALIDATOR ו־WORKFLOW. חבילת הנחיות היא יכולת לגיטימית, אך הוכחת הזרקה לפרומפט אינה הוכחה שהתוצר עמד בה.

שמור ממדים נפרדים: implementation, configuration, verification, blocked reason. הצלחה בדוגמה מסוימת נרשמת כ־verified scope מוגדר. אין צורך לשבור enums קיימים: מגרציה/מיפוי תאימות מפורשים.

Evidence: requirement id, test id, artifact, source commit, worker image/version, environment, product version, skill/agent/provider versions, result, time, scope ו־expiry/staleness rule. ריצה בודדת יכולה לתמוך בכמה יכולות רק אם יש בה assertions מתאימים לכל אחת.

ה־Auditor מוודא import/binding, חוזה, זמינות, dependency closure, הרשאות, ראיות ורעננות. שינוי ברכיב גורר אימות מחדש של היכולות התלויות בו; ״יש run id״ אינו תנאי מספיק.

תקן את 49 הסקילים הישנים ואת התפקידים שמסומנים VERIFIED באופן רחב מדי. אל תבטל הוכחות תקפות; צמצם את היקפן במדויק.

## 7. קטלוג האג׳נטים הבסיסי — 49 תפקידים

לכל תפקיד בטבלה יש להגדיר חוזה מלא מהסעיף הקודם. אלה תפקידים לוגיים, לא חובה ל־49 workers או מודלים. המימוש יכול להיות דטרמיניסטי, מבוסס מודל או משולב. תפקיד קיים ישמש מחדש.

| משפחה | אג׳נט | אחריות ותוצר | Skills מרכזיים | הוכחת קבלה |
|---|---|---|---|---|
| ניהול | Request Interpreter | פירוש הבקשה ללא דרישות מומצאות | intent, constraints, ambiguity | ניסוח חדש ודו־משמעות מסווגים נכון |
| ניהול | Product Analyst | brief, תהליכים וקריטריונים | interview, stories, acceptance | כל דרישה מרכזית קשורה לבדיקה |
| ניהול | Capability Resolver | יכולות וחסמים | registry, closure, readiness | חסר אמיתי חוסם ללא fake fallback |
| ניהול | Solution Architect | תכנון ישים בתקציב | architecture, API, data design | תלויות ומסלול הרצה תקפים |
| ניהול | Project Orchestrator | גרף עבודה ומצב | plan graph, dispatch, cancel/resume | אין כפילות; התאוששות מוכחת |
| ניהול | Cost Controller | תקציב וספר עלויות | quote/reserve/meter/settle | תחרות והוצאה לא ידועה מטופלות |
| תוכנה | UX Designer | מסכים וזרימות מלאות | navigation, forms, states | מסלול מרכזי ומקרי כשל שימושיים |
| תוכנה | Frontend Developer | ממשק מחובר | components, RTL, API binding | בדיקות דפדפן ומובייל |
| תוכנה | Backend Developer | API ולוגיקה | endpoints, validation, service | הצלחה ומקרי כשל ב־API |
| תוכנה | Data Engineer | נתונים ומיגרציות | schema, constraints, indexes | restart, concurrency, integrity |
| תוכנה | Identity & Access Engineer | זהות והרשאות | sessions, roles, tenant checks | ניסיון חוצה משתמש נדחה |
| תוכנה | Integration Engineer | adapters וחיבורים | auth, callbacks, retries | פעולה אמיתית וחוסר הרשאה |
| תוכנה | Repository Maintainer | קוד וגרסאות | inspect, patch, snapshot, export | diff ברור ושחזור תקין |
| איכות | QA Verifier | בדיקה מול מפרט | test plan, API/browser, evidence | אינו מקבל הכרזת מפתח כראיה |
| איכות | Security Reviewer | בדיקת גבולות וסודות | negative tests, hostile scan | ממצא מהותי חוסם שחרור |
| איכות | Repair Agent | תיקון ממוקד | reproduce, diagnose, patch | הכשל משוחזר ואז נפתר |
| איכות | Preview Operator | גרסה ניתנת לשימוש | runtime, readiness, adapter | content + behavior + version |
| איכות | Release Agent | מסירה ופרסום | release, deploy, verify/rollback | יעד ותוצר מאומתים |
| איכות | Operations Agent | ניטור והתאוששות | health, incident, recovery | כשל מזוהה ומתועד |
| נכסים | Asset Planner | מפרט ורשימת נכסים | inventory, formats, styles | לכל נכס שימוש ומידות |
| נכסים | Visual Creator | יצירה ועריכת תמונות | generate/edit/cutout | קובץ אמיתי ונבדק |
| נכסים | Consistency Director | עקביות מותג ודמויות | bibles, references, comparison | השוואה חזותית מתועדת |
| נכסים | Asset QA | איכות ושימושיות | alpha, resolution, visual check | מתאים ליעד ולמפרט |
| נכסים | Asset Librarian | מקור ואחסון | metadata, provenance, dedupe | נכס ניתן לאיתור ושחזור |
| מדיה | Media Producer | תוכנית הפקה | brief, shots, timing/cost | יש תוכנית ישימה |
| מדיה | Scriptwriter | תסריט | outline, dialogue, narration | אורך ומסר תואמים |
| מדיה | Storyboard Director | שוטים ורפרנסים | storyboard, motion, camera | הוראות לכל שוט |
| מדיה | Video Creator | קטעים | text/image-to-video, edits | קטע נוצר ונפתח |
| מדיה | Voice & Audio Producer | קול ומוזיקה | TTS/STT, music, SFX | אודיו תקין ומקור מתועד |
| מדיה | Timeline Editor | הרכבה | composition, mix, captions | ניגון וסנכרון |
| מדיה | Media QA | בדיקת הפקה | continuity, clipping, caption checks | פגמים מתועדים ונפתרים |
| מדיה | Publishing Operator | יצוא וערוצים | presets, metadata, upload/schedule | פרסום מורשה בלבד |
| משחקים | Game Designer | לולאה וחוקים | rules, progression, win/lose | משחק מוגדר וניתן לבדיקה |
| משחקים | Game Architect | מנוע וסצנות | engine, runtime, architecture | מנוע נתמך באמת |
| משחקים | Gameplay Developer | התנהגות | controls, physics, interactions | ניתן לשחק בלולאה המרכזית |
| משחקים | Level Designer | שלבים | layouts, encounters, difficulty | שלבים ניתנים להשלמה |
| משחקים | Game Asset Coordinator | שילוב נכסים | models/sprites/audio, optimize | נכסים נטענים בביצועים מתאימים |
| משחקים | Save & Progression Engineer | שמירות | save/load/checkpoint | מצב משוחזר לאחר סגירה |
| משחקים | Playtest Agent | משחק בפועל | inputs, play checks, performance | התחלה, משחק וסיום |
| משחקים | Multiplayer Engineer | רשת | sync, authority, reconnect | שני לקוחות נפרדים וסנכרון |
| אוטומציה | Automation Designer | טריגר ופעולות | workflow, schemas, failures | רצף מפורש וגבולות |
| אוטומציה | Connector Operator | פעולות שירות | invocation, webhooks, pagination | חשבון נכון וללא כפילות |
| אוטומציה | Scheduler Operator | תזמון | timezone, schedule, dispatch | מועד ואזור זמן נכונים |
| אוטומציה | Automation QA | בדיקת זרימה | replay, duplicate, timeout | שגיאות וכפילויות מכוסות |
| אוטומציה | Agent App Builder | סוכן ללקוח | tools, instructions, memory/evals | משימה והימנעות מפעולה אסורה |
| פלטפורמה | Skill Builder | Skill מועמד | reuse, contract, implement | ניתן לבדיקה מבודדת |
| פלטפורמה | Skill Evaluator | אימות Skill | functional/negative/permission | ראיות עצמאיות מוגדרות |
| פלטפורמה | Registry Auditor | אמת ברישום | bindings, closure, freshness | אין אימות ללא scope וראיה |
| פלטפורמה | Provider Evaluator | התאמת ספק | benchmarks, cost/quality | החלטת ניתוב ממדדים |

## 8. תפקידים נוספים להשלמת החברה — 12 תפקידים

הוסף כתפקידים מפורשים או אחריות ממופה אצל תפקיד קיים. אל תיצור כפילות רק כדי להגיע למספר. הקטלוג המתוכנן כולל 61 תחומי אחריות לפני איחודים; ספירת המימושים חייבת להיגזר מהרישום.

| תפקיד | מה נדרש ממנו | Skills ותנאי קבלה |
|---|---|---|
| Discovery Lead | אפיון עמוק ולא טופס כללי | question routing, delegated preferences, contradiction resolution; בדיקת שיחות לפי משפחה |
| Requirements Traceability Auditor | מניעת השמטות | brief→task→artifact→test; כל דרישה מאושרת מכוסה או חסומה |
| Brand & Design Director | שפה חזותית מקצועית | palettes, type, references, design tokens; בחירות מאושרות ושימוש עקבי |
| Accessibility & Localization Reviewer | שימושיות ושפות | keyboard/focus, labels, RTL/LTR, locale; בדיקות מחשב ומובייל |
| Integration & Secret Steward | בעלות וחיבורים מסחריים | scopes, vault refs, revoke, managed/customer/BYOK; אין סוד בתוצר |
| Reliability & Recovery Engineer | תקלה בלי איבוד עבודה | checkpoints, leases, compensation, restore; crash recovery מוכח |
| Performance & Resource Engineer | זמן ומשאבים | profiling, bundle/runtime limits, resource cleanup; מדדים וגבולות |
| Release & Change Coordinator | מניעת שינוי לא מתואם | branch ownership, CI/worker gate, safe rollout; אין החלפה באמצע בנייה |
| Privacy & IP Steward | מקור, מידע ומדיניות | provenance, consent, retention, complaint routing; אין רישיון מומצא |
| Customer Success & Handover Agent | מסירה שהלקוח מבין | onboarding, known limits, usage guide; אדם חדש מצליח להשתמש |
| Product Economics Analyst | יתרון עסקי ורווח תרומה | per-stage cost, scenario analysis, gross contribution; הנחות מסומנות |
| Partner Readiness Reviewer | בחינה עצמאית של המוצר | acceptance matrix, cold demo, evidence review; חסם אינו מוסתר |

לא כל אלה דורשים LLM. מבקר עקיבות, אכיפת הרשאות וחסימת פריסה צריכים רכיבים דטרמיניסטיים.

## 9. קטלוג Skills מפורט ותלויות

שמות הם הצעה למיפוי; העדף aliases וקוד קיים. כל פריט דורש implementation binding או סטטוס חסר מפורש. אין לבצע פעולות רק משום שהן הופיעו ברשימה.

| תחום | Skills נדרשים |
|---|---|
| אפיון | `intent.parse`, `domain.classify`, `requirements.extract`, `questions.select`, `answers.merge`, `ambiguity.resolve`, `contradiction.detect`, `preferences.delegate`, `references.ingest`, `brief.summarize`, `acceptance.define` |
| אישור | `brief.revise`, `approval.bind`, `approval.validate`, `approval.invalidate`, `scope.diff`, `change.classify` |
| עיצוב | `brand.profile`, `palette.propose`, `typography.select`, `design.tokens`, `screen.plan`, `states.define`, `responsive.verify`, `visual.compare`, `accessibility.check`, `locale.verify` |
| תכנון | `capabilities.resolve`, `dependencies.close`, `architecture.plan`, `api.contract`, `data.schema`, `tasks.graph`, `risk.classify` |
| קוד | `repository.inspect`, `context.select`, `code.generate`, `code.patch`, `frontend.build`, `backend.build`, `dependencies.lock`, `diff.review` |
| נתונים | `migration.create`, `migration.verify`, `data.constraints`, `data.persistence.verify`, `data.backup`, `data.restore`, `tenant.isolation.verify` |
| זהות וחיבורים | `auth.configure`, `authorization.verify`, `secrets.resolve`, `integration.configure`, `integration.probe`, `webhook.verify`, `connection.revoke`, `binding.validate` |
| ביצוע | `sandbox.prepare`, `app.start`, `runtime.readiness`, `task.checkpoint`, `task.resume`, `task.cancel`, `operation.deduplicate`, `effects.compensate`, `resources.cleanup` |
| איכות | `tests.plan`, `tests.run`, `api.behavior.verify`, `browser.flow.verify`, `visual.inspect`, `security.negative_test`, `failure.reproduce`, `repair.patch`, `regression.verify` |
| מסירה | `artifact.commit`, `version.restore`, `preview.verify`, `project.export`, `release.prepare`, `deployment.publish`, `deployment.verify`, `deployment.rollback`, `handover.generate` |
| עלויות | `cost.quote`, `budget.reserve`, `usage.record`, `cost.estimate`, `cost.reconcile`, `budget.settle`, `margin.calculate`, `budget.guard` |
| נכסים | `assets.plan`, `image.generate`, `image.edit`, `image.cutout`, `asset.inspect`, `consistency.verify`, `asset.store`, `provenance.record` |
| מדיה | `script.write`, `storyboard.create`, `shots.plan`, `video.generate`, `voice.generate`, `speech.transcribe`, `music.generate`, `captions.align`, `timeline.compose`, `media.render`, `media.verify`, `media.export` |
| משחקים | `game.rules`, `engine.select`, `scene.build`, `controls.bind`, `physics.configure`, `levels.generate`, `save.load`, `game.playtest`, `multiplayer.sync`, `game.performance` |
| אוטומציה וסוכנים | `trigger.configure`, `workflow.execute`, `schedule.configure`, `connector.invoke`, `automation.replay`, `agent.configure`, `memory.configure`, `agent.evaluate` |
| הרחבה | `skill.propose`, `skill.implement`, `skill.evaluate`, `registry.audit`, `verification.refresh`, `provider.benchmark`, `readiness.audit` |

דוגמת שרשרת מחייבת: `deployment.publish` דורש תוצר וגרסה בלתי משתנים, יעד והרשאה מאומתים, אישור שחרור, תקציב ותוכנית בדיקת deployment. `code.generate` דורש brief מאושר, יכולות, ספק ותקציב. `skill.implement` אינו מקנה לעצמו הרשאות או מקדם אוטומטית לייצור.

## 10. Runtime משותף וגרף משימות

השתמש ב־RQ, Postgres, אחסון ו־workspace הקיימים כשמתאימים. אל תחליף תשתיות ללא בעיה מוכחת.

לכל משימה: task/project/tenant ids, parent/dependencies, expected project version, inputs/outputs, agent/skill versions, policy snapshot, budget refs, idempotency key, attempts, lease/heartbeat, deadlines, trace, errors ו־checkpoint.

מעברי מצב מפורשים: PENDING, RUNNING, WAITING_FOR_USER, WAITING_FOR_DEPENDENCY, RETRYING, SUCCEEDED, FAILED, CANCELLED, BLOCKED. אם קיימים enums אחרים, בצע מיפוי ומגרציה תואמים.

תזמן רק תלויות שהושלמו. מקביליות רק בין פעולות שאינן דורסות זו את זו ושיש להן reservation נפרד בתוך התקרה. כתיבה לאותה גרסה מחייבת compare-and-set או מנגנון שקול.

צריכה ממסר/תור יותר מפעם אחת אינה אמורה לבצע שוב פעולה לא הפיכה. timeout אינו הוכחת כשל אצל ספק; סמן UNKNOWN_OUTCOME ובדוק מזהה פעולה לפני retry.

ביטול אינו הבטחה להחזר על שימוש שכבר נצרך. עצור צעדים חדשים, טפל בפעולות פעילות, נקה משאבים ושמור ראיות. כשל בתיקון לא מוחק גרסה תקינה.

## 11. עיצוב הפלטפורמה והמוצרים — בדיקה ברמת המיקרו

148AI צריכה Design System משותף: צבע, טיפוגרפיה, מרווחים, רכיבים, focus, הודעות וסטטוסים. העיצוב של מוצרי הלקוחות נקבע לפי ה־brief ולא חייב להעתיק את הפלטפורמה.

| רכיב | התנהגות חובה |
|---|---|
| כפתור | פעולה ברורה, focus, disabled reason, loading, מניעת כפילות |
| טופס | labels, required, אימות שרת, שגיאה ליד שדה, שמירת ערכים |
| טבלה/רשימה | ריק, טעינה, sort/filter גלויים, paging כשצריך, refresh |
| פעולה הרסנית | משמעות ברורה, אישור מתאים/undo כשאפשר, ללא תוצאה שקרית |
| תאריך/שעה | format מקומי, timezone, טווח עסקי, עבר/עתיד והבדלי ימים |
| שיחה | הודעה נשמרת, retry ברור, תור הודעות, שאלה מול תשובה מובחנות |
| קבצים | פורמט/גודל, כשל upload, duplicate, progress, גישה מוגנת |
| Preview | גרסה, readiness, reload, הודעת כשל, מבודד מהפלטפורמה |
| עלות | אומדן מול שימוש מול סכום שמור; אין ״חויב״ לאומדן |

כל מסך מרכזי נבדק במצב ריק, loading, success, invalid input, server failure, no permission, offline, timeout ונתונים חלקיים. אין טקסט חתוך, מפתחות תרגום גולמיים או איבוד נתונים בגלל שגיאת טופס.

עברית ואנגלית בפלטפורמה נבדקות בנפרד משפת המוצר. RTL/LTR, טקסט מעורב, ניווט מקלדת, label/focus, ניגודיות ושימוש שאינו תלוי בצבע נבדקים. אין להצהיר על הסמכת נגישות בלי תהליך מתאים.

בקש רפרנסים והצג פלטות/דוגמאות כשאפשר. פונט נבדק לתמיכה בשפה ורישיון ידוע. ביקורת עיצוב משתמשת בצילומי מסך לצד בדיקות רכיבים; heuristic CSS לבדו אינו אישור עיצוב.

## 12. איכות הקוד והתנהגות המוצר

יצירה מותאמת אמיתית של קוד וקבצים, לא Fake Build. ניתן להשתמש ברכיבים ותבניות, עם תיעוד. אין להסתפק בדף ברירת מחדל או health שמחזיר 200.

דרישות בסיס גם כשהמשתמש לא ביקש: אימות קלט, שגיאות ברורות, שלמות נתונים, מניעת כפילויות, גבולות גישה לפי ה־brief ותהליכי מסך מלאים.

ערכי טקסט בעברית, apostrophes ו־HTML נבדקים ל־escaping נכון. הימנע מהכנסת טקסט בלתי מהימן ל־innerHTML ללא הגנה מתאימה. אל תציג ״סיום״ כפעולה זמינה לפריט שכבר הושלם כשאין לכך משמעות.

Repair עובד מול כשל משוחזר ומעדיף patch ממוקד. לא מריצים בנייה יקרה מחדש אם אפשר לבדוק תיקון קיים. תקרת retries נמדדת בזמן, ניסיונות ועלות; הגעתה יוצרת חסם גלוי ולא לולאה אינסופית.

## 13. נתונים: הפלטפורמה לעומת התוצר

Postgres של 148AI ושמירת גרסאות ב־R2 אינם מוכיחים שהנתונים באפליקציה שנוצרה נשמרים. בדוק כל שכבה בנפרד.

פרופיל SELF_CONTAINED יכול להשתמש ב־SQLite כאשר יש אחסון עמיד מתאים ונבדק. /tmp אינו אחסון עמיד; ״עובד עד עצירת Preview״ חייב להיות מסומן כתוצר זמני ולא מוצר עסקי מתמשך.

למוצר עסקי מתמשך: backing store מתאים, constraints, transactions, backup/restore, schema version, בעלות והפרדת גישה. בדוק restart של השירות/Preview ושינוי גרסת האפליקציה בלי איבוד נתונים.

תורים כפולים נאכפים בשרת/מסד גם בשתי בקשות מקבילות; חסימת כפתור בלבד אינה מספיקה. rollback של קוד אינו בהכרח rollback של נתונים; אל תשחזר schema באופן הרסני ללא תוכנית והרשאה.

## 14. זהות, סודות וחיבורים

הפרד משתמש ב־148AI ממשתמש במוצר שנוצר. זהות, session ו־tenant checks נאכפים בשרת. בדוק IDOR, ביטול session וגישה לקבצים של פרויקט אחר.

Secret references נשמרים ב־Vault/מנגנון הקיים. אין ערכי סוד ב־prompt, לוגים, screenshots, exports או עמוד status. נתוני חיבור מוגנים גם לאחר ביטול.

לכל integration: owner, provider account/team, scope, binding model, health, last verification, failure reason, cost policy ופעולה לביטול. אל תציג CONNECTED כאילו פעולה עסקית אומתה.

חיבור WhatsApp/מייל/תשלום אינו אישור לבצע פעולה בשם הלקוח. הפעולות כפופות להיקף הרשאה ואישור מתאים. בדוק callbacks, כפילות webhooks, timeout, retries ו־rate limits.

## 15. כספים: מנגנון אמין לפני עסק מסחרי

התקרה המאושרת לבדיקות היא 10 דולר בסך הכול, לכל הספקים יחד. אין לאפס, להגדיל, לפתוח תקרה חדשה לכל שלב או להוציא הוצאות תשתית חדשות בשקט.

אמת את היתרה לפני בדיקה. המסמך אינו מאשר מחיר בנייה קבוע או 61 אג׳נטים פעילים בכל בקשה.

הפרד אומדן, reservation, metered estimate, supplier-confirmed cost, unknown exposure, הטבה וצריכה חינמית מאומתת. ספירת טוקנים אינה חשבונית; נתון חסר אינו אפס; reservation אינו הוצאה.

כל חשיפה כספית נספרת פעם אחת: settled + active reservations + conservative cover for unresolved costs, לפי מודל שהוכח שלא סופר כפול. reservation אטומי מונע oversubscription בהרצות מקבילות. מגבלת ספק היא שכבת הגנה נוספת, לא תחליף.

שמור היסטוריה; תיקון הוא התאמה מתועדת עם מקור. אל תסתיר עלות באמצעות סינון תאריכים ללא הוכחת free tier/חיוב.

שייך שימוש לאפיון, תכנון, יצירה, תיקון, נכסים, בדיקה, compute/storage/egress לפי זמינות הנתונים. עלות cloud שאינה נמדדת עדיין תסומן לא ידועה/אומדן ולא 0.

Provider Price Catalog ו־Capability Cost Catalog גרסאיים. Router בוחר לפי איכות מתאימה, זמינות, הרשאות ועלות; מסלול חינם נבחר רק אם עומד באיכות. context ממוקד, caching ו־patches מקטינים שימוש.

הצג רווח תרומה רק כשיש הכנסה ועלות מוגדרות: הכנסה נטו פחות עלויות משתנות ידועות/מוערכות, עם פירוט. אל תמציא מחירי מנוי, אחוז רווח או מספר משתמשים. שימוש חינמי אינו בסיס יחיד לתמחור עסקי.

## 16. אבטחה ומדיניות

קוד שנוצר מורץ בבידוד מתאים: הרשאות קבצים/רשת, cpu/memory/time, secrets, cleanup. בדוק את מנגנון האכיפה, לא רק את קובץ התצורה.

תוכן בקבצים, אתר חיצוני או בקשת משתמש אינו רשאי לשנות מדיניות מערכת, להעניק כלים או להרחיב תקרה. Prompt injection נבדק דרך כלים והרשאות בפועל.

בבדיקות של Preview ציבורי השתמש בנתונים סינתטיים. Private Preview דורש אכיפת גישה; כתובת שקשה לנחש אינה בהכרח הרשאת גישה.

מדיניות IP: תיעוד מקור, רישיון ידוע, הסכמות גרסאיות, שימוש אישי/מסחרי, חסימה/דיווח/תלונה לפי המדיניות. אין להבטיח חוקיות, המצאת רישיון או לנסח אישור משפטי אוטומטי.

## 17. QA עצמאי ומדדים

QA נפרד בהחלטות ובראיות. אפשר להשתמש באותו ספק מודל בהרצה נפרדת; ספק אחר אינו תנאי לעצמאות ואינו מבטיח אותה. אין צורך להוסיף קרדיט לספק אחר רק לצורך הטייטל ״בודק עצמאי״.

מטריצת עקיבות: requirement → component/task → verification → evidence → status. כל דרישה מרכזית PASS או חסם מפורש. בדיקת מודל אינה מחליפה API, browser או visual inspection.

בדוק במיוחד: no-login fidelity, locale/date rules, visible filter, inline errors, parallel uniqueness, cross-tenant denial, wrong version, export roundtrip, stale approval, retry billing, resume/cancel ו־restart persistence.

קריטריון שנגזר מהמפרט לא יעבור שינוי אוטומטי על ידי Repair כדי ״להעביר בדיקות״. שינויים בבדיקת קבלה דורשים הסבר וגרסה; תוצר ובודק אינם מאשרים את עצמם.

ציון איכות כמו 86 הוא מדד עזר עם rubric וגרסה. הוא אינו עוקף blocker. מדוד זמן למסירה, completion rate בתרחישים, repair rounds, עלות, דרישות שכוסו ורגרסיות. אל תסיק סטטיסטיקת אמינות רחבה משלוש הדגמות.

## 18. אמינות ותפעול

לוגים מובנים ו־trace לכל שלב; קשר run/job/build/version/deployment ו־provider operation ids. לכל timeout יש סיבה ושגיאה קריאה, ללא סודות.

Health ל־control plane, queue, worker, sandbox, storage, preview ויכולת לבצע מסלול. readiness אינו רק דף בית.

Runbooks: worker stopped, provider unavailable, stuck job, preview crashed, artifact missing, unknown cost, migration failure, rollback, secret revoked. בדיקת restore אמיתית עם נתוני בדיקה.

אין deploy שמחליף worker באמצע עבודה: drain/lease/checkpoint או חלון ללא jobs, עם deadline ודרך rollback. שמור התאמה בין control plane ל־worker; freeze של Vercel בלבד אינו הקפאת מוצר אם worker מתעדכן.

## 19. הרחבות נכסים, מדיה, משחקים ואוטומציות

הקוד והחוזים נבנים על Runtime משותף; כל משפחה זוכה ל־Preview Adapter ול־Acceptance Runner מתאימים.

- נכסים: קובץ אמיתי, אחסון, metadata, איכות, מקור, עקביות והטמעה. Replicate auth בלבד אינו יצירת תמונה.
- מדיה: תסריט→storyboard→shots→קול/וידאו→timeline→render→ניגון→QA. אין פרסום בערוץ בלי הרשאה. retries ממוקדים והוצאה לפי shot.
- משחק: מסלול קטן עם לולאה, controls, win/lose ושמירה. משחק קטן אינו הוכחה לעולם פתוח או multiplayer. שני לקוחות נפרדים נדרשים להוכחת רשת.
- אוטומציה: trigger→condition→action, אזור זמן, deduplication, retries ו־replay בטוח. בדיקת sandbox אינה שליחה לאדם אמיתי.
- סוכן ללקוח: ידע, כלים, הרשאות, זיכרון, handoff ומבחני התנהגות. יש להוכיח גם סירוב לפעולה אסורה.
- מובייל/Desktop: adapter של פלטפורמה, build/install/signing כשנדרש. אתר responsive אינו native app מאומת.

אלה חלקי תוכנית מחייבים, אך לא תנאי להפעלת כולם לפני מסלול הווב. הרחבה חדשה מקבלת משימה, budget gate וראיה עצמאית.

## 20. הרחבה עצמית בטוחה

Skill Builder קודם מחפש שימוש חוזר; יוצר מועמד עם חוזה, tests וסיבות. Skill Evaluator בודק אותו בסביבה מבודדת. Registry Auditor בודק תלויות, מדיניות וראיות.

המועמד אינו רשאי לערוך את הרשאותיו, סטטוס האימות שלו, תקרת התקציב, בדיקות הבטיחות או evidence באופן שמאשר את עצמו. rollback ו־deprecation מוגדרים. promotion מתבצע לפי שערי שחרור ולא לפי המלצת היוצר בלבד.

## 21. שלושה תרחישי Partner Review

א. אתר תורים בעברית: שיחה מבהירה כלי פנימי מול אתר ציבורי; צבע ופונט; תאריך/שעה; רשימה; ביטול; conflict; שמירה; שינוי; ZIP. בדיקת תאריך מעבר לחלון, טלפון חסר ושתי בקשות לאותה שעה.

ב. מערכת משימות בדרישות מפורטות: ללא התחברות אם זו הדרישה המאושרת; שפה ועיצוב מדויקים; מצבי ריק וסינון; הוספה/עריכה/השלמה; שינוי העדפה במהלך השיחה; אין דרישות מומצאות.

ג. בקשה בניסוח חדש שלא שימש לפיתוח: קהל אחר ונתונים אחרים בתוך יכולות הווב הקיימות, ואז שינוי מהותי אחד ושינוי עיצוב. המשתמש החדש בודק בלי להכיר את הקוד.

לפחות תרחיש אחד כולל refresh/return, כשל מבוקר, recovery ושחזור גרסה. שינוי version אינו רשאי להעלים נתונים. כל תרחיש משתמש בקומיט וב־worker מתועדים.

השתמש בתוצרים אמיתיים; סמן דוגמאות seed ככאלה. אין hard-coding שמזהה את ניסוח ההדגמה כדי לייצר הצלחה. Replay של evidence אינו ריצה חדשה.

## 22. שערי ביצוע וחבילות עבודה

| שער | עבודה | תנאי יציאה |
|---|---|---|
| G0 | מיפוי, בעלות, ענפים וטריגרי deploy | baseline, אין התנגשות, gaps מתועדים |
| G1 | registries, scope ורעננות ראיות | אין VERIFIED רחב מטעה או PARTIAL ללא מימוש |
| G2 | שיחת אפיון, העדפות, brief ואישור | שיחות ברורות/עמומות/מואצלות; approval server tests |
| G3 | design states ומרחב עבודה | screenshots, RTL/LTR, mobile, return/reload |
| G4 | Runtime, budgets ונתונים | concurrency/recovery, no double cost, persistence |
| G5 | קבלה בדפדפן ותיקון | תרחישי ווב והתנהגויות עסקיות עברו |
| G6 | מסירה ופרסום מורשה | export/restore, release readiness, יעד מאומת או חסם |
| G7 | גרסה קפואה וחבילת שותף | cold demo, הוכחות, עלות ומגבלות |
| G8+ | נכס תמונה, משחק, אוטומציה, Agent, מדיה ומובייל | לכל מסלול gate ובדיקות עצמאיים |

לכל work package: id, purpose, owner, base SHA, affected files, dependencies, design decision, acceptance ids, tests, evidence, budget, risk, rollback ו־status. פרק שינויי סכמות ו־Runtime למשימות קטנות. לא refactor רחב ללא צורך במסלול.

אל תסמן חסם חיצוני ככשל קוד ואל תסמן test skipped כ־PASS. כאשר שינוי יציב והבדיקות המתאימות עברו, המשך למסירה; אל תריץ שוב ושוב בדיקות זהות או builds יקרים ללא סיבה חדשה.

## 23. פרוטוקול מסירה ודיווח

סיכום כל שער: מה השתנה, מה הוכח, מה נכשל, חסמים, commit/PR, environment/worker, cost/unknowns והשלב הבא. אין ״הכול עובד״ ללא scope.

תוצרי המאגר לאחר שילוב מתואם: מסמך ראשי אחד עם version, תוכנית work packages, Registries, status אוטומטי, requirements/acceptance matrix, design tokens, test evidence, runbooks ו־release manifest. קבצים קיימים יעודכנו במקום לשכפל מקורות אמת.

חבילת שותף: קישור בדיקה יציב, חשבון והרשאות בטוחות, תסריט קצר, screenshots/video אמיתיים, תוצרים ו־ZIP, capabilities proven, limitations, architecture summary, עלויות מדודות וגרסת שחרור. לא מפרסמים credentials במסמך ציבורי.

Freeze כולל control plane, worker, policies, agents/skills, model catalog, price catalog ו־artifacts. branch alias משתנה אינו ראיה לגרסה קפואה; release manifest יצביע ליעדים מדויקים שאומתו.

## 24. Definition of Done

- קריטריוני הליבה אושרו ונבדקו; שיחה מקצועית ו־approval עובדים.
- המשתמש מקבל תוצר מתאים ומסוגל לבצע את התהליכים המרכזיים.
- יש שמירה מתאימה, הפרדת גישה, שינוי וגרסאות.
- אין כשל ידוע שמונע מסלול מרכזי, אובדן נתונים, חשיפת מידע, חריגת תקציב או דיווח הצלחה שקרי.
- שגיאות, refresh, כפילות וכשל מבוקר טופלו.
- עלויות ותקרות מוסברות; unknowns נראים.
- הראיות תואמות לגרסה שנמסרת; CI green אינו תחליף לבדיקה הפרוסה.
- אדם חדש עבר את ההדגמה, או שהבדיקה הזאת מסומנת ממתינה ולא מומצאת.
- פרסום חיצוני והרחבות חסומים מסומנים במדויק.
- יש runbook, restore בסיסי וחבילת מסירה לשותף.

סטטוס סופי: READY_FOR_PARTNER_REVIEW, READY_FOR_PRIVATE_REVIEW_WITH_NAMED_LIMITS או BLOCKED. תעד את התנאים שהובילו אליו. אין להסיק מכך מוכנות להשקה ציבורית.

## 25. הוראת התחלה ל־Claude

התחל ב־G0 על הענף והקוד העדכניים. הפק תוכנית ברורה ואת הפערים מול המסמך הזה, ואז התקדם בביצוע שכבר אושר. אל בנה מחדש רכיב תקין.

פעל כמו בעל המוצר: אל תסתפק בהעברת בדיקה; שאל האם הלקוח הבין, האם הנתונים נשמרים, האם העלות מוסברת והאם שותף יכול לראות ראיה אמיתית. הוסף תיקונים נחוצים בתוך ההיקף ותעד את הסיבה. רעיון חדש גדול נכנס ל־backlog עם תועלת, עלות ותלויות, ואינו מרחיב את השחרור בשקט.

עצור רק עבור הרשאה חסרה, פעולה הרסנית, הוצאה חדשה/חריגה או החלטה עסקית מהותית שאין לה בסיס מאושר. בכל חסם השלם עבודה שאינה תלויה בו והצג בקשה קונקרטית. אל תבקש שוב אישור על עבודה שכבר אושרה.

## 26. פרטי הפרויקט שנשמרו והגבול של המסמך

פרטי GitHub, הענף, Vercel וה־Preview בסעיף 1 הם ההנחיה המעודכנת של שי. שיחת אפיון מקצועית הכוללת עיצוב ואישור מפורש היא דרישת מוצר קבועה. כל עבודת ChatGPT בקוד תישאר בענף משלו וב־PR.

המסמך נשמר כהוראת ביצוע. יצירתו אינה שינוי בקוד, פתיחת PR, פריסה או אימות חדש של האתר. אין להציגו כהוכחת מימוש.
