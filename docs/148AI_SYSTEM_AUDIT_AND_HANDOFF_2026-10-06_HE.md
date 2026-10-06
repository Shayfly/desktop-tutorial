# 148AI — סקירת מערכת ונקודת המשך, 6 באוקטובר 2026

**מסקנה:** המערכת במצב `M5_PARTIAL`. יש בסיס קוד משמעותי, CI ירוק ו־Preview פעיל עם חשבון ופרויקטים. אין עדיין הוכחה למסלול יצירה חיה מלא או למוכנות להשקה. יצירת החיבורים התקדמה; נותרו התאמות קוד, תשתית הרצה והוכחות חיות. אין להבטיח שכל המוצר יסתיים ביום עבודה אחד.

**סיבת המסמך:** שי ביקש לעצור את שינויי המערכת לפני השינה, לשמור את כל הידוע ולבצע סקירה ותוכנית עבודה מעמיקה. בסבב זה נבדקו המקור, תוצאות CI, מסמכי המשימה והתיעוד הרשמי. לא שונו הגדרות, לא הופעלו קריאות ספק בתשלום ולא הורץ קוד של לקוח.

## 1. נקודת המשך מדויקת

| פריט | מצב שנשמר |
|---|---|
| מאגר | `Shayfly/desktop-tutorial`, פרטי |
| ענף העבודה של ה־Preview | `milestone/pre-staging-2026-10-05` |
| מקור שנפרס | `79b9ba785aff5e2c29c068ade94bbdf2f24d8f33` |
| שינוי Infisical | PR #2 מוזג ב־squash לענף ה־Preview; לא ל־main |
| פרויקט Vercel הנכון | `148aiv28` תחת ShayFly's projects |
| ה־Preview האחרון | https://148aiv28-7q10wt56u-shayflys-projects.vercel.app |
| כתובת ה־Preview הקודמת | https://148aiv28-p0y7g1ln7-shayflys-projects.vercel.app |
| הפריסה האחרונה | Vercel הראה Ready, Preview, commit 79b9ba7; לפי צילום משתמש |
| פרויקט הבדיקה | „בדיקת שמירה”; קיים גם „כדורגל” |
| הבקשה הקנונית להמשך | אתר ווב לניהול משימות בדפדפן: הוספת משימה, סימון כהושלמה ומחיקה. בבנייה הזאת נדרש ווב בלבד. |
| מקום העצירה | חסם מסד הנתונים נעלם אחרי הוספת ההפניה ו־redeploy. טרם נפתח/נוצר Bucket ייעודי לאתרים שנבנים |
| Production | נפרד, מקור main; לא להשתמש בו לבדיקות אלה ולא להחליף את מסד החשבונות |
| המסמך לביצוע | [תוכנית ההמשך](superpowers/plans/2026-10-06-system-completion-roadmap.md) |

הכתובות הועתקו מצילומי המסך; כתובת הפריסה וה־SHA יאומתו בתחילת הסבב הבא לפני כל פעולה. הפריסה החדשה הציגה שוב את החשבון ואת הפרויקטים אחרי redeploy: ראיה לשימור הנתונים שנראו, אך אינה מחליפה בדיקת גרסאות/קבצים או בידוד בין שני משתמשים.

## 2. גבולות הבדיקה והראיות

