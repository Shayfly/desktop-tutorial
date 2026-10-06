# Architecture Mandate (founder)

אני רוצה שתיקח את המסמך הבא לא כפקודת מימוש עיוורת, אלא כ־Architecture Mandate עם יעדים ועקרונות שאסור לאבד.

אני רוצה שתפעל כאן גם כ־Senior Architect / CTO ולא רק כמפתח שמבצע הוראות.

אם לדעתך חלק מהארכיטקטורה שאני מציע אינו הדרך הנכונה, יקר מדי, מסובך מדי, מוקדם מדי, יוצר coupling, או שיש דרך טובה יותר להגיע לאותה מטרה — תגיד זאת לפני המימוש ותציע חלופה.

אני מעדיף שתאתגר החלטה גרועה מאשר שתבצע אותה בדיוק.

מצד שני, אל תשנה עקרונות עסקיים או Product Goals בלי להסביר במדויק למה ומה החלופה נותנת לנו.

המטרה היא לבנות את 148AI בצורה נכונה לטווח ארוך, לא רק לסמן Tasks כ־Done.

היעד העליון

148AI צריכה להפוך ל־Universal AI Production Operating System.

לא עוד Wrapper למודל אחד.

לא עוד Builder פשוט.

לא מערכת שבוחרת “איזה מודל הכי זול”.

המשתמש אומר מה הוא רוצה שיתקיים, ו־148AI מחליטה איך ליצור אותו.

המשתמש יכול לבקש:

אתר, SaaS, אפליקציה, משחק, Agent, Automation, תמונה, וידאו, סרט, מוזיקה, Voice, Audio, 3D או מוצר שמשלב כמה מהם יחד.

המערכת צריכה:

Understand → Architect → Simulate → Allocate → Create → Compare → Verify → Repair → Compose → Deliver → Learn → Profit.

עיקרון מרכזי

פונקציית המטרה שלנו היא:

Produce the highest-quality verified final product at the lowest total justified cost while preserving a required profit margin.

חשוב:

“Lowest Cost” לא אומר להשתמש במודל הזול ביותר.

אם שלושה מודלים שעולים יחד 0.30 דולר מייצרים תוצאה טובה ומאומתת, בעוד מודל זול של 0.04 דולר גורר retries, repairs ו־failures ומגיע ל־0.50 דולר — שלושת המודלים הם הבחירה הזולה יותר.

אנחנו מודדים:

Cost Per Verified Successful Outcome.

לא Cost Per API Call.

הארכיטקטורה שאני חושב שנכונה

אני מציע:

User Request
→ Universal Product IR
→ Task/Capability DAG
→ Orchestration & Optimization Engine
→ Specialized Models / Providers / Tools
→ Verification
→ Repair / Retry / Escalation
→ Product Composition
→ Final Verification
→ Delivery
→ Feedback / Learning
→ Profit Accounting.

אבל אני רוצה שתבדוק את ההצעה הזאת באופן עצמאי.

לפני שאתה מיישם אותה, אני רוצה ממך לענות:

1. האם Universal Product IR הוא abstraction נכון?
2. האם Task/Capability DAG הוא המבנה הנכון לכל סוגי המוצרים שלנו?
3. האם יש סוגי מוצרים שבהם DAG בלבד אינו מספיק ונדרש State Machine, Workflow Graph, Event Graph או מבנה אחר?
4. האם Product IR ו־DAG צריכים להיות שני רכיבים נפרדים?
5. איפה נכון למקם Orchestration, Routing ו־Optimization?
6. האם model_router הקיים צריך להפוך לרכיב קטן בתוך מנוע גדול יותר?
7. איך היית מונע מהמערכת להפוך למפלצת מורכבת מדי?
8. איזה חלקים אפשר לבנות עכשיו באופן כללי ואילו כדאי לדחות עד שיהיו לנו נתוני אמת?

אם לדעתך יש Architecture טובה יותר — תציע אותה.

Multi-Model Orchestration

אסור שהארכיטקטורה תהיה:

Request → One Model → Result.

היא צריכה לאפשר:

Product → Tasks → Best model/provider/tool per task → Composition.

מוצר אחד יכול להשתמש במודל אחד או בעשרה.

אין יעד להשתמש בהרבה מודלים.

אין יעד להשתמש במעט מודלים.

היעד הוא להשתמש בדיוק בכמות היכולת הנדרשת.

לדוגמה, סרטון יכול להשתמש ב:

LLM להבנת הבריף.

LLM אחר לתסריט.

Image Provider ל־Visual Assets.

Video Provider ל־Motion.

TTS ל־Voice.

Music Provider למוזיקה.

Model נוסף לבדיקת continuity.

Composer לחיבור.

Verifier לתוצאה הסופית.

אפליקציה יכולה להשתמש ב:

Architecture model.

Frontend model.

Backend model.

Database planning.

Image provider.

Testing model.

Debugging model.

Security reviewer.

Build tools.

Deterministic tests.

אבל שוב: אל תיישם “מודל שונה לכל שלב” כחוק.

אם אותו מודל נותן תוצאה טובה יותר וזולה יותר למספר Tasks — השתמש בו.

אני רוצה Optimization, לא פיצול מלאכותי.

Universal Product IR

אני מאמין שצריך להיות representation אחיד של מה שהמשתמש מנסה ליצור.

לדוגמה:

מוצר יכול להכיל Application, Brand, Media, Agents, Integrations, Infrastructure ו־Data.

אבל אני רוצה שתבחן את זה.

Product IR צריך לייצג לפחות:

Product goals.

User requirements.

Product families.

Capabilities.

Assets.

Components.

Dependencies.

Identity.

Brand/style.

Data.

Integrations.

Runtime requirements.

Acceptance criteria.

Quality targets.

Budget.

Deadline.

Security/privacy constraints.

Deployment targets.

אם לדעתך לא נכון לקרוא לזה IR, או שצריך כמה IRs לפי שכבה — תגיד.

המטרה חשובה יותר מהשם.

Creative Intelligence

אני לא רוצה מערכת שרק “עובדת”.

אני רוצה תוצרים ברמה עולמית.

לכן הצעתי Creative Director / Taste Engine.

אבל אני רוצה שתחשוב האם זה Agent אחד, מערכת Policies, Evaluation Layer, Style Memory או שילוב שלהם.

צריך לפתור בעיות כמו:

Visual consistency.

Brand consistency.

Character consistency.

Story coherence.

UX quality.

Typography.

Spacing.

Composition.

Lighting.

Pacing.

Voice identity.

Music identity.

Cross-modal consistency.

אם משתמש יוצר דמות ואז משתמש בה בתמונה, וידאו, משחק ו־3D — היא צריכה להישאר אותה דמות.

אם נוצר Brand, האתר, האפליקציה, הפרסומת וה־Agent צריכים להרגיש כמו אותו מותג.

תציע את הארכיטקטורה הנכונה לזה.

Product Memory / Creative DNA

אני חושב שלכל מוצר צריך להיות Persistent Product DNA.

אבל אני רוצה שתגדיר מה באמת צריך להיכלל בו ומה לא.

לדוגמה:

Brand rules.

Characters.

Voices.

Visual style.

Architecture conventions.

Data semantics.

User personas.

Tone.

Product decisions.

World/story rules.

Reusable assets.

אני לא רוצה Memory ענק ולא יעיל.

אני רוצה Compact Structured Memory שמונע regeneration ושומר consistency.

תציע איך נכון לבנות זאת.

Whole-DAG Optimization

אחת הדרישות החשובות ביותר:

אין לבצע Optimization של כל Task כאילו הוא מבודד.

לפעמים Model יקר יותר בתחילת התהליך חוסך הרבה retries ותיקונים אחר כך.

לכן אני רוצה שהמערכת תחשוב גם ברמת כל המוצר.

השאלה המרכזית:

איפה הדולר הבא שאנחנו מוציאים נותן את העלייה הגדולה ביותר באיכות הסופית?

הצעתי להשתמש במדד כגון:

Marginal Quality Gain Per Dollar.

