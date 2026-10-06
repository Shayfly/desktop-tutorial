# 148AI — Operating Contract (חוזה עבודה מחייב)

> מסמך זה מגדיר את ה־Product Direction, Architectural Constraints ו־Operating Rules של 148AI. הוא אינו מחליף בדיקה הנדסית, ואינו מעניק אישור אוטומטי לכל מימוש. כאשר קיימת סתירה בין חזון עתידי לבין הוכחה הנדסית נדרשת, יש לשמר את החזון אך לבחור במימוש המינימלי, המדיד וההפיך שמקדם את ה־Golden E2E.

מסמכים קשורים: `ORCHESTRATION_ARCHITECTURE_HE.md`, `PRODUCTION_OS_VISION_HE.md`, `ARCHITECTURE_MANDATE_HE.md`, `ARCHITECTURE_REVIEW_HE.md`.
סדר עדיפות במקרה סתירה בין המסמכים: מסמך זה ← `AGENTS.md` ← ה־Review ← מסמכי החזון.

---

29A. היררכיית סמכויות ו־Source of Truth

בכל מקרה של סתירה בין רכיבים, קיימת היררכיית סמכויות ברורה:

1. Security, Privacy, Legal ו־Tenant Isolation.
2. User-approved Product Requirements ו־Acceptance Criteria.
3. Economics Policy ו־Authorized Budget.
4. Product Orchestrator.
5. Decision Layer.
6. Task Plan ו־Execution State.
7. LLM Recommendations.
8. Provider Defaults ו־Tool Suggestions.

LLM, Agent, Provider או Tool אינם רשאים לעקוף שכבה שמעליהם.

כאשר קיימת סתירה, המערכת אינה “מנחשת” ואינה ממשיכה בשקט.

היא עוצרת, מסמנת את הסתירה, מתעדת אותה ומחזירה מצב מפורש:

CONFLICT REQUIRES RESOLUTION.

Source of Truth חייב להיות מוגדר לכל סוג מידע:

Product IR הוא מקור האמת ל־Intent ולדרישות.

Build Contract הוא מקור האמת ל־Acceptance Criteria, Budget ו־Constraints.

Task Graph הוא מקור האמת ל־Execution Plan הנוכחי.

Policy Registry הוא מקור האמת ל־Decision Policies.

Provider Catalog הוא מקור האמת ל־Capabilities ולמחירי ספקים.

Attempt Ledger הוא מקור האמת ל־Execution Evidence ולעלות שנמדדה.

Verification Records הם מקור האמת ל־Pass / Fail / Not Verified.

אין להשתמש ב־Logs לא מובנים כמקור אמת עסקי או תפעולי.

29B. Desired State, Observed State ו־Verified State

המערכת חייבת להבדיל בין שלושה מצבים:

Desired State:

מה שהמשתמש ביקש ומה שה־Product IR מגדיר.

Observed State:

מה שהמערכת או הספק מדווחים שקרה.

Verified State:

מה שהמערכת הצליחה להוכיח באמצעות Evidence.

Observed אינו שווה Verified.

Provider Success אינו שווה Product Success.

Build Completed אינו שווה Acceptance Passed.

Preview Loaded אינו שווה Production Verified.

רק Verified State רשאי להפעיל Delivery, Promotion או חיוב סופי, בהתאם ל־Policy.

29C. Build Lifecycle

בנוסף ל־Task State Machine, חייבת להיות Build State Machine ברורה.

לדוגמה:

DRAFT.

ADMITTED.

PLANNED.

QUOTED.

AWAITING_APPROVAL.

AUTHORIZED.

RESERVED.

RUNNING.

PAUSED.

BLOCKED.

VERIFYING.

REPAIRING.

READY_FOR_DELIVERY.

DELIVERED.

FAILED.

CANCELLED.

ROLLED_BACK.

כל מעבר חייב להיות:

Explicit.

Durable.