- נסרק אינדקס המאגר בקומיט 79b9ba7: **510 רשומות קבצים ותיקיות**, ללא truncation. זו סקירת מבנה, לא טענה שכל שורת מקור נבדקה.
- נקראו מסמכי ההנחיות, המשימה והאמת; ונבדקו קובצי הליבה של accounts/API, sessions, frontend, provisioning/secrets, costs, model routing, storage, workers/queues, preview/sandbox, billing, backup ו־readiness. רשימת כיסוי בסעיף 12.
- נבדקו מחדש **תוצאות ה־CI של הקומיט שנפרס עצמו**. לא הסתפקנו ב־CI של ענף ה־PR.
- צילומי המשתמש מוכיחים מה שהממשק מציג. היעלמות חסם מוכיחה מעבר בדיקת configuration, לא login מול ספק או write/readback.
- לא התקבלה גישה מורשית ל־Vercel API עבור scope הפרויקט: ניסיון קודם הוחזר 403. אין בסבב זה גישה לסודות, ל־runtime logs המאומתים או לנתוני ספקים.
- סביבת הפקודות המקומית לא הייתה זמינה בסבב הפיתוח הקודם; בסקירה זו נשענו על GitHub API ועל logs קיימים, ולא נטען שהרצנו מחדש בדיקות מקומיות.
- לא בוצע penetration test, לא בוצע restore אמיתי, ולא נבדקה כל אינטגרציה חיה. אין מסקנה „הכול תקין”.
- הסקירה היא של Agent הראשי. reviewer עצמאי שהתבקש בסבב Infisical לא החזיר תוצאה; אין להציג זאת כסקירה עצמאית שעברה.

### CI מאומת כעת

| Workflow | Run | מקור | תוצאה |
|---|---:|---|---|
| v24-ci | 37387869988 | 79b9ba7, push לענף Preview | success |
| V11 Overlay CI | 37387869872 | 79b9ba7 | success |
| v24-ci / test | job 112025651400 | Python 3.12 | compileall, pytest, hostile static, international gate: success |
| v24-ci / compose-config | job 112025651091 | אותו מקור | success |

פלט pytest: **819 passed, 55 skipped, 1 warning, 95 subtests passed**. אזהרת Starlette/AnyIO deprecated קיימת; אזהרות גרסאות GitHub Actions קיימות. 55 skips אינם הצלחה חיה: יש למפות אילו מהם חוסמים את הסלייס, להריץ עם prerequisites נכונים ולדרוש PASS. Compose config מוכיח syntax/config rendering, לא שרת עובד.

קישורי ראיות:
- https://github.com/Shayfly/desktop-tutorial/actions/runs/37387869988
- https://github.com/Shayfly/desktop-tutorial/actions/runs/37387869872
- https://github.com/Shayfly/desktop-tutorial/pull/2

## 3. מפת המערכת

### שכבת הפלטפורמה

Vercel מארח את הממשק וה־FastAPI/control plane. Neon `148ai-db` שומר חשבונות, פרויקטים, חוזי בנייה, עבודות ו־bindings. R2 `omni-artifacts` מיועד לקוד/ארטיפקטים של הפלטפורמה. Redis/RQ מיועד לתורים. עובד חיצוני אמור לצרוך אותם, לפנות לספקי AI ולשלוח קוד לסביבה מבודדת.

### שכבת המוצרים שנבנים

לכל אתר שנבנה נדרשים role/schema ב־Postgres הייעודי, signing secrets ב־Infisical, גישה מצומצמת לאחסון, ובהתאם לחוזה scheduler/outbound. אלה חיבורים שונים מחיבורי הפלטפורמה. המוצר הנוצר לא מקבל admin DSN, מפתח R2 ראשי, Infisical Client Secret או credentials של Vercel.

### הבחנות קריטיות

- `Preview` של 148AI ב־Vercel אינו תצוגה מקדימה של האתר שנבנה.
- `Ready` של Vercel פירושו שהפלטפורמה נפרסה; לא שה־worker/sandbox פועלים.
- `configured` או `PARTIAL` אינם `LIVE`.
- `LIVE` של binding צריך להיקרא לפי ראייתו: secret readback אינו הוכחת מייל שנשלח, ו־scheduler health אינו משימה שהורצה.
- תכנון וחוזה שסומנו בירוק אינם ראיה לקוד שנוצר.
- מפתחות `OMNI_S3_*` הם של הפלטפורמה; `OMNI_GENAPP_S3_*` הם של המוצרים הנוצרים.

## 4. מלאי חיבורים ומצב אמת

