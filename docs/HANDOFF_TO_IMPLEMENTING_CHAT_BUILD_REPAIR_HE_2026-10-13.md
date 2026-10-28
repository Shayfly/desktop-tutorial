# הוראות ביצוע להעברה לצ'אט המפתח של 148AI — Build/Test/Repair/Verify

**מסמך זה מיועד להעתקה ישירה לצ'אט שמבצע עבודת קוד ב-GitHub וב-Vercel.**

אני מאשר להמשיך בפיתוח אב־הטיפוס הפרטי של 148AI לפי התוכנית הקיימת, בצירוף הנספח החדש, בלי לפגוע במימושים הקיימים. **אל תתחיל לבנות מנוע נוסף, אל תשכתב רכיבים עובדים ואל תתחיל מ-Production.**

## חובה לקרוא לפני כתיבת קוד

1. מסמך האב T01–T09: https://github.com/Shayfly/desktop-tutorial/blob/audit/148ai-engineering-recovery-t01-2026-10-13/docs/ENGINEERING_RECOVERY_T01_T09_2026-10-13.md
2. **מפרט השילוב החדש, הכולל File Map, חוזים, שלבי ביצוע ו-20 בדיקות:** https://github.com/Shayfly/desktop-tutorial/blob/audit/148ai-engineering-recovery-t01-2026-10-13/docs/BUILD_REPAIR_CORE_INTEGRATION_SPEC_HE_2026-10-13.md
3. מסך אבחון חסימות ומוכנות פרויקט: https://github.com/Shayfly/desktop-tutorial/blob/audit/148ai-engineering-recovery-t01-2026-10-13/docs/PROTOTYPE_READINESS_AND_BLOCKER_DIAGNOSTICS_P0_HE_2026-10-13.md
4. מעקב תוכנית: https://github.com/Shayfly/desktop-tutorial/issues/23
5. מעקב מוכנות: https://github.com/Shayfly/desktop-tutorial/issues/26
6. PR מסמכי תוכנית (Draft): https://github.com/Shayfly/desktop-tutorial/pull/24
7. PR לתיקוני T01/CI (Draft, ענף מקביל!): https://github.com/Shayfly/desktop-tutorial/pull/25

## משימתך

### שלב 0: מיפוי ואימות (ללא קריאות מודל בתשלום)
- קרא את HEAD העדכני של ענפי הקוד, הדוקומנטציה וה-Preview, וקבע מקור עבודה ומפת מיזוג שאינה דורסת PR #25. בצע git diff/compare והצג את ה-SHAs. אל תניח שה-SHAs במסמך עדיין עדכניים.
- עבור בפועל על autonomous_core.py, repair_loop.py, build_budget.py, repository_patch.py, sandbox.py, sandbox_executor.py, remote_sandbox.py, sandbox_service.py, worker_tasks.py, build_control.py, build_state.py, build_outbox_relay.py, preview_runtime.py, preview_router.py, provider_router.py, model_gateway.py, verification_contract.py, creator_plan.py ו-build_cost_plan.py.
- לכל יכולת סמן DEFINED / IMPLEMENTED / WIRED / VERIFIED / BLOCKED, עם מבחן או לוג שמוכיח זאת. אל תכריז על LIVE על סמך README, CI כללי או READY של Vercel בלבד.
- רכז דוח Gap-by-Gap: קיים ומתפקד; קיים אך שבור; חסר; ההרחבה הקטנה ביותר; קבצים לשינוי; בדיקה להוכחה; סיכון ל-Regression.

### שלב 1: מנגנון תיקון ממוקד על הקיים
- אל תוסיף orchestrator_build_loop.py כשרת FastAPI חדש. שמור את _run_live_build_job/Worker as entrypoint ואת AutonomousProductEngine כאחד ממסלולי העבודה הקיימים.
- הוסף באופן backwards-compatible חוזי RepairFailure/RepairPatch/ExecutionEvidence עם schema_version, תיקונים רב-קובציים ואימות Pydantic/JSON Schema. את פלט המודל בדוק גם בצד השרת, ללא הסתמכות על Structured Output מהספק בלבד.
- נתח stdout+stderr, שייך שגיאות לקבצים על בסיס stack/compile references ו-dependency hints. אל תתקן סתם את הקובץ האחרון.
- יישם את התיקון דרך repository_patch.py וה-Manifest הקיים; שמור acceptance criteria, checks ונכסים. חסום traversal/symlinks, קבצים מוגנים, Patch מוגזם, no-op, repeated failure ו-cycles.
- פירוש MAX_REPAIR_ROUNDS=3: בנייה/אימות ראשוניים + עד 3 תיקונים כש**כל תיקון נבדק מחדש**, כולל התיקון האחרון. עצור רק ב-success verified, failure בטוח, או תקציב/זמן/מדיניות.

