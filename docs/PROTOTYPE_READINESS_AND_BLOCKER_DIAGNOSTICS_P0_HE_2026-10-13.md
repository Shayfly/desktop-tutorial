# 148AI — נספח P0 מחייב: אבחון מוכנות לבנייה והצגת חסימות ללקוח ולבעל המערכת

תאריך: 13.10.2026 | משימת מעקב: GitHub Issue #26 | תוכנית מקור: T01–T09 / GitHub Issue #23 / Draft PR #24

**זהו ADDENDUM מצטבר לתוכנית T01–T09, ולא שינוי או החלפה שלה.**
**מצב מסמך זה: SPECIFIED / NOT IMPLEMENTED OR LIVE VERIFIED.**
להחיל על אב־הטיפוס הפרטי לפני הכרה ב-T03/T06/T07/T09 כ-DONE. אין לבצע פריסת Production, ביטול הגנת Preview או פתיחת תקציבים למען עיצוב המסך.

## 1. הבעיה שהלקוח הציג בצילום

ב-Preview נצפה מסך "תוכנית ועלות" המציג "אפשר לבנות, עם מגבלות", ובאותו מסך בניית הפרויקט אינה ניתנת לאישור עקב "לא ניתן לתמחר". בפרטים הטכניים מופיע:

cost_quote_unknown: A required capability is not available yet: ai.agent.tools, integration.maps, media.audio.tts, outbound, target.agent

כפתור "אשר והתחל בנייה" מושבת. הרשימה אינה מסבירה איזו דרישה גרמה לכל תלות, האם היא באמת חובה, איזה קובץ/Skill/Agent/Provider חסר, האם מדובר בתמחור בלבד או בחוסר מימוש, ומי צריך לתקן. בנוסף הנייד מציג צפיפות וחפיפות בין תצוגת התוכנית, השיחה, פסי הניווט והשדה התחתון.

היעד: **שקיפות מלאה ומדויקת של החלטת הבנייה; לא אישור אוטומטי של מוצר שאי־אפשר לבנות.**

## 2. עיצוב UX מחייב: שתי שכבות מידע על אותו Source of Truth

### 2A. תצוגת לקוח (Customer Readiness)

בכל פרויקט נוצר רכיב קבוע, קטן וברור מעל תוכנית העבודה ובמובייל מעל אזור השיחה:
- כותרת "מוכנות הפרויקט" + מצב מדויק: מוכן לבנייה / מוכן לאחר הבהרות / אפשרי בגרסה מצומצמת לאחר אישור / חסום בשל תלות חסרה / בנייה בעיצומה / ממתין לבדיקת ספק / שגיאת מערכת / לא ידוע.
- אם חסום: "נמצאו N חסימות, M שאלות ו-K מגבלות" — רק ספירות אמת מתוך מנוע מוכנות; אל תראה "אפשר לבנות" כאשר המודל, התקציב או ההרשאות אינם מאפשרים להתחיל.
- לכל חוסר: שם בעברית פשוטה; למה המוצר זקוק לו; מה בפועל מונע ביצוע; האם חובה לפי בקשת הלקוח; מה אפשר לעשות עכשיו; מתי נבדק לאחרונה.
- פעולות פונקציונליות: "השב על שאלה", "ערוך את הדרישה", "בדוק מחדש", "צפה בפירוט", "בקש גרסה מצומצמת" (בתנאי שהמשתמש מאשר ופורסם בדיוק מה חסר בגרסה הזאת), או "אשר והתחל" רק כאשר השרת מאשר.
- אל תסתיר חסימה מאחורי פרטי מפעיל, ואל תראה HTML מפחיד עם קודי שגיאה כטקסט מרכזי. קודים טכניים בפירוט מתקדם בלבד.
- לקוח רואה השפעה על הפונקציונליות: "מפה אינטראקטיבית לא תיכלל בגרסה מצומצמת אם תבחר בה"; ללא הבטחה לשימוש בספק חלופי שאינו מחובר.
- בעל אב־הטיפוס רשאי להפעיל גם תצוגת לקוח כדי לבדוק את החוויה האמיתית.

### 2B. מסוף מנהל/מפתח פרטי (Founder Readiness & Blocker Center)