| תחום | מה ידוע בפועל | סטטוס והוכחה חסרה |
|---|---|---|
| GitHub | PR2 מוזג לענף Preview; מקור נגיש; CI ירוק | מאומת לקומיט 79b9ba7. main נפרד ולא נבדק במלואו בסבב זה |
| Vercel Preview | redeploy Ready; login ופרויקטים מוצגים | חי עבור המסכים שנצפו; runtime tracing, headers, quotas ו־rollback עדיין חסרים |
| חשבונות ב־Neon | query לפי email החזיר 1; login עובד; פרויקטים חזרו לאחר redeploy | ראיה טובה ל־creator persistence; שני משתמשים, גרסאות, concurrency ו־restore עדיין לא אומתו בסביבה זו |
| Neon הפלטפורמה | 148ai-db/main/neondb; bootstrap רץ בעבר על schema ריק | לא להריץ שוב bootstrap ריק. להשלים בדיקת migrations/read-only והלימה לקוד |
| Redis | 148ai-redis ב־Vercel: Available | לא הוכחה ל־RQ. חסרים OMNI_REDIS_URL runtime, TLS/PING, enqueue/dequeue ו־worker heartbeat |
| R2 הפלטפורמה | omni-artifacts פרטי; token Object Read/Write; config נוספה | חסר write/read/hash/delete אמיתי דרך אותה סביבת runtime |
| Infisical | EU, 148AI-generated-apps, Machine Identity 148AI-server/Member/Universal Auth; adapter נוסף | config נקלטה. אין עדיין הוכחת auth/create/read/rotate/delete חיה |
| Neon המוצרים הנוצרים | 148ai-generated-apps נוצר דרך Vercel; Frankfurt; Free; Auth False; Preview בלבד; GENAPP prefix | admin reference נקלטה. role creation, schema permissions, login, read/write/isolation ו־cleanup חסרים |
| Generated-app auth | „מוגדר, לא נבדק” | אין עדיין secret readback + generated runtime session proof |
| Generated-app object storage | עדיין חסר | Bucket/token ייעודיים ו־R2 issuer בקוד נדרשים; AWS STS adapter קיים אינו הוכחת התאמה ל־R2 |
| Scheduler | URL/token reference חסרים | בנוסף לחיבור צריך create/run/retry/cancel אמיתי; health בלבד אינו מוכיח scheduled jobs |
| Outbound | „מוגדר, לא נבדק” | כרגע בעיקר signing-secret binding. SMTP/Resend delivery אינו מוכח |
| Code AI/model | gateway/routing/usage קיימים במקור | אין ראיית קריאת model חיה בפריסה הזו. localhost default אינו ספק חי בענן |
| Image provider | כל שדות החיבור/מחיר חסרים | adapter מסוג prediction API; יש לבחור ספק תואם או לממש adapter מתאים |
| Sandbox | remote/docker executor קיימים | host, isolation, limits, egress, install/build/test וניקוי אינם מוכחים כעת |
| Generated preview | DockerPreviewProvider + routes + behavioral acceptance בקוד | host/router/domain/TLS/stop/expiry אינם מוכחים בסביבה הנפרסת |
| Publishing | כפתור מפרסם מציג שאינו מוגדר; יצוא מושבת ללא גרסה | adapter ופרסום אמיתי של מוצר נוצר לא אומתו |
| Stripe/subscriptions | signed webhook ו־entitlement code קיימים | checkout/webhook/replay/refund/failed-payment/reconciliation חיה חסרים |
| Email identity | token lifecycle/routes קיימים | חסרים flow מלא: יצירת token, משלוח, קישור, consume/reset; יש לבדוק את wiring הקיים |
| Google/Apple login | דרישת mission; אין ראיה ל־callbacks בפריסה הנוכחית | מסלול email/password שנצפה אינו OAuth; דורש מימוש/קונפיג ובדיקות callback |
| Operations | modules עבור observability/health/backup/recovery | ניטור שירותים, alert, backup restore, incident drill אינם מוכחים |
| Android/iOS | חוזים/מקור/חתימה בחלקים שונים | אין אפליקציה חתומה ומאומתת. Web-first; native מסלול נפרד אחרי הצלחת Web |