Auditable.

Idempotent.

אסור ש־Build יקפוץ מ־RUNNING ל־DELIVERED ללא Verification Evidence מתאים.

אסור ש־Build יישאר במצב לא ברור לאחר Crash, Timeout או Worker Failure.

29D. Idempotency, Recovery ו־Exactly-once Economics

כל פעולה שעלולה להוציא כסף, ליצור Artifact, לשנות State או להפעיל Provider חייבת להיות Idempotent או מוגנת באמצעות Idempotency Key.

Retry של Worker לא יכול לגרום בטעות לחיוב כפול, יצירת תוצר כפול או שינוי State לא עקבי.

יש להפריד בין:

Execution semantics.

Billing semantics.

State transition semantics.

גם אם Provider אינו תומך ב־Exactly-once Execution, 148AI חייבת לספק לפחות:

Idempotency key.

Reservation tracking.

Duplicate detection.

Provider request correlation.

Reconciliation.

Recovery after timeout.

כאשר לא ניתן לדעת אם פעולה חיצונית הצליחה, המצב חייב להיות:

UNKNOWN — REQUIRES RECONCILIATION.

אסור לבצע פעולה יקרה נוספת רק משום שהתגובה הראשונה לא הגיעה.

29E. Pause, Cancel ו־Human Approval

המשתמש או Policy מורשה חייבים להיות מסוגלים:

Pause Build.

Resume Build.

Cancel Build.

Approve Scope Expansion.

Approve Additional Budget.

Approve Sensitive Action.

Approve External Deployment.

Approve Irreversible Operation.

Cancel אינו בהכרח מוחק פעולה שכבר נשלחה לספק.

לכן Cancel חייב להגדיר במפורש:

מה נעצר.

מה כבר בוצע.

מה לא ניתן לבטל.

מה יקרה ל־Reserved Budget.

מה יקרה ל־Artifacts שנוצרו.

במקרים של פעולה בלתי הפיכה, חריגה תקציבית, מידע רגיש, Deployment חיצוני או חוסר ודאות משמעותי, המערכת רשאית לדרוש Human Approval.

Human Approval חייב להיות:

Explicit.

Authenticated.

Scoped.

Timestamped.

Auditable.

29F. Scope Control

המערכת אינה רשאית להרחיב את ה־Scope של Build רק משום שמודל או Agent הציעו רעיון נוסף.

כל שינוי ב־Scope חייב להיות מסווג כאחד מאלה:

Within Scope.

Clarification.

Minor Change.

Material Change.

New Workstream.

Material Change או New Workstream דורשים:

Impact analysis.

Cost estimate.

Schedule impact.

Verification impact.

Updated Plan.

Authorization לפי Policy.

אם אין אישור, המערכת חייבת להישאר בתוך ה־Scope המקורי או לעצור.

אין “Feature Creep by Agent”.

29G. Security, Permissions ו־Untrusted Input

כל תוכן שמגיע ממשתמש, קובץ, אתר, Repository, Provider או Model נחשב Untrusted Input עד שהוגדר אחרת.

המערכת חייבת להגן מפני:

Prompt Injection.

Tool Injection.

Malicious Repository Instructions.

Data Exfiltration.

Secret Leakage.

Cross-tenant Access.

Unauthorized Deployment.

Malicious Dependencies.

Supply-chain Attacks.

LLM אינו רשאי להחליט בעצמו שהוא רשאי לקרוא Secret, לשלוח מידע החוצה, להפעיל Tool רגיש או לבצע Deployment.

כל Tool חייב להגדיר:

Capability.

Required Permissions.

Allowed Inputs.

Allowed Outputs.

Data Classification.

Cost Risk.

Side Effects.

Reversibility.

Approval Requirement.

Least Privilege הוא ברירת המחדל.

29H. LLM Output Contract

LLM אינו מחזיר “תשובה חופשית” כאשר הפלט אמור להפעיל מערכת.