אני רוצה שתבדוק האם זו פונקציית Optimization מספקת, או שצריך מודל טוב יותר שמשקלל:

Quality.

Probability of success.

Cost.

Latency.

Failure cost.

Repair cost.

Future DAG cost.

User tier.

Business margin.

Deadline.

Criticality.

אם צריך Multi-objective Optimization — תציע אותו.

Candidate Search

אני לא רוצה Ensemble Everywhere.

זה יקר.

אבל במשימות עם leverage גבוה אולי כדאי לייצר כמה Candidates.

לדוגמה:

Logo.

Hero section.

Architecture.

Character design.

Story concept.

Important video shots.

Core game mechanic.

אפשר למשל:

Generate several cheap candidates → cheap ranking → expensive verification only on finalists.

אני רוצה שתגדיר:

מתי Candidate Search כלכלי.

כמה Candidates.

איך לבחור Judge.

איך למנוע Judge Bias.

איך לחשב Expected Value של Candidate Search.

Verification

Verification היא חובה.

אבל אני רוצה שכמה שיותר Verification יהיה דטרמיניסטי ולא AI כשאפשר.

לדוגמה בקוד:

Compiler.

Tests.

Linters.

Security scanners.

Runtime checks.

Browser tests.

API tests.

רק במקומות שבהם אין בדיקה דטרמיניסטית מספקת להשתמש ב־AI Judge.

ב־Media:

Prompt match.

Artifact detection.

Continuity.

Audio sync.

Style consistency.

Composition.

Brand consistency.

ב־Agents:

Task success.

Tool accuracy.

Hallucination.

Safety.

Cost.

Latency.

אני רוצה Universal Verification Framework עם Verifiers ספציפיים לכל Product Family.

אבל תציע אתה איך נכון לבנות אותו.

Retry / Repair / Escalation

אני רוצה שהמערכת תבחין בין:

Retry.

Repair.

Regenerate.

Escalate.

Fallback.

Fail.

היא לא צריכה לנסות שוב אוטומטית בלי להבין את סוג הכשל.

Retry מתאים לכשל transient.

Repair מתאים כאשר רוב התוצר טוב והפגם מקומי.

Regenerate כאשר התוצר כולו גרוע.

Escalate כאשר נדרשת יכולת חזקה יותר.

Fallback כאשר Provider נכשל אבל Capability מתאימה.

Fail כאשר אין דרך כלכלית או טכנית להמשיך.

אני רוצה ממך להגדיר State Machine ברורה לזה.

Provider Intelligence

כל Provider/Model צריך לקבל performance profile אמיתי.

לא “Claude טוב בקוד”.

אלא מידע אמיתי שלנו.

לדוגמה:

Task type.

Quality score.

Success rate.

First-pass success.

Repair rate.

Retry rate.

Actual cost.

P90 cost.

Latency.

Provider failures.

Context size.

Verifier acceptance.

Final product contribution.

אני רוצה שה־Router ישתמש בנתונים האלה.

אבל צריך Cold Start strategy כשאין לנו מספיק Data.

אני רוצה ממך להציע אותה.

למשל:

Benchmark prior.

Static capability profiles.

Small controlled exploration.

Gradual exploitation.

Confidence intervals.

Minimum sample sizes.

אני לא רוצה שהמערכת תלמד שטויות ממדגם של שלוש בקשות.

Learning Flywheel

כל Build צריך להפוך את המערכת לחכמה יותר.

אבל אני לא רוצה “למידה” לא מבוקרת שמקלקלת Production.

תציע Architecture שבה:

Raw telemetry נשמרת.

Evaluation נשמר.

Routing decisions נשמרים.

Model/Provider version נשמר.

Prompt version נשמר.

Policy version נשמר.

User feedback נשמר.

אבל Production Policy מתעדכנת רק דרך Controlled Promotion.

אני רוצה אפשרות להשוות:

Policy A מול Policy B.

Provider Mix A מול B.

Prompt Version A מול B.

ואז לבצע Promote/Rollback.

Reuse Engine

