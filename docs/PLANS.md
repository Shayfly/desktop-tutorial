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
| — | Enterprise (חוזה) | **לא מופיע במחירון המאושר.** צריך להחליט: להסיר או להשאיר. |

שינוי env לבדו **לא** מספיק:
- הוא משנה מחיר, לא שם. ב-`/api/v28/pricing` ובחשבונית יופיעו "Basic" ו-"Business".
- הקרדיטים, הפרויקטים והמושבים של המדרגה הישנה יישארו כמו שהם.

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
3. **החלטה על Enterprise.**
4. **מיגרציה של מנויים קיימים** (basic/business → amateur/studio). צריך לבדוק אם יש מנויים כאלה ב-DB. לא נבדק מכאן.
5. **Price IDs ב-Stripe** למחירים החדשים, ואימות live של checkout ו-webhook.
6. **UI לבחירה ושדרוג תוכנית.**
7. **ענף לא ממוזג** `feature/profit-protection-credit-economy-v1-20261014`. ייתכן שהוא משנה את מודל הקרדיטים. לא נבדק כאן.
