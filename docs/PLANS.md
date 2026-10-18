# PLANS — מדרגות המנוי: מה קיים בקוד ומה חסר

נבדק מול `main` @ `1f744ae`, 2026-10-19. המסמך מתעד בלבד ולא משנה קוד (`omni_prod/**` מחוץ לתחום).

## המחירון המאושר

**Free $0 · Amateur $29 · Pro $99 · Studio $299** (חודשי).

מקור: הנחיית המייסד בצ'אט עם Claude, 2026-10-19 01:10 Asia/Jerusalem. זו לא רשומה שניתן לאמת בריפו. כדי שתהיה ראיה עמידה, נדרש comment של `@Shayfly` על ה-PR של המסמך הזה.

## מה הקוד מגדיר היום

מקור: `omni_prod/pricing.py:103-145` (`PLAN_CATALOG`). כל ה-status הם `prelaunch-proposed`.

| | Free | Basic | Pro | Business | Enterprise |
|---|---|---|---|---|---|
| קוד (`PlanCode`) | `free` | `basic` | `pro` | `business` | `enterprise` |
| מחיר חודשי | $0 | $12 | $39 | $99 | חוזה |
| מחיר שנתי | $0 | $120 | $390 | $990 | חוזה |
| קרדיטים כלולים | 150 | 900 | 4,000 | 12,000 | 0 |
| תקרת הוצאה על ספקים (פנימי) | $0 | $2.50 | $10 | $25 | — |
| פרויקטים | 2 | 10 | 50 | 250 | ללא הגבלה |
| מושבים | 1 | 1 | 1 | 5 | ללא הגבלה |
| cost classes מותרים | zero | zero/light/standard | עד heavy | הכול | הכול |
| מיתוג 148AI | חובה | עדין, חובה | אופציונלי | white-label | חוזה |

המחירים של Basic, ‏Pro ו-Business ותקרות ההוצאה על ספקים ניתנים לשינוי דרך env:
- מחירים: `OMNI_PRICE_{BASIC,PRO,BUSINESS}[_ANNUAL]_USD`.
- תקרות: `OMNI_PROVIDER_CAP_*_USD`.

שמות המדרגות, הקרדיטים, מגבלת הפרויקטים והמושבים קבועים בקוד.

## פער: המאושר מול הקוד

| מאושר | המקבילה הקרובה בקוד | פער |
|---|---|---|
| Free $0 | Free $0 | אין פער במחיר |
| **Amateur $29** | Basic $12 | **שם שונה, מחיר שונה.** אין `PlanCode.AMATEUR`. |
| **Pro $99** | Pro $39 | **מחיר שונה.** אפשר לתקן ב-env (`OMNI_PRICE_PRO_USD=99`). |
| **Studio $299** | Business $99 | **שם שונה, מחיר שונה.** אין `PlanCode.STUDIO`. |
| Enterprise (חוזה) | Enterprise (חוזה) | **נשאר. לא מוסר** (הוכרע: CEO, 2026-10-19) |

שינוי env לבדו **לא** מספיק:
- הוא משנה מחיר, לא שם. ב-`/api/v28/pricing` ובחשבונית יופיעו "Basic" ו-"Business".
- הקרדיטים, הפרויקטים והמושבים של המדרגה הישנה יישארו כמו שהם.

## מיפוי השינוי (הוכרע: CEO, 2026-10-19)

| בקוד היום | יעד | מחיר יעד | פעולה נדרשת ב-`omni_prod/**` |
|---|---|---|---|
| `free` (Free) | Free | $0 | אין |
| `basic` (Basic) | **Amateur** | $29 | שינוי שם התצוגה ל-`Amateur`. המחיר דרך `OMNI_PRICE_BASIC_USD=29` או בקוד. להחליט אם להשאיר את ה-`PlanCode` כ-`basic`, או ליצור `amateur` עם מיגרציה למנויים קיימים. |
| `pro` (Pro) | Pro | $99 | המחיר דרך `OMNI_PRICE_PRO_USD=99` או בקוד |
| `business` (Business) | **Studio** | $299 | שינוי שם התצוגה ל-`Studio`. המחיר דרך `OMNI_PRICE_BUSINESS_USD=299` או בקוד. אותה שאלת `PlanCode` כמו ב-Amateur. |
| `enterprise` (Enterprise) | Enterprise | חוזה | אין. **נשאר** |

