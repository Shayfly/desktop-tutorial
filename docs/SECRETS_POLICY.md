# SECRETS_POLICY — מה אסור שייכתב לריפו

**הריפו `Shayfly/desktop-tutorial` ציבורי.** כל קובץ, קומיט, הודעת קומיט, PR, issue, review comment ושם ענף קריא לכל אדם, ונשאר בהיסטוריה של Git גם אחרי מחיקה. מחיקה בקומיט חדש לא מסירה את המידע. מה שנכנס פעם אחת נחשב דלוף.

המסמך משלים את `SECRETS_AND_ENVIRONMENT.md`, שהוא רישום של **שמות** המשתנים. נבדק מול `main` @ `1f744ae`, 2026-10-19.

## 1. אסור לחלוטין

| קטגוריה | דוגמאות | איפה כן |
|---|---|---|
| מפתחות וטוקנים | `OMNI_SECRET_KEY`, מפתחות API של ספקי AI (OpenAI/Anthropic/Gemini/Groq), Stripe, Resend, RunPod, R2/S3 access/secret | Vercel env, GitHub Actions secrets, `WORKER_ENV` |
| Connection strings עם credentials | `postgresql://user:pass@…`, `rediss://default:…@…` | כנ"ל |
| טוקני session או JWT אמיתיים | כל `eyJhbGciOi…` שהונפק מסביבה חיה, כולל חשבונות smoke/QA | לא נשמרים בשום מקום |
| חומר חתימה | `*.pem`, `*.key`, `*.p12`, `*.jks`, keystore של Android, מפתח App Store Connect, service account JSON | CI secret store בלבד |
| קבצי env אמיתיים | `.env`, `.env.production`, `.env.local`, פלט של `vercel env pull` | מקומי בלבד (מוחרג ב-`.gitignore`) |
| קודי שחזור ו-2FA | recovery codes של Vercel/GitHub/ספקים | מנהל סיסמאות |
| נתוני לקוחות | אימיילים, גוף של בריפים או פרויקטים, קבצים שהועלו, נתוני תשלום | DB בלבד |

## 2. אסור: מידע תשתיתי

אלה לא סודות במובן הצר, אבל בריפו ציבורי הם מפת תקיפה.

| קטגוריה | דוגמה | הערה |
|---|---|---|
| hostnames של DB/Redis אמיתיים | `ep-…-….neon.tech`, `…upstash.io` | ה-fingerprint (12 hex) מספיק לזיהוי. ה-host לא נדרש. |
| כתובות IP של שרתים | ה-host של Oracle/worker | |
| כתובות של שירותים פנימיים | `OMNI_LOCAL_MODEL_URL` אמיתי, endpoints של sandbox | |
| מזהי חשבון בספקים | Vercel `prj_…`/`team_…`, Neon project id | בדרך כלל לא מספיקים לבד, אבל מקלים על הנדסה חברתית |
| אימיילים אישיים | כתובת ה-QA או כתובת הכניסה של המייסד | לכתוב "חשבון QA" או "חשבון המייסד" |

## 3. מותר

- **שמות** של משתנים (`OMNI_DATABASE_URL`), בלי ערכים.
- `.env.example` עם placeholders ריקים או `CHANGE_ME`.
- ערכי CI זמניים שברור שאינם אמיתיים, כמו `postgresql://postgres:ci-only@127.0.0.1:5432/postgres`.
- fixtures בטסטים עם ערכים מזויפים מובהקים, כמו `SECRETPW1`, `sk-live-DO-NOT-LEAK-…` או `AKIA-FAKE-…`, על host לא אמיתי. ערך שנראה אמיתי (prefix ופורמט מלאים) מפעיל סורקים חיצוניים, ולכן עדיף לסמן אותו כמזויף בשם.
- `db_fingerprint` (12 hex) ומזהי commit.

## 4. ערוצים שכותבים לריפו אוטומטית

