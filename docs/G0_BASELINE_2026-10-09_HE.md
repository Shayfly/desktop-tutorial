# G0 — בסיס, בעלות, ענפים, טריגרי פריסה ותוכנית חבילות עבודה

תאריך: 2026-10-09 (UTC 00:00 בערך). מבצע: Claude (session_01XFEE73…). לפי `docs/MASTER_EXECUTION_DIRECTIVE_2026-10-09_HE.md` §1, §22, §25.
המסמך משלים את `docs/PARTNER_REVIEW_GAP_MAP_HE.md` (מיפוי קריאה-בלבד של סשן Claude אחר על `b0a0cfa`) ולא משכפל אותו. בנקודות שבהן מצאתי אחרת, זה מסומן ב"תיקון".

## 1. בסיס

| פריט | ערך |
|---|---|
| נקודת קריאת המסמך | `b0a0cfac46b4ad632769c9feb5d68cd9ca9d9631` |
| HEAD של הענף הפעיל בתחילת G0 | `b0a0cfa`. אחר כך `ab253f7` (תיקון Preview, ראו §4) |
| ענף משימה של Claude | `claude/g0-baseline-2026-10-09` |
| ריצות פעילות בעת השילוב | אין. worker במצב idle (worker-diagnostics 37862201125, 23:55 UTC). בנייה אחרונה: `bld_8263a2a1…` הסתיימה ב-23:35 |
| בדיקות מקומיות | 1012 בדיקות; הכשלונות זהים לבסיס (17 מודולים שדורשים fastapi, שאינו מותקן כאן, ובדיקת W אחת). בדיקות Postgres חי: 5/5 |
| PRs פתוחים | #1 `repair/investor-demo-alpha → main` (ישן, לא יעד שילוב) |

## 2. טריגרי פריסה (נבדק בקבצי ה-workflow)

| workflow | push לענף הפעיל | push לענף משימה | הערה |
|---|---|---|---|
| deploy-worker.yml | **כן**, בנתיבים `omni_prod/**`, `infra/worker-host/**`, `infra/sandbox*/**`, `infra/postgres/**`, `requirements-production.txt`, `Dockerfile` | **לא** | מחליף את ה-worker. עד WP-OPS-1 לא בודק בנייה פעילה |
| build-evidence, worker-diagnostics, model-probe, internal-entitlement | רק כשהקובץ עצמו משתנה | לא | dispatch ידני על ענף משימה עובד ורץ על ה-runner המשותף. הם קריאה-בלבד |
| v11-overlay-ci | כן | **כן** (כל push) | CI בלבד, ללא פריסה |
| neon-bootstrap-ci | בנתיבי postgres/staging | כן, באותם נתיבים | CI בלבד |
| Vercel (Git integration) | פריסת Preview של 148aiv28 בכתובת הענף הפעיל | פריסת Preview **בכתובת נפרדת** של הענף | לא דורס את סביבת העבודה. פרויקט `148ai` לא נגעתי בו |

מסקנה: ענף משימה הוא בידוד אמיתי ל-worker. אפשר להריץ עליו את ה-workflows הקריאה-בלבד. השילוב לענף הפעיל הוא שמחליף worker, ולכן הוא נעשה רק בחלון בלי בנייה (§18), ובעתיד דרך שער drain.

## 3. בעלות

| רכיב | בעלים כעת | כלל |
|---|---|---|
| שילוב לענף הפעיל | Claude (הסשן הזה) | fast-forward מענף משימה אחרי בדיקות ובחלון בטוח |
| `docs/PARTNER_REVIEW_GAP_MAP_HE.md` | סשן Claude אחר (ענף `docs/partner-review-gap-map-2026-10-09`) | שולב כמסמך כפי שהוא, עם תיקונים כאן |
| ChatGPT | קריאה בלבד | שינוי רק בענף `chatgpt/...` ו-PR |
| ענפי feature מ-6/10 (infisical, qstash, r2-credentials) | לא פעילים | לא משולבים בשחרור הזה |

## 4. ממצא G0 שתוקן מיד: "שום דבר לא מגיב" (Preview הספרייה)

- **ראיה:**
  - worker-diagnostics 37861985721, יומן preview-worker ויומן preview-router;
  - build-evidence 37861676931 ו-37861693046 (קוד הגרסה `v_f65e904334b04776`).
- **רצף האירועים:**
  - Preview `prv_c242ef7e…` עלה ב-23:35:28.
  - בדיקות ההתנהגות עברו: POST /books → 201, /members → 201 ו-409 על כפילות, /loans → 201, /return → 200, DELETE → 200.
  - אחר כך `record_acceptance` נכשל ב-`IndeterminateDatatype`, בגלל `jsonb_build_object(%s, …)` עם מפתח שאין לו טיפוס.
  - משימת ההשקה פירקה את הקונטיינר, ומ-23:38 כל בקשה קיבלה 502.
- **תיקון:**
  - `%s::text` ב-`omni_prod/preview_repository.py`.
  - בדיקת Postgres חי `test_preview_acceptance_report_is_recorded_on_real_postgres`. בלי התיקון היא נכשלת באותה שגיאה בדיוק.
  - שולב ב-`ab253f7`. Deploy build worker 37862267177 הצליח.