מקור: הנחיית המייסד בצ'אט, 2026-10-19 01:22. נדרש comment של `@Shayfly` כראיה עמידה.

**שאלה פתוחה, לא מוכרעת:** שינוי שם התצוגה בלבד, בלי לשנות את ה-`PlanCode`, הוא המסלול הקטן ביותר. אין בו מיגרציה, ומיפוי Stripe (`STRIPE_PRICE_BASIC/BUSINESS`) נשאר כמו שהוא. אבל הקוד הפנימי ימשיך לקרוא למדרגות `basic` ו-`business`.

## מה קיים ופועל בקוד

| רכיב | איפה | מצב |
|---|---|---|
| קטלוג תוכניות + תצוגה ציבורית בלי כלכלה פנימית | `pricing.py:61-66`, ‏`PUBLIC_PLAN_FIELDS` (`:80`) | קיים. נאכף בטסט `tests/test_public_pricing_economics.py` |
| `GET /api/v28/pricing` (ציבורי) | `investor_app.py:1317` | קיים |
| אכיפת שימוש: cost class + קרדיטים + תקרת הוצאה על ספקים | `SubscriptionService.authorize/consume` (`pricing.py:248`, ‏`:287`) | קיים. builds חיים: 60/140/400 קרדיטים לפי class (`investor_app.py:1729`, ‏`:3262-3280`) |
| שמירת מנוי ב-Postgres | `subscription_store.py:19` (`PostgresSubscriptionService`) | קיים |
| Stripe Checkout (מנוי) | `stripe_billing.py:47`; מיפוי מחיר דרך `STRIPE_PRICE_{BASIC,PRO,BUSINESS}` (`:21-23`) | קיים בקוד. **התנהגות live לא אומתה** (`STATUS.md:241`) |
| Stripe webhook → הפעלת תוכנית | `stripe_billing.py:117-165`; 5 אירועים (`:123-124`) | קיים, עם חתימה מאומתת |
| מיתוג לפי תוכנית | `branding.py:36` | קיים |
| entitlement פנימי (QA) | `entitlements.py`: רק `INTERNAL_QA` ב-scope ‏`staging` | קיים |
| UI | `ui/app.js` (`loadSubscription`): מציג שם תוכנית וקרדיטים שנותרו | **תצוגה בלבד.** אין בחירת תוכנית, אין שדרוג, אין קריאה ל-checkout |

## מה חסר

1. **מדרגות Amateur ו-Studio**: `PlanCode`, ‏`PLAN_CATALOG`, מיפוי Stripe (`STRIPE_PRICE_AMATEUR/STUDIO`) וטסטים. זה שינוי ב-`omni_prod/**`.
2. **הגדרות לכל מדרגה מאושרת. כל אלה דורשים החלטה, ולא נמסרו:**
   - קרדיטים כלולים
   - תקרת הוצאה על ספקים
   - מספר פרויקטים ומושבים
   - cost classes מותרים
   - מיתוג
   - **מחיר שנתי**

   המרווחים הסופיים (`docs/PRICING.md`) גוזרים תקרת הוצאה על ספקים: כ-$2.48 / $23.46 / $114.52 לחודש.
3. **מיגרציה של מנויים קיימים** (basic/business → amateur/studio). צריך לבדוק אם יש מנויים כאלה ב-DB. לא נבדק מכאן.
4. **Price IDs ב-Stripe** למחירים החדשים, ואימות live של checkout ו-webhook.
5. **UI לבחירה ושדרוג תוכנית.**
6. **ענף לא ממוזג** `feature/profit-protection-credit-economy-v1-20261014`. ייתכן שהוא משנה את מודל הקרדיטים. לא נבדק כאן.