כל פלט תפעולי חייב לעבור דרך Schema מוגדר הכולל:

Action.

Arguments.

Expected Outcome.

Required Evidence.

Estimated Cost.

Risk Level.

Dependencies.

Fallback.

Confidence.

אם הפלט אינו תקין, חסר, סותר או אינו עומד ב־Schema:

הוא אינו מבוצע.

הוא מסומן כ־INVALID MODEL OUTPUT.

LLM אינו רשאי:

להוציא כסף ישירות.

לשנות Budget.

לשנות Policy.

לעקוף Verification.

לשנות Product IR ללא Versioned Change.

לשנות Product DNA ללא Explicit Decision.

להכריז על Success ללא Evidence.

29I. Rollback ו־Recovery

לכל Build ולכל Artifact משמעותי חייבת להיות אפשרות Recovery מוגדרת.

לפחות:

Versioned Artifacts.

Immutable Attempt Records.

Previous Known Good Version.

Rollback Strategy.

Failed Deployment Recovery.

Partial Build Recovery.

Provider Timeout Recovery.

Worker Crash Recovery.

Database Transaction Boundaries.

Rollback אינו מוחק Evidence.

Rollback יוצר אירוע חדש ומתועד.

כאשר Rollback אינו אפשרי, המערכת חייבת לסמן זאת במפורש ולא להציג את המוצר כ־Healthy.

29J. Data Governance

כל Data שנוצר או נשמר על ידי 148AI חייב להיות מסווג לפי:

Tenant.

Project.

User.

Sensitivity.

Retention.

Deletion Policy.

Legal Hold.

Training Eligibility.

אסור להשתמש בנתוני לקוח לצורך Training, Evaluation, Caching או Reuse בין לקוחות ללא הרשאה מתאימה, מדיניות ברורה והפרדה טכנית.

Deletion חייבת לכלול גם:

Artifacts.

Caches.

Embeddings.

Logs.

Telemetry.

Backups בהתאם למדיניות.

Provider Copies כאשר ניתן לשלוט בכך.

29K. Golden E2E Acceptance Criteria

Golden E2E אינו נחשב VERIFIED רק משום שהמסלול עבר פעם אחת.

הוא חייב להוכיח לפחות:

Real User Authentication.

Real Project Persistence.

Real Product Plan.

Real Quote.

Real Budget Reservation.

Real Provider Call.

Real Multi-file Artifact.

Real Dependency Installation.

Real Build.

Real Tests.

Real Verification Evidence.

Real Repair או הוכחה שלא נדרש Repair.

Real Durable Artifact.

Real Preview.

Real Modification.

Real New Version.

Real ZIP Export.

Real Attempt Ledger.

Real Cost Record.

Real Failure Handling.

Real Recovery לאחר Restart או Worker Failure.

Real Tenant Isolation.

Real Secret Redaction.

כל שלב חייב להיות ניתן ל־Replay או להסבר באמצעות Evidence.

29L. מדדי הצלחה ל־Golden E2E

לפני שמרחיבים את הארכיטקטורה, צריך למדוד:

First-pass success rate.

Verified success rate.

Repair rate.

Retry rate.

Average cost per verified build.

P95 ו־P99 cost.

Time to verified artifact.

Provider failure rate.

Build failure rate.

Verification failure rate.

Duplicate execution rate.

Unknown external operation rate.

Recovery success rate.

Margin estimate.

Reconciled margin כאשר נתוני חיוב זמינים.

אם אין לנו את המדדים האלה, אין לנו עדיין Golden E2E Production Evidence.

29M. No Speculative Architecture

אין לבנות Abstraction, Engine או Framework רק משום שהוא עשוי להיות שימושי בעתיד.

כל רכיב חדש חייב לענות על אחת מהשאלות:

האם הוא נדרש כדי להעביר את ה־Golden E2E?