- **למה זה לא נתפס קודם:** מסלול הקבלה ההתנהגותית רץ בבדיקות מול fake pool בלבד.
- **פער שנחשף (נכנס ל-G5):** האתר שנבנה מסתיר כל הודעה אחרי הראשונה, כי ל-`showBanner` יש `style.display='none'` קבוע. הבאג נמצא בהרצה בדפדפן אמיתי מקומית. בדיקות HTTP לא תופסות אותו.

## 5. תיקונים למפת הפערים של הסשן האחר

| נושא | במפה | בפועל |
|---|---|---|
| אישור | "נאכף בשרת, VERIFIED" | נאכף רק כקישור לחוזה (fingerprint). **אין** idempotency (build_id אקראי, אין אינדקס ייחודי), אין TTL, אין קישור לגרסת brief ולגרסת תקציב. לחיצה כפולה ב-API יוצרת שתי בניות ושתי הזמנות כסף (`investor_app.py:1707`, `020_m5_build_contracts.sql:38`) |
| פריסה | "נפרס בכל push" | נכון, ובלי בדיקת בנייה פעילה. בנייה באמצע נהרגת, וה-janitor מכשיל אותה אחרי 45 דקות |
| תקציב QA | "$0.35 נוצלו" | זה הסכום **מאז** `OMNI_QA_BUDGET_SINCE=2026-10-08T17:12Z`. מכל הזמנים נספרו $3.06. לפי §15 סינון תאריכים בלי הוכחת free tier אינו מותר, ולכן זה מתוקן ב-WP-COST-1 |
| QA התנהגותי | "QA קורא קוד ולא מפעיל את המוצר" | יש בדיקות HTTP התנהגותיות (`web_saas_acceptance.py`), והן הן שעברו בספרייה. אין דפדפן |

## 6. חבילות עבודה (סדר ביצוע)

עמודות לכל חבילה: מזהה, מטרה, קבצים, קבלה, בדיקה, עלות, סיכון ו-rollback. הבסיס של כולן הוא `ab253f7` אלא אם צוין אחרת.

| מזהה | שער | מטרה | קבצים עיקריים | קבלה | בדיקה | עלות | rollback |
|---|---|---|---|---|---|---|---|
| WP-OPS-1 | G0/§18 | פריסת worker לא מחליפה worker באמצע בנייה או שינוי | deploy-worker.yml, סקריפט drain | push בזמן בנייה ממתין עד שהיא מסתיימת (עם deadline); אחרי deadline הפריסה נכשלת בגלוי ולא הורגת | dispatch על ענף משימה + בנייה דמה | $0 | revert של ה-workflow |
| WP-COST-1 | G4/§15 | ספירת תקציב QA בלי הסתרה בתאריך | qa_budget.py, env | ספירה מכל הזמנים, או "since" רק עם ראיית free tier רשומה; הפרדה בין אומדן, הזמנה ועלות מדווחת | live Postgres | $0 | env |
| WP-APR-1 | G2/§5 | אישור idempotent: לחיצה כפולה = בנייה אחת | investor_app.py, migration ייחודית, app.js | שתי בקשות מקבילות עם אותו approval → בנייה אחת, הזמנה אחת | live Postgres מקבילי | $0 | migration הפיכה |
| WP-G5a | G5 | בדיקת דפדפן אמיתית לאתר שנבנה (שגיאות JS, טפסים, משוב חוזר) | omni_prod/browser_acceptance.py, sandbox/preview | הספרייה הנוכחית נכשלת על ההודעה הנעלמת; אתר תקין עובר | מקומית + rehearsal | ~$0.07 | flag |
| WP-REG-1 | G1/§6 | רישום: סוגי skill, ממדים נפרדים, evidence עם scope ורעננות, 12 תפקידים, 49 skills ישנים → DEFINED | agent_catalog, runtime_bindings, registry_audit | אין VERIFIED רחב: כל אימות עם scope; אין PARTIAL בלי מימוש | יחידה + מסמך מחושב | $0 | revert |
| WP-DSC-1..4 | G2/§4 | שיחת אפיון, ProjectBrief גרסאי, "בחרו עבורי", העדפות עיצוב, סיכום ואישור מחדש | חדש: intake/brief; build_contract; app.js | שיחה ברורה, עמומה ומואצלת; רענון שומר; שינוי מבטל אישור | live Postgres + דפדפן | ~$0.03 לשיחה | flag |
| WP-NOLOGIN | G2 | "בלי התחברות" מכובד | product_architect.py | אין auth בתוכנית | rehearsal | ~$0.07 | revert |
| WP-DATA-1 | G4/§13 | נתוני Preview עמידים (volume לכל preview) ומסומנים כזמניים עד אז | preview_runtime.py | restart של Preview שומר נתונים | חי על Oracle | $0 | revert |
| WP-UX-1 | G3 | עצירה/ביטול, יומן חי, נעילת כפתור, הצגת כשל + פעולה הבאה | investor_app.py, worker, app.js | ביטול עוצר צעדים חדשים ומשחרר הזמנה | API + דפדפן | $0 | revert |
| WP-PUB-1 | G6 | "פרסום" מוסתר או מסומן "לא זמין"; מסלולים דטרמיניסטיים חסומים | investor_app.py, app.js | אין הצלחה שקרית | API | $0 | revert |
| WP-G7 | G7 | 3 תרחישי שותף, חבילה קפואה | docs | §21, §23 | Preview פרוס | ~$1 | — |

תקציב: התקרה $10 לכל הספקים יחד, בלי איפוס. כל הוצאה נרשמת ב-STATUS עם מזהה ריצה.
