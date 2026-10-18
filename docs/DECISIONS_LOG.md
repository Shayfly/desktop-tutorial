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

## 2026-10-19 — בחירות של Claude (לא הכרעות CEO, פתוחות לשינוי)

| # | בחירה | סיבה | איפה |
|---|---|---|---|
| C1 | Studio→**HEAVY** | ההנחיה אמרה "HEAVY/PREMIUM", אבל `PREMIUM` לא קיים ב-`CostClass` | `pricing.M5_BUILD_COST_CLASS` |
| C2 | Free ו-Enterprise נשארים עם STANDARD בנתיב M5, כמו לפני ההכרעה | לא נכללו במיפוי. Free נחסם ממילא בבדיקת ההכנסה. Enterprise מתיר כל class. ב-internal QA אין בדיקת class | `m5_build_cost_class` |
| C3 | כל בנייה של M5 עולה 60 קרדיטים בכל class | חלוקת קרדיטים לפי class לא נקבעה | `_M5_BUILD_CREDITS` |
| C4 | `BASIC` ו-`BUSINESS` נשארו כ-aliases, ו-`_missing_` ממפה את `'basic'`/`'business'` | ב-DB וב-Stripe metadata שמורים הערכים הישנים. כך אין צורך במיגרציה | `pricing.PlanCode` |
| C5 | בבחירת env, השם החדש גובר על הישן | כך הוגדר בהכרעה 14. ב-Vercel לא מוגדר אף אחד מהשמות, כך שאין השפעה כרגע | `_env_decimal_renamed` |
| C6 | חיפוש מחיר בלי provider שמוצא כמה ספקים זורק `AmbiguousPrice` ולא בוחר אחד מהם | בחירה שקטה הייתה מחזירה מחיר שגוי | `prices.price_at` |
| C7 | קרדיטים, תקרות ספקים, פרויקטים ומושבים לא שונו | לא הוכרעו. המרווחים שנקבעו (הכרעה 9) גוזרים תקרות של כ-$2.48 / $23.46 / $114.52 לחודש | `docs/PRICING.md` |
| C8 | המחיר של Replicate סומן כ-verified ב-2026-10-19 | אומת ידנית מול `replicate.com/pricing` ("$3.00 / thousand output images"). אין snapshot | `prices.py` |
| C9 | התגית VERIFIED הוסרה ממחירי Venice ומהמתחרים | אין snapshot שאפשר לשחזר ממנו. ‏#57 הוא צילום טקסט, לא byte-exact | #54, ‏#56, ‏#57 |

## השלכות פתוחות

- **התווית של ה-class לא קובעת אילו מודלים ירוצו.** ‏`cost_class` משמש רק ב-`reserve` וב-fingerprint. ההוצאה בפועל נקבעת לפי `OMNI_EXTERNAL_BUDGET_USD` ורצפת המרווח. כלומר בנייה של Amateur ב-LIGHT משתמשת באותו ניתוב ובאותו תקציב כמו בנייה ב-STANDARD.
- **idempotency:** ה-fingerprint של הצעת המחיר כולל את `cost_class`. בנייה שנוצרה לפני הפריסה ומשוחזרת אחריה עם אותו מפתח תקבל `idempotency_conflict`.
- **`email-verification/request`** מחזיר 400 במקום 401. מתועד בטסט ב-#50, לא תוקן.