## 5. הגדרות שנשמרו — שמות בלבד

### הפלטפורמה (ערכים קיימים אינם נחשפים במסמך)

- `OMNI_CREATOR_PERSISTENCE=postgres` הוגדר ל־Preview.
- `OMNI_DATABASE_URL` של הפלטפורמה; לא להחליף ב־GENAPP.
- `OMNI_S3_ENDPOINT`, `OMNI_S3_BUCKET`, `OMNI_S3_REGION`, `OMNI_S3_ACCESS_KEY`, `OMNI_S3_SECRET_KEY`.
- R2 bucket של הפלטפורמה: `omni-artifacts`; region `auto`.
- `OMNI_REDIS_URL`: דורש אימות שהוא אכן מוגדר ב־runtime, ושזה Redis protocol URL ולא REST endpoint.
- model/live-build/sandbox env: אין אישור מחובר; לברר דרך בדיקת נוכחות/לוגים מוסתרים בלבד.

### Infisical — Preview בלבד לפי פעולות המשתמש

- `OMNI_GENAPP_SECRET_STORE_PROVIDER=infisical`
- `OMNI_INFISICAL_BASE_URL=https://eu.infisical.com`
- `OMNI_INFISICAL_PROJECT_ID=6c03de5e-5017-44f2-819e-739f5541706b`
- `OMNI_INFISICAL_CLIENT_ID` = Client ID של Universal Auth, **לא** Machine Identity ID.
- `OMNI_INFISICAL_CLIENT_SECRET`: הועתק privately; לא נקרא על ידי assistant.
- `OMNI_INFISICAL_ENVIRONMENT`: לא הוגדר במפורש; הקוד משתמש ב־`dev`.
- secret store adapter שומר שמות `GA_<sha256(logical reference)>` ב־root. הפניות `vault:` נשארות logical IDs; אין צורך במוצר HashiCorp Vault במסלול Infisical.
- לא נוצר cluster Vault בתשלום לפי הידוע. אם יש ספק, לבדוק Active resources/Billing באופן קריא בלבד.

### Neon ייעודי למוצרים — Preview

- `GENAPP_DATABASE_URL`, `GENAPP_DATABASE_URL_UNPOOLED` ועוד משתני `GENAPP_*` של האינטגרציה.
- `OMNI_GENAPP_DATABASE_ADMIN_DSN_REF=env:GENAPP_DATABASE_URL_UNPOOLED`, Config, Preview.
- שם המשתנה המלא של UNPOOLED הוסתר חלקית בצילום. חסם configuration נעלם, אך live resolution של הערך עדיין חייב להיבדק. אין להניח שהיעלמות החסם לבדה מאמתת את השם/ערך.
- Frankfurt, Auth False, ללא create-branch-per-deployment, Sensitive למשתנים שנוצרו.

## 6. החסמים האחרונים שהוצגו בפריסה

1. `infrastructure_object_storage_not_configured`
   - OMNI_GENAPP_S3_ENDPOINT
   - OMNI_GENAPP_S3_BUCKET
   - OMNI_GENAPP_S3_ACCESS_KEY_REF
   - OMNI_GENAPP_S3_SECRET_KEY_REF
   - לאחר הוספתם, הקוד הנוכחי ידרוש גם ROLE_ARN/STS — צריך לטפל ב־R2 קודם, ולא להמציא ARN.
2. `infrastructure_scheduled_http_not_configured`
   - OMNI_GENAPP_SCHEDULER_URL
   - OMNI_GENAPP_SCHEDULER_TOKEN_REF
3. `image_provider_not_configured`
   - OMNI_IMAGE_PROVIDER_BASE_URL
   - OMNI_IMAGE_PROVIDER_API_KEY_REF
   - OMNI_IMAGE_PROVIDER_MODEL
   - OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE
   - OMNI_IMAGE_PROVIDER_PRICE_SOURCE