האם הוא מונע Lock-in יקר?

האם הוא נדרש לצורך Security, Cost Truth, Verification או Auditability?

האם הוא משרת לפחות שני Use Cases אמיתיים שכבר קיימים?

אם התשובה היא לא, הרכיב נשאר מחוץ ל־Production Path.

Future Vision נשמר במסמך וב־Interfaces מינימליים, לא במימוש מוקדם.

29N. Product Orchestrator — Logical Singleton

148AI חייבת Orchestrator אחד מבחינה לוגית.

זה אינו מחייב Process יחיד או Server יחיד.

המימוש יכול להיות מבוזר, עם Workers, Queues, Shards ו־Services.

אבל חייב להיות Owner לוגי יחיד לכל Build, עם:

Build ID.

Versioned State.

Lease או Ownership mechanism.

Conflict detection.

Durable transitions.

Recovery לאחר כשל.

אסור ששני Workers יחשבו שהם בעלי הסמכות הסופית על אותו Build.

29O. Definition of Done לכל שינוי

שום שינוי אינו נחשב Done רק משום שהקוד נכתב.

Definition of Done חייב לכלול, לפי הרלוונטיות:

Implementation.

Tests.

Migration.

Observability.

Failure handling.

Security review.

Cost impact.

Verification evidence.

Rollback או Recovery plan.

Documentation.

Replay או E2E proof.

אם שינוי אינו מוכן לכל אלה, יש לסמן אותו כ־PARTIAL ולא כ־DONE.

39. ניסוח מחייב לסיום

הייתי מחליף את סעיף 38 בנוסח מעט יותר קשיח:

38. ההחלטה המיידית

עכשיו לא פותחים עוד חזית.

חוזרים ל־Golden E2E.

המערכת צריכה לעבור מהחזון להוכחה מדידה.

מצא את המעבר הראשון במסלול Web/SaaS שעדיין נמצא במצב:

FAIL.

BLOCKED.

NOT VERIFIED.

UNKNOWN.

או שאינו מגובה ב־Evidence מספק.

תקן רק את המעבר הזה.

אל תבצע Refactor רחב שאינו נדרש כדי להעביר אותו.

אל תוסיף Capability חדשה.

אל תרחיב Scope.

אל תחליף רכיב עובד ללא Evidence שהחלופה טובה יותר.

לפני כל שינוי:

1. תאר מהו המעבר שנכשל.
2. תאר מה ה־Expected State.
3. תאר מה ה־Observed State.
4. תאר מה חסר כדי להגיע ל־Verified State.
5. תאר את ה־Root Cause המשוער.
6. תאר את השינוי המינימלי הנדרש.
7. תאר את הסיכון והעלות.
8. בצע את השינוי.
9. הרץ את ה־Verification המתאים.
10. עדכן את ה־Evidence ואת ה־Attempt Ledger.
11. אשר שהמעבר עבר.
12. רק אז עבור למעבר הבא.

אם אין מספיק מידע כדי לזהות את המעבר הראשון, אל תנחש.

בצע קודם Diagnostic Pass מוגבל, מתועד וזול, שמטרתו היחידה היא לזהות את ה־First Failing Transition.

במקביל, הוסף רק את שכבת ה־Instrumentation שסיכמנו, ורק במידה שהיא אינה מעכבת את ה־Golden E2E.

המטרה הראשונה:

Golden E2E #1 — VERIFIED.

המטרה שאחריה:

להפוך את ה־Golden Path שעובד למנוע אוניברסלי, חכם, רווחי ולומד.

המטרה הסופית:

המשתמש אומר מה הוא רוצה ליצור.

148AI מחליטה בצורה חכמה, מאומתת וכלכלית איך לגרום לזה להתקיים.

---

## הערות CTO והתאמות מימוש (2026-10-07)

