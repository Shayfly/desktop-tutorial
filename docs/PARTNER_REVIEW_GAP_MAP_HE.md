# 148AI — Partner Review Candidate: תמונת מצב ומפת פערים (שלב 1)

נכתב: 2026-10-09 02:40 (Asia/Jerusalem). מקור: הקוד עצמו בענף `milestone/pre-staging-2026-10-05` בקומיט `b0a0cfa`, נתוני Vercel ו-GitHub Actions, ו-STATUS.md רק כמקור ראיות עם מזהי ריצה.
שלב זה הוא קריאה בלבד. לא שונה קוד, לא נדחף דבר ולא הוצא כסף.

## 0. סביבות ומקורות אמת

| פריט | מצב שנבדק | ראיה |
|---|---|---|
| ענף פעיל | `milestone/pre-staging-2026-10-05` @ `b0a0cfa` (2026-10-09 02:19) | `git ls-remote` |
| Preview (148aiv28) | READY על `b0a0cfa` | `dpl_yaSutesVYBzDyQBKjXWhwe2chKax` |
| Production (148aiv28) | עדיין `main@e8f2949` מ-23/9, קוד ישן | `dpl_9izMa4N2Ca1oMkwLcTM8JqXNgm4f` |
| CI | ירוק על `b0a0cfa` (v24-ci, V11 Overlay, Deploy build worker) | runs 37858766834, 37858766827, 37858766815 |
| Worker / Sandbox / Preview edge | Oracle `148ai-worker-01`, נפרס בכל push | Deploy build worker 37858766815 |
| מסד נתונים / תור / אחסון | Neon Postgres, Upstash Redis (RQ), R2 `omni-artifacts` | STATUS 2026-10-07: migrations, queue probe ו-storage probe עברו |
| ספקי מודלים | Gemini בתשלום עובד. OpenAI ו-Anthropic מוגדרים אבל אין בהם קרדיט | model-probe 37814803770 |
| תקציב QA | $10 בסך הכול, הוצאה אמיתית. נצרכו כ-$0.35 נכון ל-8/10 23:05 | build-evidence 37832677078 |
| בדיקות מקומיות | לא הורצו בסשן הזה, כי התקנת pip חסומה (DNS ל-pypi). מסתמך על CI | — |

**הסביבה המיועדת להדגמה:** Production מריץ קוד מלפני כל העבודה. אם מדגימים עכשיו, ההדגמה רצה על כתובת Preview. החלטה פתוחה: למזג ל-main ולפרוס, או לקבוע כתובת Preview קבועה.

## 1. ליבת ההדגמה (11 הסעיפים) — טבלת יכולות