4. `cost_quote_unknown`
   - מחיר media.image.generate חסר.
   - OMNI_GENAPP_PROVISIONING_MAXIMUM_USD חסר לכל חמשת kinds.
   - UNKNOWN אינו 0; אין למלא אפס רק כדי לפתוח את כפתור האישור.

חסם DATABASE configuration נעלם. auth_session/outbound configuration blockers נעלמו קודם. לא הופיעה דרישת Android בבקשת ה־Web המצומצמת.

## 7. ממצאי קוד חשובים וסדר חומרה

אלה ממצאים מהמקור, עם ההבחנה בין התנהגות קריאה מוכחת לבין סיכון שיש לשחזר בבדיקה. הם לא תוצאות תקיפה של הסביבה החיה.

### A1 — שימוש חוזר ב־binding LIVE מדלג על re-verification — P0 לפני credential expiry

מקור: `omni_prod/infrastructure_provisioner.py`, `InfrastructureProvisioningService._provision_one` ו־`cost_quotes`.
שניהם מסתמכים על `existing.live`; `_provision_one` מחזיר את הקיים בלי `provisioner.status(existing)`. לעומת זאת, `ManagedWebSaaSProvisioner.status` יודע לחסום scoped credentials שפגו.
**סיכון:** credentials זמניים שפגו או משאב שנשלל עלולים להישאר מוכרזים LIVE ולהתקבל ב־gate; quote יכול להצהיר reuse ללא בדיקת תוקף.
**סיום:** בדיקת clock/expiry שמוכיחה BLOCKED/recovery; freshness נרשמת durable; renew נעשה עם idempotency ולא עוקף עלות.

### A2 — ה־integration gate של התשתית עדיין Vault-only — P1 מיידי

מקור: `tests/integration/test_m5_managed_web_saas_live.py`.
REQUIRED וה־skip check מחייבים `OMNI_GENAPP_SECRET_STORE_URL` וטוקן Vault גם כשנבחר Infisical; דורשים ROLE_ARN ללא הבחנת R2.
**תוצאה:** נתיב ה־live החדש עלול להישאר skipped למרות config תקפה.
**סיום:** prerequisite checker לפי provider; tests עבור Vault/Infisical ו־AWS/R2; בדיקת Infisical standalone אמיתית עם cleanup. להריץ בדיקות חיות מוגדרות ולפסול SKIP.

### A3 — worker רגיל לא צורך תור stop/cleanup של preview host — P1

מקור: `omni_prod/worker.py` מאזין רק ל־`omni-builds`. `queueing.preview_host_queue` ו־DELETE preview שולחים ניקוי ל־`omni-preview-host-<host>`.
**סיכון:** פריסה לפי worker.py בלבד תשאיר ניקוי בתור ללא צרכן.
**סיום:** worker launcher מאזין לשני התורים או manifest מפורש; בדיקה cross-host ו־STOPPED שנעשה CLEANED פיזית.

### A4 — R2 credential issuer טרם מומש במסלול generated-app — P0 לפני storage LIVE

מקור: `StsCredentialIssuer` קורא AWS `AssumeRole` עם role ARN/session policy. דרישת ROLE_ARN נאכפת ב־config.
Cloudflare מתעדת Temporary Credentials API ולחלופין local JWT signing, עם bucket/prefix scope.
**סיום:** issuer ייעודי, בחירת provider מפורשת, TTL/session token, ראיות allowed-prefix ו־denied-cross-project/environment; בלי מסירת operator token למוצר.

### A5 — בדיקת storage חיובית חלשה יותר משמה — P1

`S3ProbeBackend.verify` מבצע PUT ו־DELETE; אין בו GET והשוואת bytes. הוא מוכיח write/delete בלבד. בדיקת deny חיה מתמקדת sibling environment; cross-app isolation נבדק גם ב־fixtures אך דורש live.
**סיום:** PUT/GET/checksum/DELETE, LIST prefix אם נדרש; cross-app ו־cross-environment deny עם sentinel קיים. 404 לא נחשב permission denial.