### שלב 2: Sandbox ו-Preview בלי רגרסיות
- השאר את Docker Sandbox המבודד כברירת מחדל; אל תסיר network none, cap-drop, non-root, read-only, timeouts/cgroups.
- כתוב Adapter דק סביב הסביבה הקיימת, עם versioned capabilities ו-cleanup, ולא שירות מתחרה.
- E2B רק PoC אופציונלי לאחר אימות תיעוד SDK המדויק, בידוד, ניתוב, עלויות, API, הרשאות, תוחלת חיים של Preview והחזרת artifacts. אל תהפוך אותו לספק חובה.
- אל תפעיל npm install דרך shell string מהלקוח; התקנה בתהליך dependency מוכר ומאובטח עם lockfiles ו-egress מוגבל.
- השתמש ב-preview_runtime.py הקיים: מקור קבצים וגרסה שנבדקו, port/health מה-Manifest, URL פרטי עם הרשאות, HTTP + browser check, חיי Preview נפרדים מה-Sandbox של הבנייה.

### שלב 3: Agent/FinOps/State/UI
- שמור את Model Gateway + Provider Router. אין ספק או מודל AI מקובע בקוד. בחר לפי איכות, מחיר, מדיניות שימוש, זמינות ויכולת structured output. רישום ספק אמיתי לכל ניסיון ותוצאה.
- שמור Quote/Reserve/Meter/Settle ואת Job/Outbox/Neon/RQ הקיימים; אין קוד שמחייב פעמיים אחרי retry/crash. לא להציג ללקוח $10 יתרה בכל ספק בלי הוכחת יתרת חשבון אמיתית. יש מגבלת QA כוללת נפרדת.
- חבר חסימות ל-Readiness UX בראש כל פרויקט: ללקוח מה חסר ומה אפשר לעשות; למנהל מקור דרישה, capability/Agent/Skill, קבצי מקור רלוונטיים אמיתיים, סיבת מחיר/ספק/סביבה, check to verify. צרף אבחון למנוע התיקונים, לא רק לתמחור.
- תקן את ההבדל בין "אפשר לבנות עם מגבלות" ל-"לא ניתן לאשר בנייה": feasibility לעומת execution admission, בשימוש באותו contract revision ו-budget check.
- כפתור אישור צריך ליצור Job durable ולהעביר אוטומטית למסך Build progress, ולא לחכות ב-HTTP עד שהכול מסתיים.
- התייחס ל-Mobile Safari Hebrew RTL, מצב session, preview, editor וגרסאות כמבחני קבלה מחייבים.

### שלב 4: בדיקות, רולבאק וראיות
- הוסף בדיקות חוזה/יחידה לפני שינוי, ולאחר מכן integration ו-Golden E2E (שתי בניות לפחות, אחת עם שגיאת קומפילציה מכוונת, בדיקה חוזרת לאחר התחברות מחדש).
- בדוק כשלי Worker, Duplicate Request, timeout, malformed patch, unknown file, 429 provider, budget reached, isolated secret access, injected regression, Preview health and expiry.
- כל השינויים בענף ייעודי + PR. Feature flags default-off לתכונות חדשות עד אימות. העלה deployment Preview פרטי עם דרך כניסה מאובטחת לבדיקות, ללא הסרת SSO.
- בצע רק בדיקות חינמיות עד שה-Gate מתאים. בקריאות AI בתשלום השתמש בתקרה המאושרת וברישום actual usage. אין להוסיף שירות בתשלום בלי הצדקת PoC.
- העבר לי: רשימת קבצים/שורות ששונו, SHA, PR, תוצאות בדיקות כולל failures, diff מול source-of-truth, מצב מול T01–T09 ו-Issue #26, URL Preview מאומת, פרטי evidence, עלות בפועל, rollback plan.
- **אסור להגיד "מוכן" או "Production-Ready" בלי הוכחה שהמשתמש יכול לבקש אתר → לאשר → לבנות → לתקן → לבדוק → לראות Preview חי → לבקש שינוי → לקבל גרסה חדשה, בבטיחות ובתקציב.**