| # | Capability | Code location | Implementation | Configuration | Verification | Evidence | Gap |
|---|---|---|---|---|---|---|---|
| 1 | כניסה ופתיחת פרויקט | `investor_app.py` `/api/v28/auth/*`, `/api/v28/projects`; `assets/app.js` | קיים | Postgres | VERIFIED (חי) | Golden E2E #1, 8/10 23:05 | אין חשבון בדיקה ייעודי לשותף |
| 2 | שיחת אפיון מקצועית בעברית | `product_architect.py::_material_questions` | **לא קיים כשיחה.** שדה טקסט אחד. השאלה היחידה היא באנגלית ונבחרת לפי מילות מפתח | — | NOT IMPLEMENTED | קוד, שורות 380–396 | **פער הליבה הגדול.** אין שיחה, אין שמירת הודעות, אין הסתעפות, אין סימון ידוע/הנחה/חסר, אין זיהוי סתירות |
| 3 | בחירת עיצוב והעדפות | `skills_runtime` (`skill.visual_design@1`, `3526dc5`) | המערכת בוחרת צבע ופונט אוטומטית. המשתמש לא נשאל | — | VERIFIED לבחירה האוטומטית בלבד (rehearsal 37858017258) | — | אין שלב העדפות. אין "בחרו עבורי" עם הסבר. אין רפרנסים או לוגו |
| 4 | סיכום, אומדן ואישור | `POST .../build-contracts` → `POST .../builds` (`build_contract_id` + fingerprint, QA reservation) | קיים. האישור נאכף בשרת ונקשר למפרט ולתקציב | Postgres | VERIFIED (חי) | `beb67b4` (409 על חוזה ישן), Golden E2E #1 | הסיכום חסר מסכים, "מה מחוץ להיקף" ותפקידים בעברית קריאה. `auth_session` תמיד True (`product_architect.py:62`), כך ש"בלי התחברות" לא מכובד בתשתית. אין כפתור "עדכן את הבקשה" מובנה |
| 5 | יצירת קוד וקבצים אמיתיים | `worker_tasks.py`, `routed_gateway.py` (Gemini) | קיים | Gemini paid | VERIFIED | `bld_f419acd1…` → `v_246bae81…` | ערימה טכנולוגית אחת בלבד (stdlib + SQLite) |
| 6 | הרצה, בדיקות ותיקון בתקציב | `remote_sandbox.py`, `repair_loop.py`, `qa_budget.py` | קיים | Oracle sandbox | VERIFIED | rehearsal 37814985551 (5 סבבים) | ה-QA קורא קוד ולא מפעיל את המוצר: אין בדיקות דפדפן או HTTP התנהגותיות |
| 7 | תצוגה חיה | `preview_runtime.py`, Caddy + sslip.io | קיים | `PREVIEW_DOMAIN_TEMPLATE` | VERIFIED | `prv-1760dedc…sslip.io` | **נתוני המוצר שנוצר נשמרים ב-/tmp ונמחקים כשה-Preview נעצר.** הקישור פתוח לכל מי שמחזיק בו ופג |
| 8 | שינוי בשפה טבעית וגרסה | `modification_*`, `POST .../modifications` | קיים | Postgres + R2 | VERIFIED | `mod_c14435dc…` → `v_0bc82ef7…` | אין ניתוח השפעה ואין אישור היקף לשינוי מהותי |
| 9 | בדיקת שינוי ושחזור | `POST .../rollback`, `restore_version_with_spec` | קיים | Postgres | VERIFIED | `mod_6ddd35a8…` על גרסה משוחזרת (STATUS שורה 415) | שחזור מהממשק טרם נבדק בתרחיש שותף |
| 10 | ייצוא | `GET .../export` | קיים | R2 | VERIFIED | ZIP של `v_0bc82ef7…` נפתח 8/10 22:59 | — |
| 11 | פרסום לסביבת יעד | `POST .../promote` → `unified_engine.promote` | **בזיכרון בלבד.** snapshot ב-dict בתוך פונקציית serverless | — | NOT VERIFIED | `unified_engine.py:328` | **אסור להציג כפרסום.** יש להציג "פרסום: לא זמין בגרסה זו" עד שיהיה יעד אמיתי |

## 2. ממצאים רוחביים

**מופעל בפועל במסלול המשתמש** (`app.js`): auth → projects → build-contracts → builds → poll → previews → modifications (latest/accept/reject) → history → rollback → export. אין קריאות ל-promote, branding או rights.

**רכיבים שקיימים אבל לא מחוברים למסלול:** 32 מתוך 49 תפקידים מוגדרים בקטלוג בלבד (`docs/AGENT_SKILL_STATUS.md`). ביניהם UX Designer, Data Engineer, Identity & Access, Release Agent, וכל משפחות המדיה, המשחקים והאוטומציה. בנוסף: Replicate (CONNECTED, אבל אף תמונה לא נוצרה), Stripe checkout, ו-rights/IP endpoints.

**מסלולים דטרמיניסטיים שעדיין חשופים:** `/api/demo/build`, `/api/live/build`, `/api/v25|v26|v27/.../build`, ו-`POST /api/v28/projects/{id}/build` ("zero-cost deterministic build"). הממשק לא משתמש בהם, אבל הם נגישים ב-API. יש לחסום אותם או לסמן אותם במפורש לפני מסירה לשותף.

**נשמר רק בזיכרון או זמנית:** פרסום (`_deployments`), runtimes של `hosted/v2x`, `MemoryBuildContractRepository` במצב reviewer, ונתוני המוצר שנוצר ב-Preview (`/tmp`).

**בדיקות:** CI ירוק. חלק ניכר מבדיקות היחידה רצות מול fake pool או mocks. הראיות החיות הן מזהי הריצה שבטבלה. כשל קצה לקצה לא מתבטל בגלל בדיקות ירוקות.

**Preview מול סביבת ההדגמה:** Preview = `b0a0cfa` עם worker מחובר. Production = `main@e8f2949`, בלי worker ובלי async builds.

**התנגשויות עבודה:**
- **סשן Claude אחר (`session_01XFEE73…`) דחף לענף הזה עד 02:19 הלילה** (Agent OS step 1, visual design skill, sandbox). כרגע אין ריצות CI פעילות. אסור לשני סשנים לדחוף לאותו ענף.
- ענפים שלא מוזגו מ-6/10: `feature/infisical-…` (7 קומיטים), `feature/qstash-…` (10), `feature/r2-generated-app-credentials-…` (9), `docs/system-audit-handoff-…` (2). אף אחד מהם לא חוסם את ליבת ההדגמה.
- המפרט הקודם `docs/AGENT_OS_SKILLS_RUNTIME_SPEC_HE.md` (8/10) נבלע במסמך הנוכחי. הסשן השני עובד לפיו.

