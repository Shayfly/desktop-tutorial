# PUBLIC_ROUTES — נתיבים ללא אימות ב-middleware

מקור: `omni_prod/investor_app.py:95` (`_PUBLIC_PREFIXES`), נבדק מול `main` @ `7afaa75`, 2026-10-19.
המסמך מתאר את הקוד כפי שהוא. הוא לא משנה התנהגות.

## איך הרשימה נאכפת (`production_auth`, שורות 96–110)

1. **פעיל רק כש-`OMNI_ENV == 'production'` בדיוק.** ב-`staging`, ב-`development` ובכל ערך אחר אין בדיקת אימות במידלוור על אף נתיב `/api/`.
2. **רק נתיבים שמתחילים ב-`/api/`.** כל נתיב אחר (כולל `/_omni/metrics`) לא נבדק בכלל.
3. **שני סוגי התאמה:**
   - ערך שמסתיים ב-`/` הוא **prefix**: כל מה שמתחתיו ציבורי.
   - כל ערך אחר הוא **התאמה מדויקת**: `/api/v28/pricing` ציבורי, `/api/v28/pricing/x` לא.
4. המידלוור מקבל רק `Authorization: Bearer`. עוגיית session לבדה מקבלת 401 בכל נתיב שאינו ציבורי. (זה הנושא של PR #39.)
5. מידלוור נפרד (`_LEGACY_PREFIXES`, שורה 114) מחזיר **410** על `/api/source/*` ב-staging וב-production, לפני שה-handler רץ.

"ציבורי" בטבלה פירושו: המידלוור לא דורש טוקן ב-production. בעמודת ההצדקה מצוין אם ה-handler עצמו מאמת.

## טבלה

| נתיב | מה מחזיר | האם ציבורי | הצדקה | האם נדרש טסט |
|---|---|---|---|---|
| `POST /api/v26/auth/register` | יצירת חשבון V26 + טוקן | כן (prefix) | **טעון הכרעה**: גרסת auth ישנה. אין צרכן ב-`ui/`, ב-`scripts/` או ב-`.github/`. צריך להחליט אם להשאיר. | כן: ההחלטה (השארה או 410) |
| `POST /api/v26/auth/login` | טוקן V26 | כן (prefix) | **טעון הכרעה**: כמו למעלה | כן |
| `POST /api/v27/auth/register` | יצירת חשבון V27 + טוקן | כן (prefix) | **טעון הכרעה**: גרסת auth ישנה, אין צרכן | כן |
| `POST /api/v27/auth/login` | טוקן V27 | כן (prefix) | **טעון הכרעה**: כמו למעלה | כן |
| `POST /api/v28/auth/register` | חשבון + טוקן + עוגיית session; ניסיון login אם החשבון קיים | כן (prefix) | הרשמה חייבת להיות ציבורית. ה-UI צורך אותו (`ui/app.js:6`). | יש חלקי. נדרש: 409 על חשבון קיים עם סיסמה שגויה |
| `POST /api/v28/auth/login` | טוקן + subscription + עוגייה | כן (prefix) | כניסה חייבת להיות ציבורית (`ui/app.js:6`) | יש (2 קבצים) |
| `POST /api/v28/auth/logout` | `logged_out`, מוחק עוגייה תמיד | כן (prefix) | חייב לעבוד גם עם session שפג תוקפו, כדי שהעוגייה תימחק (הערה בקוד, שורות 1375–1379) | כן: מחיקת עוגייה בלי טוקן תקף |
| `GET /api/v28/auth/sessions` | רשימת ה-sessions של החשבון | כן (prefix) | **טעון הכרעה**: ציבורי בגלל ה-prefix, לא בגלל צורך. ההגנה היחידה היא `_v28_bearer` + `_v28.account` ב-handler. | **כן, חסר**: 401 בלי טוקן ב-production |
| `POST /api/v28/auth/sessions/{id}/revoke` | ביטול session | כן (prefix) | **טעון הכרעה**: כמו למעלה; ההגנה ב-handler בלבד | **כן, חסר**: 401/403 בלי טוקן, ו-403 על session של משתמש אחר |
| `POST /api/v28/auth/email-verification/request` | 202 | כן (prefix) | **טעון הכרעה**: דורש חשבון; ההגנה ב-handler בלבד | **כן, חסר** |
| `POST /api/v28/auth/verify-email` | `verified` + `user_id` | כן (prefix) | הקישור מהמייל נפתח בלי session; הטוקן במייל הוא האימות | כן: טוקן לא תקף מחזיר 400 |
| `POST /api/v28/auth/password-reset/request` | 202 תמיד | כן (prefix) | משתמש שאיבד סיסמה אינו מחובר; התגובה בטוחה מפני enumeration | כן: אותה תגובה למייל קיים ולא קיים |
| `POST /api/v28/auth/password-reset/confirm` | `reset` | כן (prefix) | טוקן האיפוס הוא האימות | כן: טוקן לא תקף מחזיר 400 |
| `POST /api/v28/auth/consents` | רישום הסכמה | כן (prefix) | **טעון הכרעה**: דורש חשבון; ההגנה ב-handler בלבד | **כן, חסר** |
| `POST /api/v28/auth/data-export` | בקשת ייצוא נתונים (202) | כן (prefix) | **טעון הכרעה**: פעולה על נתוני משתמש; ההגנה ב-handler בלבד | **כן, חסר**: 401 בלי טוקן |
| `POST /api/v28/auth/account-deletion` | בקשת מחיקת חשבון (202) | כן (prefix) | **טעון הכרעה**: פעולה הרסנית; ההגנה ב-handler בלבד | **כן, חסר**: 401 בלי טוקן, ו-CSRF על עוגייה |
| `GET /api/v28/pricing` | קטלוג תוכניות ציבורי (`public_dict`) + עקרונות | כן (exact) | עמוד תמחור לפני הרשמה. כלכלה פנימית מוסננת (`pricing.py:61`). | יש (`test_public_pricing_economics.py`) |
| `GET /api/v28/brand/readiness` | מצב מוכנות מיתוג | כן (exact) | **טעון הכרעה**: מידע פנימי, אין צרכן ציבורי | כן |
| `GET /api/v28/launch/readiness` | שערי מוכנות להשקה | כן (exact) | **טעון הכרעה**: הצרכן היחיד הוא כפתור ב-UI אחרי התחברות (`ui/app.js:18`), כך שאין צורך שיהיה ציבורי | כן |
| `GET /api/v28/ui/translations` | מחרוזות UI | כן (exact) | נדרש לפני התחברות, כדי להציג את מסך הכניסה בשפה הנכונה | יש (1) |
| `POST /api/v28/billing/stripe/webhook` | עיבוד אירוע Stripe | כן (exact) | Stripe לא שולח Bearer. האימות הוא חתימת `stripe-signature` מול `STRIPE_WEBHOOK_SECRET`. | יש (1). נדרש גם: 400 כשהסוד ריק |
| `GET /api/v28/deployment` | commit, environment, branch, תאימות סכמה, **`db_host` + `db_fingerprint`** | כן (exact) | נצרך ללא אימות ע"י `tools/deployment_verify.py:340` ו-`production-smoke.yml:95`. **טעון הכרעה לגבי `db_host`**: hostname של מסד הייצור חשוף לציבור. ה-fingerprint לבדו מספיק לאימות. | יש (2). נדרש: אסרשן על מה מותר לחשוף |
| `GET /api/status` | מוצר, יכולות, `readiness`, `international`, `brand_readiness`, `launch_readiness` | כן (exact) | נצרך ע"י `verify.yml` ו-`scripts/run_v28_http_acceptance.py`. **טעון הכרעה לגבי התוכן**: חושף את `OMNI_LOCAL_MODEL_URL` (`readiness.py:24`) ואילו תשתיות מוגדרות. בדיקת בריאות לא צריכה את זה. | יש (7). נדרש: אין כתובות פנימיות |
| `GET /api/international/readiness` | מוכנות בינלאומית | כן (exact) | **טעון הכרעה**: אין צרכן | כן |
| `GET /api/integrations` | קטלוג אינטגרציות + **שמות** הסודות הנדרשים (לא ערכים) | כן (exact) | **טעון הכרעה**: קיימת גרסה מאומתת `/api/v28/integrations`, ואין צרכן לגרסה הציבורית | כן |
| `GET /api/benchmark/catalog` | עד 200 מקרי בנצ'מרק כולל prompts | כן (exact) | **טעון הכרעה**: אין צרכן | כן |
| `GET /api/targets/mobile/{platform}` | תוכנית build למובייל | כן (prefix) | **טעון הכרעה**: אין צרכן | כן |
| `GET /api/targets/game/{engine}` | תוכנית build למנוע משחק | כן (prefix) | **טעון הכרעה**: אין צרכן | כן |
| `GET /api/source/mobile/{platform}` | `_repo_summary` של פרויקט Android/iOS שנוצר | כן (prefix), **אבל 410 ב-staging/production** (legacy guard) | **טעון הכרעה**: לא נגיש בפועל ב-production. הכניסה ל-`_PUBLIC_PREFIXES` מתה. | יש: 410 (`test_legacy_paths_guard.py`) + חוזה סודות (PR #47) |
| `GET /api/source/game/{engine}` | `_repo_summary` של פרויקט משחק | כן (prefix), **אבל 410 ב-staging/production** | **טעון הכרעה**: כמו למעלה | כן |
| `GET /api/v28/source/client/{platform}` | `_repo_summary` של קליינט 148AI ל-Android/iOS | כן (prefix), **לא חסום ע"י legacy** | **טעון הכרעה**: זה הנתיב הציבורי היחיד ב-production שמחזיר previews של קבצים, כולל קבצים רגישים כל עוד `is_sensitive_path` לא ממומש (PR #47). צרכן: `scripts/run_v28_http_acceptance.py` בלבד. | **כן, חסר**: אין טסט על הנתיב הזה |
| `GET /api/agent-team` | תוכנית צוות סוכנים | כן (exact) | **טעון הכרעה**: אין צרכן | כן |
| `GET /_omni/metrics` | מטריקות Prometheus (מונה בקשות, 5xx, זמני תגובה) | **כן, תמיד**: לא מתחיל ב-`/api/`, לכן המידלוור לא בודק אותו בכלל | **טעון הכרעה**: הכניסה ב-`_PUBLIC_PREFIXES` מתה ומטעה. המטריקות ציבוריות בכל סביבה, בלי קשר לרשימה. | כן |

## סיכום

- 33 נתיבים תחת 18 ערכים ב-`_PUBLIC_PREFIXES`.
- 24 מסומנים **טעון הכרעה** (בשורה של `/api/v28/deployment` ההכרעה נוגעת רק ל-`db_host`, ובשורה של `/api/status` רק לתוכן).
- 6 נתיבים תחת `/api/v28/auth/` ציבוריים רק בגלל ה-prefix, וההגנה עליהם קיימת ב-handler בלבד: `sessions`, `sessions/{id}/revoke`, `email-verification/request`, `consents`, `data-export`, `account-deletion`. לאף אחד מהם אין טסט שמוודא 401.
- שתי כניסות ברשימה מתות:
  - `/api/source/`: מקבל 410 ב-production ממילא.
  - `/_omni/metrics`: ציבורי תמיד, בלי קשר לרשימה.
- ב-staging אין אימות במידלוור על אף נתיב (`OMNI_ENV != 'production'`).
- חשיפת תשתית לציבור: `db_host` ב-`/api/v28/deployment`, `OMNI_LOCAL_MODEL_URL` ב-`/api/status`.

המסמך לא מכריע באף אחת מהנקודות האלה. ההכרעות שייכות לבעלי `omni_prod/**`.
