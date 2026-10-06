# החלטות מייסד — 2026-10-07 (אחרי ה־Architecture Review)

מקור: הודעת המייסד מ־2026-10-07 01:35. מחייב יחד עם `OPERATING_CONTRACT_HE.md`.

1. **Product Orchestrator** — Owner לוגי יחיד לכל Build (לא בהכרח LLM, לא בהכרח process יחיד). כל שינוי מהותי: Orchestrator → Decision Layer → Economics Gate → Updated Plan → Execution.
2. **Decision Layer** מאושר: deterministic, versioned, auditable, replayable, explainable. כל החלטה משאירה Evidence: נבחר, חלופות, מחירים, Policy, Budget, איכות נדרשת, סיבה, החלופה הבאה.
3. בחירה **ברמת Task**; אין חובה למודל אחד או לכמה.
4. **Free Provider Lane**: FREE_CAPABLE → ECONOMY → QUALITY → PREMIUM. Free הוא Provider Metadata (quota, rate limits, privacy/data-use, availability, version, reliability, capabilities, metered cost) — הזדמנות, לא תלות. מועמדים לבדיקה: Groq, Cloudflare Workers AI, OpenRouter free pool, Gemini Free Tier.
5. המדד: **Cost per Verified Successful Outcome**.
6. **Cost Truth**: `metered_cost` (usage × catalog price בגרסה), `provider_reported_cost`, `reconciled_cost` (מקור אמת פיננסי). metered אינו Final Actual.
7. **Profitability**: שני תנאים. Target Contribution ≈70% על Expected, Hard Minimum Contribution ≈10–15% על Maximum — **Policy Parameters לפי Product Family/Budget Profile, לא קבועים**. לבחון בהמשך Expected/P95/P99/Hard Max.
8. **Golden E2E רץ על Internal QA / Staging Budget** עם Hard Cap מפורש — לא על Customer Free Tier. Free Tier ללקוחות ייקבע אחר כך (העדפה: one-time taste / micro-build, לא סבסוד חודשי).
9. **Telemetry עכשיו** — רשימת השדות לכל Attempt (migration 027; מוני retry/repair/regenerate/escalation/fallback ב־migration 028).
10. Provider Intelligence — סטטי עכשיו; למידה אחרי מדגם. ספים (30 תצפיות, 5% exploration) הם Policy Parameters.
11. **Style & Identity System** במקום Creative Director Agent; LLM/Vision Judge רק לטעם/שיפוט.
12. Verification: Deterministic First; Acceptance מה־IR/Build Contract; Generator ≠ Reviewer כשנדרש.
13. Reuse של Verified Primitives למה שאינו מבדל; יצירה מחדש למה שמבדל. לא Template Builder.
14. **Failure Signature → Proven Fix** כנכס רשמי: קודם תיקון דטרמיניסטי מוכח, ורק אז AI Repair.
15. Caching content-addressed **עם Revocation** (מחיקת משתמש/פרויקט, revoke, legal takedown). Cache key כולל scope, input hash, model, prompt, policy, DNA ו־primitive versions.
16–18. **Golden E2E #1 הוא Priority #1.** מותר במקביל רק Instrumentation: Attempt Ledger, task tagging, cost truth, verification taxonomy, basic stop-loss, versions, routing evidence, traceability, Internal QA Budget.
19. החזון נשאר אוניברסלי; אסור לנעול ל־Request → One Model → Website.
22. החלטה ארכיטקטונית שמתגלה כשגויה — מציגים בעיה, Evidence, חלופה והשפעה, ומחליטים יחד. לא עוקפים בשקט.

## החלטות המייסד — 2026-10-07 (תשובות לשאלות ה־CTO)