## נספח חובה — סקירת קוד E2B/Repair/Worker מעודכן (13.10.2026)

הצעת קוד שנייה התקבלה לבחינה עם `E2BSandboxAdapter`, `IntegrationRepairAgent`, `autonomous_build_worker_job` וטבלת Dashboard. **אסור להעתיק את הקוד הזה כפי שהוא**: הוא עדיין אינו משולב, מאומת או בטוח. קרא לפני כל שינוי את **סעיף N (R2-01 עד R2-14, R2-T01 עד R2-T12)** במסמך ההנדסי:

https://github.com/Shayfly/desktop-tutorial/blob/audit/148ai-engineering-recovery-t01-2026-10-13/docs/BUILD_REPAIR_CORE_INTEGRATION_SPEC_HE_2026-10-13.md

הבהרות מחייבות למפתח:
- E2B הוא **PoC אופציונלי, לא ברירת המחדל**. בדוק גרסת Python SDK נעולה מול מסמכי E2B הרשמיים; בקוד שהוצע `AsyncSandbox.get()`, `sandbox.id`, `sandbox.close()` אינם הממשקים המתועדים שנמצאו ב-v2.5.0 — `connect()`, `sandbox.sandbox_id`, `kill()`. חובה בדיקת יצירה, reconnect, TTL, ניקוי והגנת סודות. שמור Docker Sandbox קיים.
- **אל תסמוך על `if ".." in path` או על `mkdir -p {dir_name}`**; השתמש בנתיבים מנורמלים, API קבצים וללא Shell-interpolation; בדוק סינון symlinks ו-path traversal.
- **אל תעקוף Provider Router.** בקוד המוצע `router=None` וקריאה ישירה ל-Gemini סינכרוני בתוך `async`. חבר רק דרך ה-Model Gateway עם הרשאות, ניתוב איכותי, מדידת שימוש ו-Structured Output שעובר ולידציה של צד שרת.
- **אל תמציא עלויות** (`$0.45`, `$0.60`, `$0.80`) ואל תקבע `$1.50` כ-Reserve בלי Quote מאושר. השתמש ב-Quote/Reserve/Meter/Settle/Reconcile הקיימים, ושמור הוצאה אמיתית גם במסלול Exception/Crash.
- **לא ליצור Worker/DB State חדש.** `database_state_manager.py` לא נמצא בשורש הריפו/omni_prod בענף הבסיס שנבדק; יש כבר worker_tasks, leases, Outbox ו-Postgres. להוסיף רק חוזים/Adapters חסרים למנוע הקיים.
- **לא להציג COMPLETED אחרי Build בלבד**; חובה QA מאומת, סריקת סודות, behavioral/browser tests, גרסה שמורה ו-Preview פרטי ובריא. ניסיון תיקון שלישי חייב להיבדק במלואו.
- **למנוע דליפות:** יצירת Sandbox חייבת להיות תחת אחריות cleanup ושחרור רזרבה גם אם היא נכשלת. `finally: pass` אסור. Heartbeat פעיל לכל אורך install/build, לא רק בין שלבים.
- **לא להציג דמו כאמת:** שורות Dashboard עם סכומים/התקדמות ממקור הדוגמה הן דמו בלבד. להציג ללקוח ולמנהל רק נתוני Runtime אמת, בהפרדת הרשאות לפי Issue #26.

**סטטוס:** REVISION REVIEWED, NOT IMPLEMENTED. אין לפתוח שירות נוסף, לא להחליף את הקוד הקיים או למזג את PR #24/#25 בלי השלמת בדיקות ו-Golden E2E.

## Definition of Done להעברה הזאת
דוח השוואה לקוד הקיים + תוספות מינימליות ללא מנוע מקביל + טסטים מוכחים + build pipeline פרטי ובר-שחזור + ממשק חסימות אמיתי + אב־טיפוס שמוכיח Golden E2E. אם חוסם קיים, הצג אותו ואת התיקון המדויק עם סטטוס BLOCKED; אל תייפה את הנתונים.