| ערוץ | מה נכתב | סיכון | מצב |
|---|---|---|---|
| `.github/workflows/production-smoke.yml` → `smoke/last-run.md` (commit ו-push ל-`main`) | גוף **גולמי** (`BODY_RAW`) של תשובות Production | כל שדה שיתווסף לתשובה ייחשף אוטומטית | `7afaa75` מסנן `::add-mask::` ו-JWT. **`db_host` של Production עדיין נחשף** (מגיע מ-`/api/v28/deployment`). גם user id ואימייל של חשבון smoke נחשפים. |
| Actions logs | stdout של workflows | בריפו ציבורי, logs של workflows גלויים לכולם | `migrate.py` מדפיס host ו-fingerprint. `write-env.sh` מדפיס שמות בלבד. |
| Vercel bot comments על PRs | קישורי Preview | Preview פתוח לציבור, אלא אם Deployment Protection פעיל | לא נבדק כאן |

כלל לערוצים אוטומטיים: **allowlist של שדות, לא denylist.** דוח שנכנס ל-Git מכיל רק סטטוס, קוד HTTP ושמות בדיקות, לא גוף תשובה.

## 5. אירועים פתוחים (נמצאו בבדיקה הזו)

1. **טוקני session של Production בהיסטוריה הציבורית:** קומיט `ba2bb23` (smoke-bot, 2026-10-18 20:48 UTC), קובץ `smoke/last-run.md`, שתי שורות. הטוקנים שייכים לחשבון smoke סינתטי, ותוקף session הוא 7 ימים (`identity_lifecycle.py:391`). **פעולה נדרשת: לבטל את ה-session.** מחיקת הקובץ לא מבטלת את הטוקן. סיבוב `OMNI_SECRET_KEY` יבטל את **כל** ה-sessions, וזה צעד רחב יותר.
2. **`db_host` של Production** ב-`smoke/last-run.md` (הקומיטים `ba2bb23`, `1f744ae`) וגם ב-`/api/v28/deployment` הציבורי.
3. **אימייל אישי** ב-`docs/DECISIONS_2026-10-07_HE.md:27`.
4. **מזהי פרויקטים של Vercel** ב-`STATUS.md:1274` וב-`STATUS.md:1278`.

לא נמצאו בקבצים המעוקבים (`main` @ `1f744ae`): מפתחות בפורמט `sk-…`/`gsk_…`/`AKIA…`/`ghp_…`/`xox…`, ‏private keys, connection strings אמיתיים עם סיסמה, IP ציבורי, או קבצי `.env` מלבד `*.env.example`. הבדיקה נעשתה ב-regex בלבד, על ה-tree הנוכחי ועל 40 הקומיטים האחרונים של `smoke/last-run.md`. זו לא סריקה מלאה של כל ההיסטוריה.

## 6. אם משהו דלף

1. **לבטל או לסובב קודם.** הסוד נחשב דלוף מרגע ה-push, גם אם הקומיט נמחק אחר כך.
2. רק אחר כך לנקות את ה-tree. ניקוי היסטוריה (`git filter-repo`) בריפו ציבורי לא מבטיח כלום, כי forks, caches וסורקים כבר העתיקו.
3. לרשום ב-`STATUS.md`: מה דלף, מתי, ומה בוטל. בלי הערך עצמו.

## 7. בדיקה לפני push

```
git diff --cached | grep -nE 'eyJhbGciOi|postgres(ql)?://[^:]+:[^@]+@|neon\.tech|upstash\.io|-----BEGIN|sk-[A-Za-z0-9]{20}|gsk_|AKIA[0-9A-Z]{16}|@gmail\.com'
```
אם יש פלט: לעצור ולבדוק.

**אין בריפו סורק סודות שרץ על כל push או PR.** קיימים `omni_prod/secret_scan.py` וה-release gates (`scripts/run_v2*_release_gate.py`), אבל הם לא workflow שחוסם merge.