### A6 — health/signing secret אינם scheduler delivery או email delivery — P1 truth/behavior

`_provision_scheduled_http` מאמת health ומפתח callback, ומחזיר binding LIVE; אינו רושם משימה או מוכיח delivery.
`_provision_outbound` מציין `email_live_verified=False`; signing secret alone אינו משלוח מייל.
**סיום:** evidence נפרד לשירות/feature; schedule→receive→verify→retry/cancel; outbound webhook ומייל לפי בקשה, ללא claim רחב.

### A7 — backup drill הנוכחי סימולציה — P0 לפני production

`omni_prod/recovery_drill.py` כותב `SIMULATED-DB-BACKUP` ומשווה bytes. זו בדיקת manifest/תרגיל logic, לא restore של Postgres/Neon.
**סיום:** snapshot/dump אמיתי restored ליעד נפרד; migrations/rows/versions/artefact hashes מאומתים; הזמן והכשל נמדדים.

### A8 — הודעת 401 בממשק מטעה — P2 מהיר

`assets/app.js::explain` מתרגם כל 401 ל־session expired, גם `invalid credentials` ב־login. כך נוצר אבחון שגוי במסכים.
**סיום:** הודעה לפי error code/context; bad password שונה מ־expired session; לא לחשוף אם email קיים.

### A9 — readiness ציבורית אינה מכסה את כל מסלול הבנייה — P1

`_m5_status_payload` מזהה durable workspace ו־configuration של infrastructure/image. הוא אינו מוכיח worker, queue dequeue, model call, sandbox או preview router. `_model_gateway_and_executor` דורש OMNI_ENABLE_LIVE_BUILD=1 ועוד endpoint/docker בפועל.
**סיום:** preflight אמיתי עם ראיות זמן/מקור/סביבה ורק בדיקות לא מחייבות הוצאה; מזהה חסר לפני reserve/build.

### A10 — ניסיונות concurrent provisioning/rotation דורשים בדיקה — P1, סיכון לבדיקה

ה־service קורא existing, מפעיל external effects ואז שומר. record upsert אינו לבד מוכיח single-writer להקמת role ושינוי password. role/password נוצרים לפני secret readback.
**סיכון שיש לבדוק:** שני workers או crash בין שינוי DB לסוד יכולים להשאיר credential mismatch/secret rotation לא מתואמת.
**סיום:** durable lease/advisory lock ברמת resource, operation journal ו־compensation/recovery; fault injection בכל boundary; rerun לא מבטל credentials של build שכבר משתמש במשאב.

### A11 — בידוד Postgres טרם הוכח — P0 לפני מסירת runtime למשתמש

`verify_login` מוכיח login ו־write schema; אינו מוכיח DENY ל־schema של משתמש אחר/role admin. string comparison מול control DSN אינו מדיניות הרשאות מלאה. נוצר Neon project נפרד כדי לצמצם ערבוב, ועדיין יש לבדוק grants/default PUBLIC privileges.
**סיום:** משתמש A לא יכול read/write/admin ל־B; אין הרשאות superuser/role creation ל־generated role; sessions/search_path תקינים.

### A12 — מחירים והוצאות אינם מחוברים עדיין — P0 לפני paid build

הקוד נועל build כשמחיר לא ידוע, וזה נכון. provisioning quote כללית לכל kind דורשת תיעוד יחידות; Free quota אינו הוכחת עלות 0 לכל שימוש עתידי. בדיקת ceilings עבור paid primary/local flag נדרשת כדי לא לסווג ספק מסחרי כ־local ולדלג על budget.
**סיום:** מחיר מקור/תאריך/יחידה; reservation לפני side effects; actual stays NULL אם לא נמדד; reconcile ספק/ledger/build אחד.