אני חושב שזה יכול להיות אחד ממנועי הרווח הגדולים שלנו.

אם כבר יש לנו Component מאומת, אין סיבה ליצור אותו מחדש.

למשל:

Auth.

Payments.

CRUD.

Database patterns.

UI elements.

Agents.

Tool adapters.

Workflow primitives.

Video transitions.

Styles.

Tests.

אבל צריך להיזהר שלא נהפוך את המערכת ל־Template Factory.

אני עדיין רוצה מוצרים מותאמים אישית.

תציע דרך נכונה להבדיל בין:

Reusable verified primitives

לבין

Unique product generation.

Caching

אני רוצה Context Caching ו־Artifact Caching אגרסיביים איפה שזה בטוח.

אבל לא במחיר stale context או cross-tenant leakage.

תגדיר:

מה ניתן לשתף גלובלית.

מה ניתן לשתף רק בתוך Project.

מה ניתן לשתף רק בתוך Tenant.

מה אסור לשמור.

מתי Cache invalidated.

Profit Governor

זה Non-Negotiable.

Profitability היא Runtime Constraint.

אנחנו לא מריצים ביודעין Build עם Unit Economics שליליים.

לפני פעולה יקרה צריך לדעת:

Maximum authorized cost.

Expected cost.

Customer revenue allocated.

Risk reserve.

Required contribution.

Minimum margin.

המערכת צריכה לאשר פעולה רק אם היא עומדת במדיניות הרווח.

אבל אני רוצה שתאתגר את הנוסחה.

האם נכון להשתמש ב:

Revenue Reserved > Maximum Authorized Cost + Risk Reserve + Required Contribution

או שיש מודל פיננסי טוב יותר?

צריך לקחת בחשבון:

Provider uncertainty.

Refund probability.

Chargeback risk.

Payment processing.

Infrastructure.

Storage.

Egress.

Support burden.

Free tier subsidy.

Promotional credits.

Enterprise contracts.

אני רוצה Unit Economics אמיתי, לא רק AI token economics.

Quality Tiers

אני חושב שנכון ליצור Tiering:

Fast.

Standard.

Pro.

Studio.

Cinematic.

Enterprise.

אבל אל תיישם את השמות האלה עדיין כחוק.

תבדוק האם Product Tiers הם הדרך הנכונה, או שעדיף:

Budget modes.

Quality targets.

Service profiles.

Dynamic quoting.

אולי שילוב.

המטרה היא:

משתמש שלא צריך Cinematic Quality לא צריך לגרום לנו לשלם Cinematic Costs.

Stop-Loss

חובה.

לכל Build ולכל Task חייבים להיות:

Hard budget.

Max retries.

Max repairs.

Max escalations.

Deadline.

Minimum ROI for another attempt.

אם Expected Value של ניסיון נוסף שלילי — מפסיקים.

אבל תציע אתה את המודל המתמטי וה־Policy הנכון.

Business Moat

אני רוצה שהיתרון שלנו לאורך זמן יהיה:

Data + Orchestration + Evaluation + Provider Intelligence + Reusable Assets + Product Memory.

לא API keys.

לא Prompt אחד.

לא Provider אחד.

אני רוצה שככל שיש לנו יותר שימוש:

האיכות עולה.

העלות הממוצעת יורדת.

ה־Routing משתפר.

ה־Repair יורד.

ה־Reuse עולה.

וה־Margin עולה.

אני רוצה שתבחן האם יש עוד Data Moats או Feedback Loops שאנחנו מפספסים.

מה לא לעשות עכשיו

חשוב מאוד:

אל תעצור את Golden E2E #1 כדי לבנות עכשיו את כל החזון הזה.

כרגע יש לנו יעד מיידי:

להוכיח Web/SaaS אמיתי מקצה לקצה.

User → Login → Project → Prompt → Plan → Quote → Reserve → Queue → Worker → AI Provider → Generated Files → Build → Verification → Artifact → Preview → Modification → Version → ZIP.

קודם צריך לגרום לזה לעבוד אמיתי.