**סתירות במסמכים:**
- הסטטוס "CI failing" מ-5/10 התיישן. CI ירוק.
- `AGENT_SKILL_STATUS.md` מסמן את Request Interpreter כ-VERIFIED, אבל הפער הרשום שם הוא "no clarification questions are asked". לפי המסמך החדש, VERIFIED צריך להתייחס ליכולת המוצהרת. מוצע לפצל ל-"Prompt→Contract: VERIFIED" ול-"Discovery conversation: NOT IMPLEMENTED".
- קבצי `CURRENT_TRUTH_V24–V28`, `VALIDATION_*` ו-`RELEASE_NOTES_*` הם היסטוריה. מקור האמת הוא STATUS.md יחד עם הטבלה הזאת.

## 3. מה חוסם "Partner Review Candidate" (לפי סעיף 18)

| תחום | מצב | חוסם? |
|---|---|---|
| אפיון | אין שיחה, אין העדפות | **כן** |
| אישור | נאכף בשרת | לא. נדרש רק להעשיר את הסיכום |
| יצירה | אמיתית | לא |
| איכות | הדגמה אחת עברה בסביבה הפרוסה. נדרשים 3 תרחישים, כולל ניסוח חדש | **כן** (טרם בוצע) |
| נתונים | נתוני המוצר שנוצר אובדים ב-/tmp | **כן** |
| התאוששות | רענון ושינוי כפול תוקנו (`fe84c4d`). אין ביטול, ואין המשך build שנקטע | חלקי |
| גרסאות | שינוי ושחזור עובדים | לא |
| עלויות | ספר קיים. עלות האפיון לא נמדדת (היום $0 כי אין מודל) | חלקי |
| עיצוב | אין בדיקה חזותית של 148AI עצמו במובייל ובמחשב | **כן** (טרם בוצע) |
| מסירה | Preview וייצוא עובדים. "פרסום" מטעה | **כן** (עד שיוסתר או יסומן) |

## 4. תוכנית עבודה מוצעת (סעיף 20)

| # | מטרה | קבצים | תלות | תנאי קבלה | בדיקה | עלות משוערת |
|---|---|---|---|---|---|---|
| 1 | שיחת אפיון: מודל נתונים ושמירה | migration חדשה (`intake_sessions`, `intake_messages`), `intake_repository.py` | — | רענון שומר הודעות. הודעה כפולה (idempotency key) לא יוצרת שתי פעולות | Postgres חי | $0 |
| 2 | מנוע אפיון: קבוצות שאלות, ידוע/הנחה/חסר, סתירות, "בחרו עבורי" | `intake_engine.py` + Skills לפי תחום (Web ומערכת עסקית תחילה) | 1 | שיחה בעברית, ללא שאלה חוזרת. "בלי התחברות" מול "מידע פרטי" מעלה בירור | יחידה + שיחה חיה | ~$0.01–0.03 לשיחה, נמדד בספר |
| 3 | העדפות עיצוב בחוזה | `build_contract.py`, `skill.visual_design` | 2 | הבחירה עוברת ל-generator ומופיעה בסיכום | rehearsal | ~$0.07 |
| 4 | מסמך הבנה ואישור | `app.js`, build-contracts | 2–3 | כל 10 הסעיפים של סעיף 5. "עדכן" יוצר revision חדש. אישור מחדש נדרש | דפדפן + API | $0 |
| 5 | no-login אמיתי והרשאות מוצר | `product_architect.py` | 2 | "בלי התחברות" לא מוסיף auth. מידע פרטי מחייב בירור | rehearsal | ~$0.07 |
| 6 | נתוני מוצר עמידים ב-Preview | `preview_runtime.py` (volume לכל preview) | — | נתונים שורדים restart של ה-preview | חי על Oracle | $0 |
| 7 | פרסום: הסתרה או סימון כלא זמין, וחסימת מסלולים דטרמיניסטיים | `investor_app.py`, `app.js` | — | אין הצלחה שקרית | API | $0 |
| 8 | מצבי מסך ובדיקה חזותית | `app.css`, `app.js` | 4 | 10 המצבים של סעיף 6, מחשב ומובייל | צילומי מסך | $0 |
| 9 | QA: 3 תרחישי ההדגמה + ניסוח חדש + כשל מבוקר | — | 1–8 | מטריצת קבלה עם ראיות | Preview פרוס | ~$0.5–1.0 מתוך ה-$10 |
| 10 | הקפאה וחבילת מסירה | docs | 9 | סעיף 19 | הדגמה מסביבה נקייה | $0 |

סה"כ הוצאה צפויה: כ-$1–2 מתוך יתרה של כ-$9.6.