### A13 — שמירת מצב UI ובקרת Production — P2

ה־UI חוזר לפרויקט ראשון ומנקה plan/build state בבחירה; זה תרם לחזרות ידניות. Production main וה־Preview שונים, והודעות Redeploy כלליות בלבלו בין הסביבות.
**סיום:** restore פרויקט/עבודה פעילה durable; environment+commit בממשק admin; checklist אחד ולא צילום לכל קליק.

## 8. מה אכן תקין ומה לא נסגר

**תקין בטווח הראיות:** Source compile/regression על הקומיט שנפרס; חסימה כשעלות/תשתית חסרות; הפרדה בקוד בין platform/generated credentials; HttpOnly cookie transport ו־same-origin checks בקוד; Infisical opt-in עם deny redirects ו־sanitized errors; UI עובד ומציג פרויקטים; generated-app DB configuration החדשה נקלטה.

**לא נסגר:** provider live calls, Infisical lifecycle, generated role isolation, R2 roundtrip/scoped delegation, scheduler delivery, worker/queue recovery, AI output arbitrary apps, isolated preview, ZIP persistence/tenant controls, publish, billing, OAuth/email recovery, monitoring ו־restore.

**לא נדרש להקים מחדש:** החשבון הקיים; מסד creator; bootstrap; פרויקט Infisical; פרויקט Neon החדש. לא לפתוח Vault cluster בתשלום ולא למחוק נתונים כדי „להתחיל נקי”.

## 9. שינוי שיטת העבודה כדי להאיץ

1. התקדמות לפי תוצר שנבדק: חיבור רשום → probe → negative test → evidence, לא לפי מספר משתנים.
2. להכין מראש חבילת env names, מדיניות scope והשלבים לכל ספק; המשתמש מבצע רק פעולות חשבון/סודות שאיננו יכולים לעשות.
3. פיתוח adapters ובדיקות אינו מחכה לצילום מסך. פעולות config תלויות משתמש מרוכזות בסבב אחד.
4. לקרוא readiness אחת מרוכזת ולא לחזור על plan/redeploy לכל משתנה.
5. לאשר Preview source/env פעם אחת בתחילת batch, לעשות redeploy אחד אחרי batch מתואם.
6. לחסום build שאין לו worker/model/sandbox עוד לפני reservation. לא להמתין שיהפוך QUEUED לנצח.
7. כל משימה: reproducer/RED→minimal fix→PASS→live probe אם רלוונטי→evidence→commit/PR.
8. בתחילת יום לקרוא מסמך זה + תוכנית. בסיום לתעד SHA, deploy URL, blockers ושינוי סטטוס בלבד.
9. לא להרחיב ל־native/media families לפני 3 Web apps אמתיים; לא להוריד את M5 required floor בלי שינוי spec מפורש.
10. זמן כולל הוא תחזית בלבד; blockers external-account תלויים בגישה/תקציב. לא לקרוא לתוכנית „הבטחה לסיים מחר”.

## 10. קריטריוני סיום

### Working staging slice

שלוש בקשות שונות יוצרות repository אמיתי דרך model, install/build/test עוברים בסביבה מבודדת, preview נגיש ומתנהג נכון, הנתונים והגרסאות נשמרים, שני משתמשים מבודדים, edit/repair/rollback/ZIP עובדים, budget וה־ledger ניתנים לשחזור. ההוכחות על אותה פריסה ומקור.

### Production release

בנוסף: OAuth/email recovery בהתאם ל־mission, payment webhooks/entitlements מאומתים, publishing אמיתי של מוצר נוצר, backup restored, hostile isolation, cancellation/crash/retry recoverability, observability/alerts, תנאי שימוש/פרטיות/מסלולים, domain/TLS, quotas/abuse controls ו־rollback. מותר להשיק scope Web אמיתי ומוצהר; אין להציג native כבנוי.

### Native expansion