גישה רק דרך RBAC/entitlement מפורש, אימות שרת ולוג audit. אין לגלות מידע פרטי או סודות באמצעות שינוי JS בלבד. מסך אבחון עילי ודף עומק:
1. סטטוס תפעולי לפי רכיב: API/route, User Auth, Neon Postgres + migration, Redis/RQ, worker heartbeats, Sandbox/isolation, model-chat, architect, agents/skills, provider router, provider balance/quota/quote, object storage, generated preview, verification gates, Vercel protection/automation, Git SHA parity. לכל שורה VERIFIED/PARTIAL/BROKEN/BLOCKED/UNKNOWN עם זמן בדיקה ואסמכתה.
2. לכל חסימה: blocker_id יציב, code, stage, severity, provenance, requirement_id + requirement_revision, mandatory vs optional vs recommended, מקור ה-customer request בציטוט מינימלי נטול PII, dependency chain, בעל אחריות (owner domain), סוג כשל, רכיב חסר, השפעה על יכולת לבנות, פעולת תיקון מומלצת ובדיקת אימות. אין להציג הנחה כעובדה.
3. מקום של תקלה בקוד: קבצים/פונקציות אמיתיים מה-Registry או מטבלת source mapping מאומתת, ולא נתיבים מומצאים. הצג "לא ידוע; יש לאתר" כשלא אומת.
4. ספק ומודל: configured? key configured? (bool only), supported capability, model availability, quote known?, pricing_version, quality gate, last provider response, retry_after, fallback candidates with eligibility. לעולם לא להציג API key או body המכיל secret.
5. פיננסים: estimate/reserved/actual/settled לפי build_id, shared QA cap vs *real upstream provider balance* — אין להציג "10$ אצל כל ספק" בלי אישור API/דשבורד. UNKNOWN כשאי אפשר לקרוא יתרה. להבחין בין insufficient_balance/quota_exhausted/rate_limited/auth_failed/provider_down/cost_unknown.
6. "Copy diagnostic" לייצוא דוח מסונן בלי מפתחות, פרטי משתמש רגישים או URLs חתומים; כולל SHA, env type, timestamps, result, linked traces, acceptance gate. הייצוא הוא לקריאה, לא מבצע אוטומטית שינויי production.
7. מערכת מציעה Run safe checks (read-only) או פתיחת GitHub Issue עם נתונים מסוננים; ביצוע תיקון קוד, ENV או חיוב ספק דורשים תהליך מפורש ומאובטח נפרד. אין כפתור "תקן הכול" שמנסה פעולות מסוכנות.
8. במסך ניהול: מיון קודם לפי "חוסם בנייה", אחר כך "מעכב בדיקות", אחר כך "לא נדרש כרגע". חיפושים לפי project_id, build_id, capability_key, agent_key, skill_key, provider, SHA.

## 3. אבחון אוטומטי כבר בשלב בקשת לקוח חדשה

- מיד לאחר כוונת לקוח בעלת משמעות, הצג "בודק מה נדרש לבנייה", והפעל cheap deterministic inventory ללא קריאות AI בתשלום רק לצורך בדיקת מוכנות.
- לאחר ניסוח/הבהרה/שינוי אפיון הרץ evaluation לפי immutable Product IR + plan revision + catalog revisions. עדכן חזית ואבחון מנהל יחד. אל תתקדם למסקנת מוכנות לפני שהתלות נסגרה.
- בכל שלב יש להציג שלוש קבוצות: (1) דרישות הלקוח שאושרו, (2) חוסמים מוכחים, (3) תכונות שניתן לדחות **רק באישור הלקוח**. תקן false positive שמסמן תוספות מיותרות כחובה; אל תכפה API, DB, AI agent, מפות, TTS או outbound על אתר תוכן פשוט שלא ביקש אותן.
- בכפוף להרשאת מנהל, הצג "מה צריך לפתח כדי לתמוך בבקשה הזאת?" עם רשימת dependencies ותתי־משימות למימוש: Registry entries, source files, env key names, tests, CI/Preview checks, estimates, owner domain.
- עם שינוי בקטלוג או סביבת ספק, אל תציג "נבדק מחדש" אם לא התרחש evaluation אמיתי. הצג STALE / last_checked_at כאשר הנתונים לא עדכניים.
- הקפד ששאלות הבהרה לא יומצאו רק כדי למנוע משימת בנייה שכבר אפשר לאשר.

