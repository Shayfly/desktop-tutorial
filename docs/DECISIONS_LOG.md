# DECISIONS_LOG — יומן הכרעות

כל שורה מציינת **מי** הכריע, **מקור** ההכרעה, ו**איפה** היא ממומשת או מתועדת. ההכרעות הקודמות נמצאות ב-`docs/DECISIONS_2026-10-07_HE.md`.

**מקור "צ'אט":** הנחיות שהמייסד מסר ל-Claude Code בצ'אט, בשעון Asia/Jerusalem. לכמה מהן יש ראיה עמידה בריפו: תגובה על PR שפורסמה בשם הבעלים, עם השורה "נכתב ע"י Claude Code בשם הבעלים." **ההכרעות האלה לא אומתו באופן עצמאי.**

## 2026-10-19 — הכרעות CEO

| # | הכרעה | מקור | מימוש / תיעוד |
|---|---|---|---|
| 1 | Claude אחראי על `tests/**` ו-`docs/**`, ולא נוגע ב-`omni_prod/**` בלי אישור חריג. עובד בתור משלו ולא ממתין ל-Copilot או לאימות | צ'אט 00:24, 00:34 | — |
| 2 | חוזה סינון הסודות ב-`_repo_summary` (`is_sensitive_path`) נעול. ההכרעה לגבי `config.json` הושארה ל-Claude | צ'אט 00:34, 00:44 | PR #47 (אדום עד מימוש) |
| 3 | 13 נתיבים ציבוריים הוכרעו: 6 נתיבי `/api/v28/auth/*`, ‏`launch/readiness`, ‏`/_omni/metrics`, ‏`/api/source/*` (410), ‏`/api/v28/source/client/*`, ‏`/api/status`, ‏`/api/v28/deployment` | צ'אט 00:48, 00:52; [תגובה על #48](https://github.com/Shayfly/desktop-tutorial/pull/48#issuecomment-6256005877) | `docs/PUBLIC_ROUTES.md` (#48) |
| 4 | host של DB אינו סודי. גם ה-fingerprint אינו סודי | צ'אט 00:52; [תגובה על #49](https://github.com/Shayfly/desktop-tutorial/pull/49#issuecomment-6256006017) | `docs/DB_TARGETS.md` (#49), ‏`docs/SECRETS_POLICY.md` (#51) |
| 5 | ביטול הסשנים שדלפו ב-`ba2bb23`: "התקבל" | צ'אט 00:52 | #51. **האירוע נשאר פתוח עד שיהיה probe או ראיה מה-DB** |
| 6 | מחירון: Free $0 / Amateur $29 / Pro $99 / Studio $299. המחיר השנתי שווה ל-10 חודשים, כלומר חודשיים חינם | צ'אט 01:10; [תגובה על #55](https://github.com/Shayfly/desktop-tutorial/pull/55#issuecomment-6256006199) | `omni_prod/pricing.py` (#59), ‏`docs/PLANS.md` (#55) |
| 7 | Amateur ו-Pro בקרדיטים מוגבלים. Enterprise נשאר בחוזה ולא מוסר | צ'אט 01:22; תגובה על #55 | #55, ‏#59 |
| 8 | מיפוי שמות: Basic→Amateur, ‏Business→Studio | צ'אט 01:22, 01:48 | #55, ‏#59 |
| 9 | מרווחים סופיים: Amateur 86.8%, ‏Pro 72.4%, ‏Studio 58%. ההנחות שמאחוריהם לא נמסרו | צ'אט 01:22 | `docs/PRICING.md` (#56) |
| 10 | פרסום `PRICING.md` (פנימי) בריפו הציבורי | צ'אט 01:22; [תגובה על #56](https://github.com/Shayfly/desktop-tutorial/pull/56#issuecomment-6256153156) | #56 |
| 11 | [תגובה על #54](https://github.com/Shayfly/desktop-tutorial/pull/54#issuecomment-6256033733) ("המסמך פנימי"). **הערה:** #54 הוא MODEL_PRICES, והתוכן מתאים ל-#56. ההכרעה הייתה להשאיר את התגובה כפי שהיא | צ'אט 01:34, 01:48 | — |
| 12 | cost classes: ‏Amateur ‏ZERO+LIGHT · Pro עד STANDARD · Studio הכול | צ'אט 01:37, 01:48 | `pricing.py` (#59); טסט: `tests/test_amateur_cost_class_lock.py` |
| 13 | נתיב הבנייה של M5 בוחר class לפי התוכנית: Amateur→LIGHT · Pro→STANDARD · Studio→HEAVY. ‏`reserve` לא יחסום בנייה לגיטימית | צ'אט 01:55 | `pricing.M5_BUILD_COST_CLASS`, ‏`investor_app.py:~2269` (#59); טסט: `tests/test_m5_plan_build_class.py` |
| 14 | תמיכה לאחור ב-env: גם `OMNI_PRICE_BASIC_*` / `OMNI_PRICE_BUSINESS_*` נקראים, ובנוסף לשמות החדשים | צ'אט 01:55 | `pricing._env_decimal_renamed` (#59) |
| 15 | הקוד ממשיך לפנות ל-Gemini דרך Google, ומחירי Google נשארים. Venice נוסף כ-provider נפרד, עם מזהי המודלים שלו | צ'אט 01:48 | `prices.py` (#60) |
| 16 | מפתח החיפוש של מחירים יהיה `(provider, model)`. Claude דרך Venice נוסף בלי לשבור את `anthropic` | צ'אט 01:55 | `prices.py` וכל הקוראים (#60); טסטי collision |
| 17 | אסור שספק מחובר יפעל בלי רשומת מחיר. ל-Replicate ‏flux-schnell נוספה שורה | צ'אט 01:55 | `prices.py` (#60); שמירה: `test_every_connection_tested_model_has_a_price_row` |
| 18 | אישורי חריגה ל-`omni_prod`: קודם `pricing.py` בלבד (01:48), ואחר כך גם `investor_app.py` בשורה 2269 ובסביבתה (01:55). ‏`prices.py` לפי סעיף 2 ב-01:48 | צ'אט | #59, ‏#60 |

### מיפוי cost class (הוכרע 02:05–02:16; מחליף את הכרעה 13 ואת בחירות C2/C3)

ה-class של בנייה קובע שלושה דברים בפועל: (א) allowlist של מודלים, (ב) תקרת תקציב לבנייה, (ג) קרדיטים. מימוש: #59 (`633158b`).

| # | הכרעה | ערך | מימוש |
|---|---|---|---|
| 19 | class לכל תוכנית (בלי ברירת מחדל STANDARD) | Free→LIGHT · Amateur→LIGHT · Pro→STANDARD · Studio→HEAVY · Enterprise→EXTREME | `pricing.M5_BUILD_COST_CLASS` |
| 20 | קרדיטים לבנייה לפי class | ZERO 20 · LIGHT 45 · STANDARD 200 · ADVANCED 300 · HEAVY 500 · EXTREME 1200 | `M5_CLASS_BUILD_CREDITS`; ב-reserve, ב-approval וב-preview |
| 21 | קרדיטים לתוכנית | Free 150 · Amateur 1000 · Pro 4500 · Studio 10000 | `PLAN_CATALOG` |
| 22 | Free | ZERO + LIGHT, 150 קרדיטים (כ-3 בנייות בחודש) | `PLAN_CATALOG` |
| 23 | Enterprise | EXTREME, פטור מרצפת המרווח (תמחור בחוזה) | `MARGIN_FLOOR_EXEMPT_PLANS` |
| 24 | תקרת תקציב מודלים לבנייה, **soft cap** (לא דוחה בנייה, רק רושם חריגה) | ZERO $0.05 · LIGHT $0.35 · STANDARD $1.60 · ADVANCED $3.00 · HEAVY $5.50 · EXTREME $18.00. לכל class יש משתנה env נפרד: `OMNI_BUILD_LLM_CAP_<CLASS>_USD` | `m5_class_llm_cap`, ‏`m5_llm_budget` |
| 25 | חריגה של יותר מפי 2 מהתקרה | התרעה בלוג (`LLM_SPEND_ALERT`) | `pricing.llm_overage`, ‏`worker_tasks.llm_cap_overage` |
| 26 | רצפת 60% לא יורדת. אם תקרה שוברת את הרצפה, התקציב נחתך לגובה הרצפה (אפשרות 1) | — | `m5_llm_budget` |
| 27 | יעד מרווח במקרה הגרוע (כל התקרה מנוצלת) | Amateur 72% · Pro 63% · Studio 62% | מושג: 73.2% / 63.6% / 63.2% |
| 28 | טסט חובה ב-CI: אותה משימה עולה פחות ב-Amateur מאשר ב-Studio, והמרווח נשמר בשלושת ה-tiers | — | `tests/test_m5_plan_build_class.py::SameTaskTierTests` |

**~~allowlist (בחירה של Claude, כלל מחיר)~~ (הוחלף בהכרעה 31):** מקסימום מחיר output ל-1M טוקנים: ZERO ‏$0 · LIGHT ‏$1.50 · STANDARD ‏$10 · ADVANCED/HEAVY/EXTREME ללא תקרה. אלה אותם ספים שמופיעים ב-`docs/MODEL_PRICES.md`. עם ה-catalog הנוכחי:
- ל-LIGHT נשארים `gemini-3-1-flash-lite` ו-`openai-gpt-6-luna`.
- STANDARD ומעלה מקבלים את כל 6 המודלים, כך שבין Pro ל-Studio אין כרגע הבדל ב-allowlist, רק בתקציב ובקרדיטים.

**~~בעיה פתוחה, Free~~ (נפתרה בהכרעה 29):** ל-Free אין הכנסה, והרצפה חלה עליו (רק Enterprise פטור). לכן תקציב המודלים שלו הוא **$0**: בנייה של Free יכולה לרוץ רק על מסלולים בעלות אפסית. כדי לתת ל-Free ‏3 בנייות LIGHT בתשלום (עד $0.35 לבנייה, כלומר עד $1.05 למשתמש בחודש), צריך לפטור גם את Free מהרצפה. **זו הכרעה שעוד לא התקבלה.**

**פער שקיבל הכרעה:** בתשובה הראשונה נכתב "Free 300", ובשנייה "Free 150 (= 3 בנייות)". נבחר 150, וזה אושר בהודעה של 02:16.

### תיקונים (הוכרע 02:22; מחליף חלקים מהכרעות 19–28)

מימוש: #59 (`d8b3a8c`, ‏`f8006fe`).

| # | הכרעה | ערך | מימוש / טסט |
|---|---|---|---|
| 29 | **Free פטור מרצפת המרווח**, כמו Enterprise. התקרה של LIGHT ($0.35) נשארת | Free יכול לבצע בנייה בתשלום עד $0.35 | `MARGIN_FLOOR_EXEMPT_PLANS`; טסט `test_free_can_run_a_paid_build_up_to_the_light_cap` |
| 30 | **תקציב ה-class הוא הקובע ב-worker.** ה-env הוא תקרה עולמית בלבד: כשהוא נמוך מתקציב ה-class נרשמת התרעה ב-log, ואין חסימה שקטה | `WORKER_BUDGET_BELOW_CLASS` (WARNING) | `routed_gateway.bind_budget`; טסט `test_pro_keeps_its_class_budget_when_worker_env_is_lower` (env ‏$0.50, ‏Pro מקבל $1.60) |
| 31 | **ספי allowlist** (מחיר output מקסימלי ל-1M טוקנים) | LIGHT ≤ $1.50 · STANDARD ≤ $5 · ADVANCED ≤ $8 · HEAVY ו-EXTREME ללא תקרה · ZERO ‏$0 | `M5_CLASS_MAX_OUTPUT_PER_MILLION`; טסט `test_pro_and_studio_get_different_allowlists` |
| 32 | הצ'אט של ה-intake מציג את הקרדיטים של ה-class (במקום 60 קבוע) | — | `investor_app._supervisor`; טסט `tests/test_intake_credits_by_plan.py` |

**ל-#31:** בהתחלה הוצע LIGHT ≤ $1. בסף כזה היה נשאר ל-Amateur ול-Free רק `gpt-6-luna`, שמסומן `INSUFFICIENT_CREDIT` ‏(אין קרדיט ב-OpenAI) ו-`UNVERIFIED`. התוצאה הייתה שכל בנייה שלהם נכשלת. לכן הוכרע LIGHT ≤ $1.50.

**allowlist בפועל (catalog נוכחי):**
- **Amateur ו-Free** (LIGHT): `gemini-3-1-flash-lite`, ‏`openai-gpt-6-luna`.
- **Pro** (STANDARD): 4 מודלים: ‏`gemini-3-1-flash-lite`, ‏`gemini-3-5-flash-lite`, ‏`gemini-3-8-flash`, ‏`openai-gpt-6-luna`.
- **Studio** (HEAVY): כל 6 המודלים, כלומר גם `openai-gpt-6-1-sol` ו-`anthropic-claude-sonnet-5-5`.

ההכרעה מסמנת כמוחלפים את הפריט "allowlist (בחירה של Claude)" ואת "בעיה פתוחה, Free" שבסעיף הקודם.

## 2026-10-19 — בחירות של Claude (לא הכרעות CEO, פתוחות לשינוי)

| # | בחירה | סיבה | איפה |
|---|---|---|---|
| C1 | Studio→**HEAVY** | ההנחיה אמרה "HEAVY/PREMIUM", אבל `PREMIUM` לא קיים ב-`CostClass` | `pricing.M5_BUILD_COST_CLASS` |
| C2 | ~~Free ו-Enterprise נשארים עם STANDARD בנתיב M5~~ **הוחלף בהכרעות 19, 22 ו-23** | לא נכללו במיפוי. Free נחסם ממילא בבדיקת ההכנסה. Enterprise מתיר כל class. ב-internal QA אין בדיקת class | `m5_build_cost_class` |
| C3 | ~~כל בנייה של M5 עולה 60 קרדיטים בכל class~~ **הוחלף בהכרעה 20** | חלוקת קרדיטים לפי class לא נקבעה | `_M5_BUILD_CREDITS` |
| C4 | `BASIC` ו-`BUSINESS` נשארו כ-aliases, ו-`_missing_` ממפה את `'basic'`/`'business'` | ב-DB וב-Stripe metadata שמורים הערכים הישנים. כך אין צורך במיגרציה | `pricing.PlanCode` |
| C5 | בבחירת env, השם החדש גובר על הישן | כך הוגדר בהכרעה 14. ב-Vercel לא מוגדר אף אחד מהשמות, כך שאין השפעה כרגע | `_env_decimal_renamed` |
| C6 | חיפוש מחיר בלי provider שמוצא כמה ספקים זורק `AmbiguousPrice` ולא בוחר אחד מהם | בחירה שקטה הייתה מחזירה מחיר שגוי | `prices.price_at` |
| C7 | קרדיטים, תקרות ספקים, פרויקטים ומושבים לא שונו | לא הוכרעו. המרווחים שנקבעו (הכרעה 9) גוזרים תקרות של כ-$2.48 / $23.46 / $114.52 לחודש | `docs/PRICING.md` |
| C8 | המחיר של Replicate סומן כ-verified ב-2026-10-19 | אומת ידנית מול `replicate.com/pricing` ("$3.00 / thousand output images"). אין snapshot | `prices.py` |
| C9 | התגית VERIFIED הוסרה ממחירי Venice ומהמתחרים | אין snapshot שאפשר לשחזר ממנו. ‏#57 הוא צילום טקסט, לא byte-exact | #54, ‏#56, ‏#57 |
| C10 | ל-Free נקבעה תקרה חודשית של $1.05 להוצאה על ספקים (3 × $0.35), שניתנת לשינוי ב-`OMNI_PROVIDER_CAP_FREE_USD` | בלעדיה `reserve` היה חוסם את הבנייה בתשלום שהוכרעה ב-#29, כי התקרה הקודמת של Free הייתה $0 | `PLAN_CATALOG` |

## השלכות פתוחות

- ~~ה-class הוא תווית בלבד~~ **תוקן ב-#59:** ה-class קובע allowlist, תקציב וקרדיטים. **~~תנאי ל-worker~~ (נפתר בהכרעה 30):** ‏`bind_budget` רק מוריד תקציב ולעולם לא מעלה אותו. אם `OMNI_EXTERNAL_BUDGET_USD` ב-`WORKER_ENV` נמוך מתקרת ה-class (למשל $0.50 מול $5.50 של Studio), התקרה של ה-worker גוברת, וההבדל בין ה-tiers נעלם בזמן ריצה. כדי שה-tiers יהיו אמיתיים עד הסוף, הערך הזה צריך להיות לפחות $18.
- **approvals ישנים:** ה-budget fingerprint כולל עכשיו את הקרדיטים של ה-class. approval שנוצר לפני הפריסה (עם 60 קרדיטים) לא יתאים יותר, והלקוח יתבקש לאשר מחדש. הכשל חוסם בצורה בטוחה ולא גורם לחיוב שגוי.
- **idempotency:** ה-fingerprint של הצעת המחיר כולל את `cost_class`. בנייה שנוצרה לפני הפריסה ומשוחזרת אחריה עם אותו מפתח תקבל `idempotency_conflict`.
- **`email-verification/request`** מחזיר 400 במקום 401. מתועד בטסט ב-#50, לא תוקן.

## 2026-10-20 — גל מיזוגים (הרשאת מייסד, צ'אט 00:16)

כללי הגל: מיזוג רק על ה-SHA המדויק של ה-head אחרי CI ירוק, ואז המתנה ל-CI ירוק על main. PR שנוגע ב-`omni_prod/**` או ב-`.github/workflows/**` ממתין לאודיט הגולמי של מאט. בלי rebase "לריפוי".

| PR | head SHA | קבצים | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|---|
| #65 | `a59211d` | `AGENTS.md` | **מוזג**. CI על main ירוק (test, validate, pg, smoke, compose-config, customer-ui, verify) | `8f4530c` | מייסד, צ'אט 00:16 |
| #48 #49 #51 #54 #55 #56 #61 #62 | `1b2fc41` `1760f9e` `ec6e17b` `883c8db` `818b5ee` `56288aa` `57b9c6a` `4df51b3` | `docs/` בלבד (PUBLIC_ROUTES, DB_TARGETS, SECRETS_POLICY, MODEL_PRICES, PLANS, PRICING, PROVIDERS_INVENTORY, DECISIONS_LOG) | **באצ' דוקס**, מיזוג אחד. כל head ירוק, אין קבצים חופפים | ראו את PR הבאצ' | מייסד, צ'אט 00:16 |
| #63 | `ea9abfc` | `omni_prod/investor_app.py`, טסט | **לא מוזג**: נוגע ב-`omni_prod/**` (תנאי א), ונכתב ע"י Claude, כך שנדרש מבט שני | — | ממתין למאט |
| #43 | `ef5051a` | `.github/workflows/backup-restore.yml` | **לא מוזג**: workflows (תנאי א) | — | ממתין למאט |
| #46 | `dceae0f` | `.github/workflows/production-smoke.yml` | **לא מוזג**: workflows (תנאי א). גם #45 נוגע באותו קובץ (תנאי ד) | — | ממתין למאט |
| #39 → #50 | `67f6d77` / `575bde6` | `omni_prod/browser_session.py`, `investor_app.py` / טסט | **לא מוזג**: #39 נוגע ב-`omni_prod/**` (תנאי א). ‏#50 תלוי בו, וה-CI שלו אדום (test, customer-ui; תנאי ב) | — | ממתין למאט |
| #47 → #52 | `09406ea` / `1b22676` | טסט / `omni_prod/investor_app.py` | **לא מוזג**: CI של #47 אדום (test, validate: הטסט אדום עד שיהיה מימוש; תנאי ב). ‏#52 נוגע ב-`omni_prod/**` (תנאי א) | — | ממתין |
| #57 | `a97d5b8` | `docs/venice_prices_snapshot.*` | **לא נכלל בבאצ'**: `pg=failure` על ה-head (תנאי ב) | — | — |
| #75 | `3163dc2` | `.github/workflows/deploy-worker.yml`, טסט | **לא מוזג**: workflows (תנאי א) | — | ממתין למאט |

### המשך הגל — 2026-10-20 00:57 (main ירוק ב-`0ee20fe`; ‏rule ב שוחרר עבור #47, #50, #57)

| PR | head SHA | קבצים | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|---|
| #76 (באצ' הדוקס) | `2cdae51` | `docs/` | מוזג ב-`0ee20fe`. ‏customer-ui נפל פעם אחת (job 118323597983); הרצה חוזרת עברה (118328825858). העץ זהה ל-head שעבר פעמיים ב-PR | `0ee20fe` | מייסד, צ'אט 00:16 |
| #57 | `a97d5b8` | `docs/venice_prices_snapshot.md`, `.tsv` | **מוזג**. ‏`pg` הורץ שוב פעם אחת (117810289395 → 118332213063 success), בלי rebase. CI על main ירוק | `3234ca4` | מייסד, צ'אט 00:57 |
| #47 | `09406ea` | `tests/test_repo_summary_secrets.py` | **לא מוזג**. הכשל דטרמיניסטי: טסט החוזה מוצא דליפה של `config.json` ו-`.env` ב-`_repo_summary`, והוא אדום עד שימוזג #52 (נוגע ב-`omni_prod`, ממתין למאט). מיזוג יצבע את main באדום (תנאי ג) | — | ממתין ל-#52 |
| #50 | `575bde6` | `tests/test_pr39_cookie_fallback_real_routes.py` | **לא מוזג**. ה-base הוא הענף של #39, לא main. ‏assertions אמיתיים נכשלים (`400 != 401`, `200 != 401`, `401 != 200`): אפיון של #39 מול קוד בלי #39 | — | ממתין ל-#39 (מאט) |

**פלייק customer-ui (נמדד, לא תוקן):** `tests/customer_flow_browser.cjs` רץ 25 פעמים מקומית (Playwright 1.56.1, Chromium 1194). **4/25 נכשלו** (16%), כולם בשורה 34: click על כפתור "שינוי" הראשון ב-`#discoveryPanel`, ‏`TimeoutError`, ‏"element is not visible". זה **לא** ה-`setTimeout` של 150ms ב-`/approvals` (שורה 23), שקורה מאוחר יותר.

### 2026-10-20 08:31 — מיזוג #81, בדיקת R2 (#83), תקציב QA

| PR | head SHA | קבצים | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|---|
| #81 | `513e08f` | `tests/customer_flow_browser.cjs` | **מוזג**. טסט בלבד. CI על ה-head ירוק; CI על main ירוק (test, customer-ui, pg, validate, compose-config, smoke, verify) | `1b9a229` | מייסד, צ'אט 08:31 |
| #83 | `3535a0f` | `omni_prod/postdeploy_checks.py`, `tests/test_postdeploy_r2_artifact.py` | **לא מוזג**: נוגע ב-`omni_prod/**` (תנאי א) | — | ממתין למאט |

**תקציב QA (spend-audit, run 39375470852, $0):** ‏`qa_used_usd` ‏(`omni_prod/qa_budget.py:102-121`), נבדק ב-`authorize_qa_build` ‏(`:181-183`) מול `OMNI_QA_BUDGET_TOTAL_USD=10`: ‏used=5.26698025 (all-time). ‏`settled_provider_cost_usd` של 34 בנייות: 12.311130.

### 2026-10-20 08:46 — אפשרות (ג): E2E בתשלום בלי R2

- ה-worker הפרוס היה `4b019d8`, מאחור לעומת main: 215 שורות ב-`omni_prod`. ‏`pg` על `6781b9d` רץ שוב פעם אחת (118473633457 → 118476560774, success). ‏deploy-worker רץ על `4d488b4`, ‏run 39377073605: success, כל ה-probes עברו (PASS).
- ‏postdeploy-checks, ‏stage=paid, ‏max_usd=0.50, ‏run 39377332673 על `4d488b4`: **FAIL**. הבנייה `bld_65ee693e356847d89ab50300415d6861` עצרה ב-verification_failed אחרי 3 סבבי תיקון (max_repair_rounds). אין גרסה, אין preview, ו-R2 לא רלוונטי. העלות: $0.04756005 (metered = settled; שוריינו 0.35). לא היה כשל תחביר בסבב 0, ולכן לא הייתה הרצה שנייה. ‏inspect-build: ‏run 39378559811, ‏$0.
- ממצא, לא תוקן: `omni_prod/web_saas_acceptance.py:396-398` מבצע `str(step['expect_text_contains'])`. כשהשלב מכיל רשימה, הבדיקה מחפשת את המחרוזת `"['viewport', 'width=device-width']"`, שלא קיימת. ה-HTML של הבנייה מכיל `<meta name="viewport" content="width=device-width, ...">`, כך שבסבבים 1–3 BEHAVIOR/A5 נכשל כנראה כשל שווא.

### 2026-10-20 09:23 — תיקון expect_text_contains (#84), הכרעות

| PR | head SHA | קבצים | תוצאה | אישר |
|---|---|---|---|---|
| #84 | `2f20ec6` | `omni_prod/web_saas_acceptance.py`, `tests/test_expect_text_contains_list.py`, רג'יסטרים שנוצרו מחדש | CI ירוק. **לא מוזג**: נוגע ב-`omni_prod/**` (תנאי א) | ממתין למאט או לאישור מייסד |
| #75 | `3163dc2` | `.github/workflows/deploy-worker.yml`, טסט | **לא נגעתי**: הטקסט של שני החסמים של מאט לא נמצא ב-PR, ב-repo או בשיחה | ממתין לטקסט |

### 2026-10-20 13:09 — preflight (#85), ‏#75 EOF, ‏json_schema

| PR | head SHA | קבצים | תוצאה | אישר |
|---|---|---|---|---|
| #85 | `717cd83` | `omni_prod/round_preflight.py`, `tests/test_round_preflight.py` | CI ירוק. **לא מוזג**: תנאי א | ממתין למאט |
| #84 | `2f20ec6` | `omni_prod/web_saas_acceptance.py` + טסט | **לא מוזג**, החלטת מייסד 13:09: לא ממזגים בלי אודיט | ממתין למאט |
| #75 | `3b7bdf2` | `tests/test_deploy_rollback_snapshot.py`: הוסרה שורה ריקה אחת ב-EOF (`git diff --check`: 2 → 0) | CI ירוק. **לא מוזג**: על exit=42 מאט עוד צריך לפסוק | ממתין למאט |

- ‏exit=42, שוחזר עם docker מזויף: config_error OLD=1 / NEW=42; ‏missing_worker 1/1; ‏missing_intake 1/1; ‏ok 0/0. ב-OLD, ‏pipefail מחזיר את ה-1 של grep ומסתיר את קוד היציאה של docker. ב-NEW, הקוד של docker עובר כמו שהוא. בשני המקרים הצעד נכשל.
- ‏gpt-6-luna: לפי התיעוד של OpenAI, ‏structured_outputs נתמך ב-`v1/chat/completions` (וגם `response_format: json_schema` עם `strict`). לא נשלחה קריאה, ולא שיניתי דבר.

### 2026-10-20 17:49 — מיזוג #84, ניתוב luna (#86)

| PR | head SHA | קבצים | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|---|
| #84 | `2f20ec6` | `omni_prod/web_saas_acceptance.py` + טסט + רג'יסטרים | **מוזג**. מאט סגר את תנאי א על ה-head הזה (תגובה ב-PR, 10:12Z). CI על main ירוק | `6f78119` | מאט (תנאי א) + מייסד 17:49 |
| #86 | `74b2ca3` | `omni_prod/intelligence/{task_policy,inventory,matrix}.py`, ‏`PROVIDER_MATRIX.*`, 2 טסטים | CI ירוק. **לא מוזג**: תנאי א | — | ממתין למאט |
| #82 | `1bded16` | `.github/workflows/intake-budget-pg.yml` | מאט סגר. ממתין, לפי הוראת המייסד ("אחרי המשחררים") | — | — |

- ה-allowlist של cost class light הוא לפי מחיר בלבד: `omni_prod/pricing.py:228-231` (LIGHT <= $1.50/M output), והוא מופעל ב-`omni_prod/routed_gateway.py:129-138`. שני המודלים שהוא מכניס נמצאים מתחת לרף של codegen (85), ולכן `ranked_routes` בחר את הזול מביניהם, luna.
- החלטה: ‏`deny_models` ב-`task_policy`. ‏gpt-6-luna לא משמש ל-codegen, ל-repair ול-modification, באף cost class.

### 2026-10-20 18:36 — מיזוג #75, ‏#85 (reproduction), מונה ה-CSS (#87)

| PR | head SHA | קבצים | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|---|
| #75 | `3b7bdf2` | `.github/workflows/deploy-worker.yml`, טסט | **מוזג**. ה-PR היה עדיין draft (405), סומן ready ואז מוזג. מאט סגר את תנאי א ופסק על exit=42 (ACCEPTED), ‏14:52Z. CI על main ירוק | `3b9fbad` | מאט + מייסד 18:36 |
| #85 | `65cd729` | + `tests/test_preflight_propagation_real_behaviour.py` (SHA-256 `77173ab2…28c3`) | CI ירוק. reproduction של BASE מול HEAD פורסם ב-PR (comment 6294778479). **לא מוזג**: ה-HOLD של מאט עדיין פתוח | — | ממתין למאט |
| #87 | `e1a9864` | `omni_prod/skills_runtime.py` (`css_declaration_count`), טסטים, רג'יסטרים | CI ירוק, אחרי הרצה חוזרת אחת של `pg` (118724171626 → 118730212315). **לא מוזג**: תנאי א | — | ממתין למאט |

- החלטה ב-review: מתקנים את המונה. הסף 40, ה-tokens וה-`@media` נשארים חוסמים, תחת המכסה הקיימת (2 סבבים, ואז אזהרה).

### 2026-10-20 21:00 — מיזוג #85, ‏#86, פריסה והרצה

| PR | head SHA | תוצאה | SHA ב-main | אישר |
|---|---|---|---|---|
| #85 | `65cd729` | **מוזג**. מאט: HOLD REMOVED / RULE_A=CLOSED ‏(15:43Z). CI על main ירוק | `a00e803` | מאט + מייסד 21:00 |
| #86 | `74b2ca3` | **מוזג** אחרי ש-main ירוק על #85. מאט: RULE_A=CLOSED ‏(15:43Z). CI על main ירוק | `921d20f` | מאט + מייסד 21:00 |

- ‏deploy-worker: ‏run 39472683855 על `8a3ea4a` (מכיל את #85 ואת #86): success, כל ה-probes עברו (PASS).
- ‏postdeploy-checks, ‏stage=paid, ‏max_usd=0.50: ‏run 39473090833 ‏**FAIL**. הבנייה `bld_4f3b3514edd34776b096bf20fd66cc58` עצרה ב-verification_failed אחרי 3 סבבי תיקון. סבב 0 נכשל על PREVIEW (דף placeholder), לא על תחביר, ולכן לא הייתה הרצה שנייה. העלות: $0.02940445 ב-10 קריאות, כולן ok, ואף קריאה של luna ל-codegen או ל-repair. ‏inspect-build: ‏run 39473867717.
- לא מוזגו, לריצה הבאה: #87, #83, #39, #52, #80.

### 2026-10-20 21:24 — ראיות מ-run 39473090833, ‏#88 (קריאת R2)

**ראיות (inspect-build 39473867717):**
- **‏#86 עבד.** כל 6 קריאות ה-codegen וה-repair הלכו ל-gemini-3.1-flash-lite וכולן ok, בלי אף כשל JSON. ‏gpt-6-luna קיבל רק architecture (1) ו-review (3), כולן ok.
- **‏responsive עבר בסבב 3** (`S5 responsive: HTTP 200 matched expectations`). התיקון של #84 (רשימה ב-`expect_text_contains`) נוגע בדיוק בצעד הזה. אם הצעד בהרצה הזו השתמש ברשימה או במחרוזת, עוד לא נקרא; זה יתברר מה-zip, דרך #88.
- **‏preflight נקרא:** קריאת repair אחת לפני האימות הראשון (סבב 0), וקריאה נוספת בסבב 2. ה-inspect לא מראה אם זה היה תיקון syntax או תיקון plan, ולכן זה עוד לא ראיה ש-#85 עצמו פעל.

| PR | head SHA | קבצים | תוצאה | אישר |
|---|---|---|---|---|
| #88 | `2d6c1b4` | `.github/workflows/inspect-round-artifacts.yml`, `tests/test_inspect_round_artifacts_workflow.py` | **לא מוזג, לא הורץ**: תנאי א | ממתין למאט |

### 2026-10-20 21:38 — ראיה (תיקון מייסד), ‏#89, ‏#90

**ראיה, כפי שתוקנה:** ש-responsive עבר בסבב 3 של run 39473090833 זו ראיה ל-#84, לא ל-#85. ‏#85 עוד לא הוכח בהרצה חיה.

| PR | head SHA | קבצים | תוצאה | אישר |
|---|---|---|---|---|
| #89 | `cb4a020` | `omni_prod/preview_smoke.py`, `tests/test_preview_verdict_names_condition.py`, רג'יסטרים | הודעת ה-preview מציינת איזה תנאי נכשל: (a) קצר מדי ו/או (b) בלי רכיב אינטראקטיבי. הכלל לא השתנה. **לא מוזג**: תנאי א | ממתין למאט |
| #90 | `6c74bdc` | `omni_prod/consistency_gate.py` (`http_reason`), `tests/test_consistency_http_reason.py`, רג'יסטרים | ‏`send_error`/`send_response` עם reason שאינו latin-1 נחסם לפני ה-sandbox. **לא מוזג**: תנאי א | ממתין למאט |

- ‏#89 ו-#90 נוגעים שניהם בקבצי הרג'יסטרים שנוצרים אוטומטית. לפי תנאי ד: ממזגים אחד, מחכים ל-main ירוק, ואת השני מבססים מחדש (rebase) ומריצים שוב את ה-generators.
- ‏app.py של run 39473090833 נכתב על ידי המודל (gemini-3.1-flash-lite). אין לו תבנית בנתיב הבנייה; ‏`app.py` קבוע מופיע רק ב-fixtures של טסטים.