23. **תקרות Internal QA**: ‎$0.50 לבנייה, ‎$10 סה"כ. Policy Parameters (`OMNI_QA_BUILD_MAX_USD`, `OMNI_QA_BUDGET_TOTAL_USD`), לא קבועים בקוד.
24. **חשבון QA**: כרגע `shayfly84@gmail.com`, דרך **Entitlement מפורש `INTERNAL_QA` ב־scope `staging`** הקשור לחשבון (account id), ניתן ונשלל באופן מתועד. התקציב **אינו** קשור למסלול הלקוח או ל־Free Plan: נספרות רק הזמנות שמומנו כ־`internal_qa`.
25. **תלויות בקוד שנוצר (Golden E2E #1)**: sandbox image עם **allowlist קטן של dependencies מאושרים מראש ונעולים בגרסה**. תלות שאינה ברשימה מחזירה `UNSUPPORTED_DEPENDENCY` — כשל מפורש. אין Package Proxy ואין התקנה חופשית עכשיו. אחרי Golden E2E: controlled package installation (registry/proxy, lockfiles, allow/deny policy, vulnerability scanning, supply-chain controls).

## החלטת תמחור (כיוון, לא מספרים סופיים) — 2026-10-07 01:59

26. מחירי בדיקה: **Pro ‎$25/חודש, Business ‎$100/חודש** — לא מחירי Launch.
    * אין Unlimited Provider Spend. מנוי = Customer Credits / Usage Entitlement, שהמערכת מתרגמת מאחורי הקלעים ל־Authorized Cost.
    * **אין יחס קבוע ופומבי `1 credit = $X provider cost`.** Credits = ערך ללקוח; Provider Cost = מדד פנימי. חיסכון בעלות מגדיל Margin ולא מוזיל אוטומטית.
    * Target ≈70% / Hard Minimum ≈10–15% — Versioned Policy Parameters לפי Product Family / Service Profile. בהמשך: Expected / P95 / P99 / Hard Max.
    * Free/near-free = שכבת אופטימיזציה, לא תנאי לרווחיות. המוצר רווחי גם אם Free Tier של ספק נעלם.
    * Heavy media (וידאו, 3D, compute ארוך): multipliers גבוהים או add-on / pay-as-you-go, מאחורי Economics Gate.
    * Business = מוצר עסקי (צוות, הרשאות, היסטוריה, DNA, רכיבים פרטיים, פריסות, אנליטיקה, אינטגרציות, עדיפות), לא רק יותר Tokens.
    * Add-on Credit Packs — הארכיטקטורה חייבת לאפשר.
    * **לא לקבוע עדיין**: Credits ב־Pro/Business, מחיר Credit Pack, multipliers, seats, Free-tier subsidy — רק אחרי Cost Truth אמיתי.
    * **לא לפתוח Workstream תמחור.** רק לוודא ש־Golden E2E וה־Ledger לא נועלים אותנו לשימוש בלתי מוגבל.

### בדיקת תאימות של הקוד הקיים (CTO, 2026-10-07)

* **אין נעילה לשימוש בלתי מוגבל — מאומת בקוד**: לכל תוכנית `included_credits` ותקרת עלות ספק חודשית פנימית לחשבון (`paid_provider_budget_usd`, ניתנת להגדרה ב־env); כל Build מוזמן מראש במלוא העלות המקסימלית (`credit_reservations`); שער Margin לפני ביצוע; אישור לכל קריאה; ה־worker מוגבל לסכום שהוזמן; overage = hard stop. Credits ועלות ספק נשמרים בעמודות נפרדות — אין המרה קבועה ביניהם בקוד.
* **קיים**: subscription allowance, internal cost budget לחשבון/מחזור, provider reservations, per-build ו־per-call authorization, cost classes (zero…extreme) לפי תוכנית, usage metering (Attempt Ledger), שכבות עלות כולל עמודת reconciled.
* **חסר (לשלב התמחור, לא עכשיו)**: credit balance / add-on packs (יש רק credits חודשיים); multipliers לפי capability (כרגע 60 credits קבועים לכל build); Margin Policy versioned לפי Product Family עם שני התנאים (כרגע פרמטר גלובלי אחד `OMNI_MIN_BUILD_VARIABLE_MARGIN` על ה־Maximum); Expected/P95/P99; תהליך reconciliation.
* **סתירה שנמצאה — ממתינה להחלטה**: ה־endpoint הציבורי (ללא התחברות) `/api/v28/pricing` מחזיר לכל תוכנית `paid_provider_budget_usd` ו־`variable_margin_floor` לצד `included_credits` (למשל Pro: 4000 credits מול ‎$10 עלות ספק) — בדיוק היחס הפומבי credit→עלות וה־Margin שלנו. גם ה־snapshot של החשבון מחזיר ללקוח `provider_spend_usd` / `provider_budget_remaining_usd`. ה־UI לא משתמש בשדות האלה.
* ברירות המחדל בקוד הן Pro ‎$39 / Business ‎$99; מחירי הבדיקה ניתנים להגדרה ב־env (`OMNI_PRICE_PRO_USD`, `OMNI_PRICE_BUSINESS_USD`) בלי שינוי קוד.

## שאלה פתוחה לרמת ארכיטקטורה (סעיף 22) — תשתית מנוהלת מול Golden E2E #1

**הבעיה.** כל Build Contract של Web/SaaS דורש היום, בלי תלות בפרומפט, 5 סוגי תשתית `PLATFORM_MANAGED` לכל מוצר: database, auth_session, object_storage, scheduled_http, outbound (`ProductArchitect._infrastructure_requirements`). ה־worker מסרב להתחיל ייצור קוד עד שכל ה־5 LIVE.

**למה זו בעיה.**
1. ‏Plan → Quote נכשל כבר עכשיו ב־Preview: `OMNI_GENAPP_PROVISIONING_MAXIMUM_USD` חסר, ולכן אף סוג תשתית אינו מתומחר → 402 `cost_quote_unknown`. הוכח עם `tools/golden_e2e_quote_probe.py`.
2. גם אם נתמחר, ההחלטה #25 קובעת שקוד האפליקציה משתמש בספריה הסטנדרטית בלבד. אין לו driver ל־Postgres או ל־S3, כך שהתשתית שתוקצה לא תשמש את המוצר. זו תשתית "על הנייר".
3. אף אחד מחמשת ה־provisioners לא אומת אי־פעם live. זה מוסיף 5 מעברים לא מאומתים לפני Real AI Provider, ואינם ברשימת המעברים של Golden E2E.

**חלופות.**
* **א. Self-contained profile ל־Golden E2E #1 (המלצת CTO).** פרופיל תשתית versioned `self_contained_v1`: SQLite מוטמע, sessions בתוך האפליקציה, קבצים מקומיים; scheduled/outbound לא נדרשים ומדווחים NOT VERIFIED. ה־Quote כולל מודל + תמונה (אם נשארת) + retry. לא נדרשים חשבונות חיצוניים חדשים. מוכיח את כל השרשרת Login→…→ZIP עם AI, build, tests, preview וגרסאות אמיתיים. התשתית המנוהלת הופכת ל־Golden E2E #2 עם allowlist של drivers בשני ה־images.
* **ב. רק להגדיר `OMNI_GENAPP_PROVISIONING_MAXIMUM_USD`.** תיקון קונפיגורציה של דקות. הכשל זז ל־worker (5 provisioners לא מאומתים), ומוקצית תשתית שהאפליקציה לא יכולה להשתמש בה. לא מומלץ לבד.
* **ג. מסלול מנוהל מלא עכשיו.** מוסיפים drivers (`psycopg`, `boto3`) ל־allowlist, image preview מותאם עם אותם pins ורשת ל־Neon, ואימות live של 5 ה־provisioners. נאמנות מלאה לחוזה, אבל הכי יקר ואיטי, ומרחיב scope לפני Golden E2E ראשון.

**השפעה.** א' מקצרת את הדרך ל־VERIFIED ושומרת על הבטחת "אין Fake". ג' מוסיפה ימים ותלות חיצונית. ב' מזיזה את הבעיה.

### החלטות המייסד על השאלה הפתוחה — 2026-10-07

27. **Golden E2E #1 = פרופיל `self_contained_v1`.** Self-contained אינו Fake:
    * SQLite / persistence מקומית ו־Sessions מותרים **רק** אם הם אמיתיים, עובדים ונבדקים. רק אז הם נחשבים VERIFIED.
    * Email / Scheduler מחוץ ל־acceptance scope של #1 ונשארים NOT_VERIFIED / NOT_CONFIGURED. אסור להציג אותם כחלק מ־#1 שעבר.
    * אין Fake Provider Success ואין Fake Infrastructure Success. לא בונים עכשיו את 5 ה־managed provisioners.
    * Golden E2E #2 יסגור את פרופיל ה־Managed Infrastructure האמיתי.
28. **Image Generation אינה חובה גלובלית.**
    * היא Capability שמופעלת רק כש־Product IR / Build Contract דורש אותה.
    * כשאינה נדרשת, ברמת ה־Build היא `NOT_REQUIRED` — לא FAIL ולא Fake PASS.
    * ב־Capability Registry, Replicate/Image נשארים NOT_VERIFIED / PARTIAL עד E2E נפרד (Image task → budget → real Replicate → image → R2 → artifact → verification → preview). אין placeholder כתמונה שנוצרה.
    * Golden E2E #1 משתמש במוצר בדיקה שאינו דורש תמונה.
    * היכולת נשארת בארכיטקטורה.
29. **`/api/v28/pricing` הציבורי מחזיר רק מידע Customer-Facing**: שם תוכנית, מחיר, credits/allowance, features, seats, limits, add-ons, usage.
    * כל שדה Unit Economics פנימי (provider budget, expected/hard cost, margins, subsidy, QA budget, markup, credit valuation) לא מופיע בו.
    * Admin/Finance יקבל בעתיד endpoint נפרד עם הרשאות.
    * Test קבוע מוודא זאת.

### יישום (2026-10-07)
* #27 יושם כפרופיל `self_contained_web_v1` שנקשר לחוזה. הפרופיל נבחר ב־`OMNI_BUILD_INFRA_PROFILE` (Policy Parameter), שהוגדר ב־Vercel Preview בלבד.
* #28 יושם: בקשת תמונה רק בכוונה מפורשת (לוגו/מיתוג/hero/איור), ומשחקים לפי דרישותיהם. אחרת, ב־evidence מופיע `NOT_REQUIRED`.
* #29 יושם עם test קבוע.
* **ממצא פתוח להחלטה:** סטטוס הבנייה (`evidence`) ותצוגת התוכנית (`economics`) עדיין מחזירים ללקוח נתוני Economics פנימיים.