## 4. מצבי מוכנות בלתי סותרים

יש להפריד שלוש קביעות נפרדות:
A. scope_feasibility: CAN_IMPLEMENT_FULL / CAN_IMPLEMENT_REDUCED_WITH_CONSENT / UNSUPPORTED / NOT_YET_ASSESSED.
B. execution_readiness: ADMISSIBLE_NOW / BLOCKED_REQUIREMENTS / BLOCKED_CAPABILITY / BLOCKED_PROVIDER_OR_QUOTE / BLOCKED_BUDGET / BLOCKED_INFRA / BLOCKED_SECURITY / TEMPORARILY_UNAVAILABLE / UNKNOWN.
C. build_lifecycle: DRAFT / DISCOVERY / APPROVED / QUEUED / PLANNING / BUILDING / TESTING / REPAIRING / VERIFYING / PREVIEW_READY / FAILED / CANCELLED.

למנוע אמירה "מוכן לבנייה" על בסיס capability feasibility כאשר build admission נכשל. ה-CTA הפעיל מחייב בדיקה בצד שרת על *אותו* project_id/account_id, requirement fingerprint, contract version, agent/skill routing, provider quotes and budget reservation. Snapshot מוכן שהתיישן צריך לעבור revalidate לפני הוצאת כסף.

## 5. מודל נתונים/API מומלץ (התאמה לפני הוספת endpoints)

מקור אמת מרכזי ל-ReadinessAssessment בתוך domain, לא שני מנועים שונים ב-UI וב-backend; שקול להשתמש ב-POST /api/v28/projects/{id}/build-contracts הקיים עם שדות מורחבים או GET /api/v28/projects/{id}/readiness (מחזיר latest approved plan). תוספת endpoint פרטי /api/v28/operator/projects/{id}/readiness-diagnostics או הקיים אם יש דומה.

הנתונים צריכים לכלול:
- schema_version, project_id, account_scope, requirement_revision, requirement_fingerprint, contract_id, contract_version, plan_id, generated_at, checked_at, expires_at/stale, evaluated_environment, source_commit_sha.
- feasibility, execution_readiness, build_lifecycle, can_build (מחושב מהשרת), required_approvals, optional_scope_proposals, totals.
- blockers[]: id, code, category, severity, blocking_stage, title_he/title_en, customer_explanation, operator_diagnosis, required, requirement_id, source_requirement, capability_key, dependency_path, provider_key/model_key, agent_key/skill_key, service_key, quote_status, quote_version, env_name (name only), checks[], owner_domain, recommended_actions[], evidence_refs[], last_verified_at, resolution_status.
- signals[]: source (db/worker/model/quote/catalog), observed_status, reason, observed_at, evidence_ref. No secrets or raw provider payload leaking PII.
- operator-only diagnostic must be scoped and redacted. Customer endpoint must not include internal fields, even if hidden by CSS.
- stable codes/category from centralized taxonomy; no string parsing of free-form Python exception as the basis for UI decisions.

Re-evaluate and emit updates upon: conversation change, plan/contract revision, quote/approval, provider availability/usage update, enqueue, worker/job status, build failure, repair, preview probe, modification, resumed session. Use polling on existing channels if available; do not introduce WebSocket/Temporal solely for this feature. Rate-limit/reuse read-only checks; never perform test calls to billable AI per keystroke.

## 6. טיפול מדויק בחמש החסימות מהצילום

**אין להסיק אוטומטית שהן מיותרות או שהן מתוקנות.** לכל אחת לבצע Dependency Audit:

| Capability | בירור חובה | פעולה תקינה |
|---|---|---|
| ai.agent.tools | האם הלקוח ביקש סוכן שמבצע פעולות וכלים? האם Skill ו-Agent קיימים עם allowed tools ואימות? | אם חובה — תכנון runner/permissions/provider + quote; אם לא — להסיר מה-required list על ידי תיקון ה-IR והבדיקות |
| integration.maps | האם באמת נדרש אינטגרציית מפות חיה או רק מידע סטטי/תמונה? | חיבור ספק/מפתח/מחיר/תנאי שימוש ובדיקות, או אפשרות fallback שאינה מחליפה תכונת חובה ללא אישור |
| media.audio.tts | האם הלקוח ביקש קריינות ודיבור בפועל? | ספק TTS מוכח + quote/test או גרסה ללא TTS רק באישור |
| outbound | האם נדרשת שליחת מייל/SMS/webhooks בזמן אמת? | ספק משלוח ו-rate/credentials ו-quote או self-contained רק אם בקשת הלקוח באמת מאפשרת זאת |
| target.agent | האם מוצר היעד הוא AI Agent או אתר/מערכת עם צ'אט? | לדייק product family + required runtime; אתר עם צ'אט לא מחייב בהכרח target.agent מלא |

מצב cost_quote_unknown יכול לנבוע מ-required quote חסר, מ-assignment חסר או מ-infra quote חסר — **לא להתייחס לכל המקרים כאל "אין לנו את היכולת"**. שמור evidence של הבחנה בין NOT_IMPLEMENTED, NOT_CONFIGURED, UNPRICED, DISABLED_BY_POLICY ו-UNVERIFIED. תן קישור ברור בין החסם לבין רכיב הקוד/Registry שמגדיר אותו והשלב שבו נהיה required.

### נקודות חיבור בריפו (יש לקרוא מחדש את HEAD לפני שינוי)
- omni_prod/creator_plan.py → build_plan_preview: עכשיו כולל blockers + can_build + build_authorization; מחזיר CostQuoteUnknown כללי. להרחיב ל-structured reason ו-provenance.
- omni_prod/build_cost_plan.py → collect_build_cost_inputs: המיפוי בין required capability לבין provider assignments/pricing, ו-CostQuoteUnknown. לא להסיר fail-closed.
- omni_prod/product_architect.py וה-Product IR/Capability Registry → מקור תלות אמיתי, עם mandatory vs optional ו-product family.
- omni_prod/investor_app.py → build-contracts/approvals/builds endpoints: ensure identical admission evaluation; auth and QA caps.
- omni_prod/qa_budget.py → shared internal QA spending, not per-provider external bank balance.
- omni_prod/assets/app.js → renderPlan/startBuild and current collapsible operator details; integrate status surface without breaking workspace and build auto-transition.
- omni_prod/assets/app.css → responsive/RTL/mobile overlapping panels, top banner and bottom composer.
- Master Agents Registry / Master Skills Registry + availability and evidence catalog (read and verify before mapping paths).
- tests: add unit/contract/security/browser/E2E cases, reusing existing suites and fixtures when suitable.

## 7. UI מובייל — דרישות מפורשות מהתמונות

- סטטוס מוכנות בראש הפרויקט, גלוי גם כאשר הכרטיס "תוכנית ועלות" מקופל. לחיצה על המספר פותחת רשימת חוסמים ברורה.
- לא להציג בו-זמנית על הנייד שני אזורי גלילה מקוננים וחלוניות גדולות שמכסות את תוכן השיחה. אחת פתוחה בכל פעם; הצג header sticky במידה מדודה.
- פס צ'אט תחתון וכפתור שליחה לא מסתירים תוכנית ופעולות, ו-bottom tabs + safe-area של iOS לא חוסמים לחיצה על "אשר והתחל".
- מצב loading, error, stale, offline, 401-protected ברור; אין כפתורים מושבתים ללא סיבת חסימה צמודה.
- Hebrew RTL ו-English LTR, accessibility labels, 44px touch target, keyboard focus order, overflow break-word לקודי capability, תמיכה ב-iPhone 375px ובדסקטופ.
- בדיקות תמונות ותסריטי דפדפן אמיתי, לא צילום מסך שבו השדות מוצגים אך אינם מחוברים.

## 8. בדיקות קבלה חובה (לא mock בלבד)