מקבל את כל הסעיפים 29A–29O ואת סעיף 38. ההתאמות הבאות אינן משנות עיקרון; הן מגדירות איך ליישם בלי ליצור מורכבות מוקדמת:

1. **29C Build Lifecycle** — לא מוסיפים 18 מצבים בבת אחת. הקוד הקיים (`omni_prod/build_state.py`, `phase` ב־migration 013) מגדיר QUEUED → RUNNING → READY/FAILED/CANCELLED עם מעברים חוקיים בלבד. מרחיבים רק כשמעבר נדרש ל־Golden E2E: `UNKNOWN_EXTERNAL` (29D) ו־`VERIFYING` עכשיו; `AWAITING_APPROVAL`/`PAUSED` כשיש UI לאישור. QUOTED/AUTHORIZED/RESERVED כבר קורים באותה טרנזקציה של `v28_build_async` ולכן אינם מצבים נפרדים כרגע.
2. **29D Idempotency** — קיים: `build_id` כ־RQ job id, outbox (`build_outbox_relay`), journal להגשות ספקי מדיה עם recovery. **התאמה ל־LLM:** לרוב ספקי ה־LLM אין API לבדיקת "האם הבקשה בוצעה". לכן קריאת LLM שנקטעה (timeout) נרשמת כ־`UNKNOWN` ונחשבת כאילו נוצלה **בעלות המורשית המלאה**; ניסיון נוסף מותר רק אם התקציב הנותר מכסה אותו. כך לא מוציאים פעמיים בלי כיסוי, ולא נתקעים לנצח.
3. **29E Pause/Cancel** — Cancel נדרש (קיים חלקית ב־`build_state`); Pause/Resume ואישורים אנושיים נדחים עד שיש UI ומקרה אמיתי. ההגדרות של "מה קורה ל־Reserved Budget ול־Artifacts" נכתבות עם המימוש של Cancel.
4. **29H LLM Output Contract** — Schema חובה לכל פלט תפעולי: כן (הקוד כבר דוחה JSON לא תקין: `complete_json`). **אבל** שדות כמו Estimated Cost, Confidence ו־Risk Level **לא** יתקבלו מה־LLM עצמו — המודל אינו יודע את העלות האמיתית ו"ביטחון" שהוא מדווח אינו מכויל. עלות וסיכון מחושבים ע"י ה־Decision Layer ממקורות האמת (Catalog, Ledger).
5. **29K Golden E2E Criteria** — מתקבל במלואו, עם החלטה פתוחה אחת: **Real Dependency Installation**. ה־sandbox כרגע ללא רשת (בכוונה, מטעמי אבטחה). התקנה אמיתית דורשת proxy לחבילות עם allowlist ו־lockfile (פריט Supply Chain מה־Review). זו תוספת Scope משמעותית שצריך לאשר; החלופה הזולה לשלב #1 היא image עם סט תלויות מוצמד ומאושר — אך היא **אינה** "Real Dependency Installation" ולכן תסומן PARTIAL.
6. **29L מדדים** — המדדים מוגדרים ונאספים מה־Attempt Ledger. P95/P99 אינם משמעותיים לפני מדגם; לפי `PRODUCT_MISSION_AND_ACCEPTANCE.md` ההוכחה דורשת לפחות 3 prompts שונים, ולכן ה־Evidence של #1 יכלול את כל הריצות שבוצעו עם הערכים בפועל, בלי לטעון ל־P99.
7. **29N Logical Singleton** — יש בסיס: `worker_lease.py` ו־RQ job id ייחודי ל־build. חסר: lease מתמשך ב־DB לכל build ובדיקת בעלות במעברים; נבנה עם הרחבת ה־lifecycle.
8. **29J Data Governance** — עכשיו: שדות סיווג (tenant/project/sensitivity/retention/training_eligibility=false כברירת מחדל) בטבלאות חדשות כמו ה־Attempt Ledger. מחיקה מלאה מ־caches/embeddings/backups — עם מימושם.