Android/iOS מקבלים פרויקט/spec נפרדים: cross-platform/source strategy, device tests, signing, distribution, subscriptions/store rules ו־operational ownership. הם אינם נפתרים בהוספת API key או בתצוגה מותאמת לטלפון.

## 11. תיעוד חיצוני שנבדק

- Cloudflare R2 temporary credentials: https://developers.cloudflare.com/r2/api/s3/temporary-credentials/
- API: https://developers.cloudflare.com/api/resources/r2/subresources/temporary_credentials/
- דוגמה כולל allowed/denied: https://developers.cloudflare.com/r2/examples/authenticate-r2-temp-credentials/
- Vercel Functions limits: https://vercel.com/docs/functions/limitations
  - repo config כיום maxDuration=60 עבור app.py; docs מאפשרות יותר בחלק מהמסלולים. אין צורך להאריך כדי להפוך בקשת API לעובד durable.
- Upstash compatibility: https://upstash.com/docs/redis/overall/compatibility
- RQ connection semantics: https://python-rq.org/docs/connections/

אין במסמך המלצה לרכוש שירות מסוים בלי בדיקת מחיר/גישה. בחירת worker host/sandbox provider מחייבת החלטת תשתית עם מחיר ותנאי שימוש עדכניים, בלי ליצור משאב בתשלום קודם.

## 12. כיסוי מקור ותיעוד

מסמכי סמכות: AGENTS.md; PRODUCT_MISSION_AND_ACCEPTANCE.md; 00_START_HERE_HE.md; CURRENT_TRUTH_V28_HE.md; STATUS.md; GOVERNANCE.md; COST_MODEL.md; M5_VALIDATION.md; M5 design/plan.

קוד/הגדרות שנבדקו בסקירה או בסבב העבודה שנבדק מחדש: investor_app.py; assets/app.js; assets/sw.js; browser_session.py; identity_lifecycle.py; db.py; storage.py; infrastructure_provisioner.py; providers/managed_web_saas.py; secrets_manager.py; product_architect.py; build_cost_plan.py; build_budget.py; model_runtime_config.py; model_gateway.py; routed_gateway.py; providers/llm_provider.py; providers/image_provider.py; worker_tasks.py; worker.py; queueing.py; build_outbox_relay.py; preview_runtime.py; remote_sandbox.py; deployment_runtime.py; web_saas_acceptance.py; stripe_billing.py; launch_readiness_v28.py; integration_center.py; health.py; worker_health.py; backup_manifest.py; recovery_drill.py; secret_scan.py; .env.example; vercel.json; docker-compose.international.yml; .github/workflows/v24-ci.yml.

בדיקות שנבדקו/ראיות קודמות שנשמרו: test_infisical_secret_store.py; test_m5_generated_app_storage_isolation.py; integration/test_m5_managed_web_saas_live.py; integration/test_live_stack.py; full CI logs על 79b9ba7.
יש מסמכים היסטוריים עם טענות live על סביבה אחרת/תאריך אחר. לא להשתמש בהן כהוכחה לסביבת Vercel הנוכחית.

## 13. הוראות פתיחת הסבב הבא

1. לקרוא מסמך זה, המשימה ותוכנית ההמשך.
2. לאמת ענף/מקור/URL ולעצור אם השתנו במקביל.
3. להתחיל ב־A1/A2/A3 ומסלול preflight, תוך הכנת adapter R2.
4. probe Infisical ו־Neon generated DB בנפרד לפני build מלא.
5. המשתמש נדרש בהמשך רק לבחור/לחבר compute host וספקי AI וליצור Bucket/token ייעודיים כשקוד החיבור והעלות מוכנים.
6. לא לבקש Client Secret, password, token או DSN בצ'אט. לקבל צילום שמות/סטטוס בלבד.
7. לא לתאר „הכול נשמר” כגיבוי מסדי הנתונים: המסמך שומר ידע ונקודת המשך; source שמור ב־Git; נתוני המשתמש נשארים בשירותים הקיימים ולא גובו בסקירה זו.