A1. לקוח מבקש אתר תדמית פשוט. המנוע אינו דורש maps/tts/target.agent/outbound/agent.tools אם לא התבקשו.
A2. לקוח מבקש מוצר מורכב עם כל חמש היכולות. כל תלות מדווחת עם מקור דרישה וסטטוס מימוש/quote מדויק; אין הסרה שקטה.
A3. הזרק חסר provider quote ליכולת חובה: readiness=BLOCKED_PROVIDER_OR_QUOTE, כפתור בנייה חסום עם סיבה ופעולת תיקון, 0 חיובים.
A4. הזרק חסר Skill מוגדר/מאומת: category=AGENT_SKILL_MISSING, וללא "אפשר לבנות מלא" שגוי.
A5. עדכן הצעת מחיר תקפה או ספק מוגדר והריץ recheck; החוסם מוסר רק לאחר אימות שהכלל עבר.
A6. תכונה אופציונלית אינה חוסמת בנייה כאשר כל קריטריוני הקבלה של הגרסה שאושרה מתקיימים. תכונת חובה מחייבת הסכמה לגרסה מצומצמת ואפיון/contract חדש.
A7. משתמש ללא הרשאת Founder אינו יכול לצפות בפרטי ENV names, provider settings, raw logs או diagnostic export.
A8. Internal QA shared remaining credit ומאזן ספק upstream מוצגים בנפרד. חוסר יתרה אמיתי מספק מזוהה רק מראיה; rate-limit 429 אינו מסומן ללא בסיס כ"נגמר כסף".
A9. plan preview approval ובניית POST מסכימים על can_build/quote/mandatory gates; שינוי quote/budget אחרי preview גורם approval stale/recheck, לא overspend.
A10. iPhone Safari: status, composer, CTA, tab-nav and project menu are usable, no clipping or overlapping of scroll regions; screenshot evidence in Hebrew and English.
A11. Reload/new session restores project readiness/approved scope and timestamps; cannot inherit another account's diagnostics.
A12. user-approved eligible plan → queue/build → exact status + build_id → verified private Preview → modification/new version; preserve budget, rights and secure sandbox gates.
A13. Fault injection for worker down/migration pending/Preview 401/provider 503 shows distinct reason and scoped fix actions, not generic "plan doesn't allow costs."
A14. Real data contract tests validate each blocker origin, severity and action. No invented file paths, fabricated provider balances or test results.

## 9. סדר הביצוע והקשר לתוכנית T01–T09

- **T01 (P0 addendum):** לתעד את חמש החסימות המקוריות ולעקוב אחר כל אחת ב-code path/contract/quote; להוסיף taxonomy ודוח first reproducible failure עם exact SHA.
- **T03 (P0):** classifier של חובה/רשות, AI discovery, Product IR עם provenance, DAG capable vs required, השפעה על customer scope.
- **T06 (P0):** מסך readiness בראש כל פרויקט, טבלת חסימות, כלי מנהל, עיצוב מובייל ומעבר לבנייה.
- **T07 (P0):** מחיר/ספק/תקציב לפי יכולת והודעות quota אמיתיות, parity בין preview/approval/queue.
- **T08 (P0):** RBAC, redaction, logs, safe checks, session persistence, evidence.
- **T09:** להרחיב Golden E2E בשני תרחישים: (1) חסימה ואז תיקון אמיתי; (2) בקשה מורכבת והצעה לצמצום scope עם אישור מפורש, ואז Build→Preview→change.

העבודה מתבצעת בענף פיתוח + PR + CI + protected Preview; לא לשנות Production ולא לצרוך API בתשלום רק כדי לבדוק תוויות. יש לחבר את השדרוג לקוד המבצע ולבדיקות; מסמך UX בלבד אינו השלמה.

## Definition of Done מחייב

בפרויקט החסום שבתמונות, בתוך כמה רגעים לאחר עדכון האפיון, מופיעה בראש המסך אבחנת מוכנות עקבית שמסבירה ללקוח מדוע אי אפשר להתחיל ומה יכול לעשות. מנהל רואה לכל אחת מחמש החסימות מקור דרישה, האם נדרשת, Dependency chain, רכיב קוד/Registry מאומת, סטטוס provider+quote, פעולה נדרשת + בדיקת אימות. לאחר תיקון אמיתי או אישור חוזר לגרסה מצומצמת, המוכנות מחושבת מחדש בהתאם לאותו build contract; הכפתור מופעל רק כשהשרת באמת יכול לקבל את הבנייה. דפדפן נייד עובד ללא חפיפות. יש ראיות לבדיקות הרכיב ולתסריט ה-Preview, מבלי להחליש Security/FinOps.

**מצב: SPECIFIED, לא נבדק/מומש. משימה #26 משלימה את #23.**