הארכיטקטורה שאנחנו בונים עכשיו רק צריכה לא לחסום את החזון העתידי.

אני לא רוצה premature architecture שמאריך בחודשים את ההגעה למוצר עובד.

אני רוצה ממך לפני מימוש גדול

לפני שאתה מתחיל לבנות את השכבות החדשות, אני רוצה ממך Architecture Review משלך.

אני רוצה שתכתוב:

1. מה מתוך החזון הזה אתה מסכים איתו.
2. איפה אתה חושב שאני טועה.
3. מה Overengineered.
4. מה חסר.
5. איזה רכיבים צריך לשלב.
6. איזה רכיבים צריך לפצל.
7. מה צריך לבנות עכשיו.
8. מה צריך לבנות אחרי Golden E2E.
9. מה צריך לחכות עד שיש Data אמיתי.
10. איזה Design היית בוחר אילו היית CTO של 148AI.
11. אילו Failure Modes אתה רואה שאנחנו עדיין לא מכסים.
12. איך היית שומר על המערכת פשוטה למרות החזון הרחב.
13. איך היית שומר על Profitability ככל שאנחנו מוסיפים מודלים וספקים.
14. איך היית הופך את Learning Flywheel ל־Moat אמיתי.
15. מה לדעתך יכול להפוך את 148AI למוצר שקשה מאוד למתחרים להעתיק.

אל תסכים איתי אוטומטית.

אם רעיון חלש — תגיד.

אם יש פתרון טוב יותר — תציע.

אם דרישה מסוימת טובה לטווח הארוך אבל מסוכנת עכשיו — תסביר ותדחה אותה לשלב מתאים.

ואחרי ה־Architecture Review, אני רוצה שנקבע יחד את ה־Target Architecture ואת ה־Execution Plan.

Non-Negotiable Principles

יש כמה דברים שאינם נתונים לוויתור:

1. REAL EXECUTION OR EXPLICIT FAILURE.
2. אין Fake Build.
3. אין Fake Provider Success.
4. אין Estimated Cost שמתחפש ל־Actual Cost.
5. אין Provider Call בתשלום ללא Budget Authorization.
6. אין Build שמאושר ביודעין עם Unit Economics שליליים.
7. Verification לפני Delivery.
8. Durable State בכל מסלול מסחרי.
9. Tenant Isolation.
10. Secrets אינם מופיעים ב־DB, logs, artifacts או API responses.
11. כל PASS משמעותי חייב Evidence.
12. המערכת חייבת להישאר Provider-Neutral.
13. Product Architecture לא תהיה תלויה במודל AI יחיד.
14. Preview Success אינו Production Success.
15. Build Success אינו Functional Acceptance.
16. אין לשכתב רכיב שעובד בלי הוכחה שהשכתוב נחוץ.
17. קודם למצוא את המעבר שנכשל, אחר כך לתקן אותו.
18. Profitability היא Constraint של המערכת, לא דוח בדיעבד.

היעד

אם נעשה את זה נכון, המשתמש לא יצטרך לדעת איזה מודל לבחור.

הוא לא צריך לדעת אם Claude, Gemini, OpenAI, מודל Open Source, Replicate או Provider אחר ביצעו חלק מהעבודה.

הוא צריך לומר:

“אני רוצה שזה יהיה קיים.”

148AI צריכה להחליט:

מה צריך לבנות.

איך לפרק את זה.

מי צריך לבצע כל חלק.

כמה כדאי לשלם.

מתי צריך מודל נוסף.

מתי כדאי Repair.

מתי צריך Escalation.

מתי לעצור.

איך לבדוק.

איך לחבר את הכל.

ואיך לספק מוצר סופי מעולה תוך שמירה על Profit Margin.

אני לא רוצה ממך רק לבצע את המסמך הזה.

אני רוצה שתעזור לנו להפוך אותו לארכיטקטורה הטובה ביותר שאפשר לבנות.

תחשוב על עצמך כחלק מצוות הארכיטקטורה של 148AI.

המטרה היא לא להוכיח שאני צדקתי.

המטרה היא לבנות את המערכת הנכונה.