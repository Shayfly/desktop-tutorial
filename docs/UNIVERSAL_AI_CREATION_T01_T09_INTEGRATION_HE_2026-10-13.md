# 148AI — Universal AI Creation Platform: מפת שילוב מצטברת

**מקור אמת:** T01–T09, Agent OS, Master Agents Registry, Master Skills Registry, PR #27 ודרישת ״כל־בו AI״ מ־13.10.2026. **מסמך זה אינו מסלול הרצה, מקור תמחור או מנוע נפרד.**

## החלטות ארכיטקטורה
- **מנוע אחד:** Natural Language → ConversationSupervisor / Discovery → Brief + BuildContract / CapabilityPlan → ProductArchitect → DAG/Agent OS → Redis/RQ → Docker Sandbox → Build/Test/Repair/Verify → PreviewRuntime → Workspace/Versions.
- **Product IR:** משתמשים בחוזי `Brief`, `BuildContract`, `ProductSpec` ו־`CapabilityPlan` הקיימים, כולל Fingerprints, גרסאות וקישורי ראיות. לא יוצרים DB או IR מתחרה. הרחבת המבנה תתבצע בשדות מאומתים, עם תאימות לאחור.
- **בחירת מודל:** רק דרך ה־Model Gateway ו־Provider Router/FinOps הקיימים. הלקוח רואה מוצר, מצב עבודה ועלות קרדיטים; הוא אינו צריך לבחור ספק או להכיר שמות מודלים. Founder diagnostics מופרד ומוגבל הרשאות.
- **Product Family Adapters:** הרחבות עתידיות של מנוע אחד. Adapter שאינו מחובר לתורי העבודה, למערכת העלויות ולתנאי קבלה אמיתיים נשאר **BLOCKED/UNVERIFIED** ואינו מוצג כמוכן.
- **Reuse Before Rewrite:** Docker/Oracle, Neon, Redis/RQ, R2 ו־Vercel נשארים. E2B, Temporal ו־LangGraph אינם תלות מחייבת.

## המצב מול P0 / P1 / P2

| משפחה | רכיבים קיימים | דרגת בשלות מוכחת לסבב זה | Gate לפני הצגה כזמין |
|---|---|---|---|
| P0 דפי נחיתה ואתרים | discovery, product_architect, capability_planner, autonomous_core, preview_runtime | WIRED / Integration tested in CI; no new Golden E2E | שיחה אמיתית, אישור, בנייה, בדיקות, Preview חי וגרסה |
| P0 Web/SaaS ומערכות בסיסיות | ProductSpec, contracts, Agent OS, worker_tasks, workspace | PARTIAL / CI verified portions | Neon/Redis/Worker/permissions E2E, tenant isolation |
| P1 CRM, הזמנות, מסחר | unified_engine, managed web profile, infrastructure registry | DEFINED/PARTIAL | תרחישי API, נתונים והרשאות לכל מוצר |
| P1 אפליקציות מובייל | native_source, target android/ios source | PARTIAL; packaging/distribution unverified | build אריזה חתומה/התקנה/הרשאות ב־device |
| P1 סוכני AI וצ'אטבוטים | Agent OS, capability registry, model gateway | PARTIAL, no generated-agent E2E | tools permissions, isolation, budget, independent eval |
| P1 אוטומציות | capability registry, task DAG, provider routing | DEFINED/PARTIAL | טריגרים, retries, idempotency, no duplicate execution |
| P1 משחקי 2D | native_source, capability target.game.2d | PARTIAL/unverified | playable sandbox, input, scoring, 2D playtest |
| P1 תמונות/עריכה | media_pipeline, router and providers | PARTIAL/unverified | real provider commercial rights, asset QA and storage |
| P2 וידאו/קול/מוזיקה | media_pipeline and planned skills | DEFINED/PARTIAL | model/rights budgets, composed media artifact and QA |
| P2 Marketplace/Creator Studio | product roadmap only | NOT VERIFIED | publish/ownership/payment/IP/social multiuser E2E |

**סטטוס אינו נגזר משם סוכן או מקיום קובץ.** ה־Registries נשארים מקורות האמת למימוש/סטטוס וכל ראיית Real Server חייבת להיקשר ל־SHA ולבדיקה שבוצעה. 54 סוכנים ו־427 סקילים מופיעים בסנאפשוט Registry; אין להסיק מכך שהם כולם עובדים.

## תלות ושלבי ביצוע
```text
T01: current source, CI, deployment, Oracle baseline
  → T02: durable job lifecycle, leases, idempotency, crash recovery
  → T03: actual model conversation → approved Product IR → capability/agent/skill DAG
  → T04: isolated existing Docker and signed request validation
  → T05: bounded Build → Test → Repair (≤3) → Verify (incl. last repair)
  → T06: independent private preview lifetime, runtime+browser proof, versions/restore
  → T07: provider router / quote→reserve→meter→settle→reconcile
  → T08: security, permissions, secrets, audit, rights, janitor
  → T09: two real Golden E2E, change request and persistence under capped budget
  → P1: verified family adapters
  → P2: advanced creator studio
```

## מה בוצע בפועל ב־PR #27
- תיקוני חיווי מוכנות, תמחור וסיסמה; תיעוד חסימות לפי דרישות.
- חיבור AI-semantic decisions ל־Brief ול־ProductArchitect, עם ראיות, אימות ואישור.
- הגבלה קשיחה של 3 סבבי תיקון; חוזי Repair/Sandbox מאומתים ודגלי הפעלה זהירים.
- **הרחבת Agent OS resolver:** אם קיים CapabilityPlan מאושר, בחירת סקילי game/media/automation נעשית לפי required capability keys, ולא לפי מילים במקרה. Route ישן נשמר לחוזים ישנים בלי Plan.
- **הסתרת פירוט שגיאות ספקים מהלקוח:** הודעות משתמש בטוחות בשפה טבעית; פרטי ספק ותמחור רגישים מיועדים לאבחון מוגבל הרשאות.

## P0 חסמים ממשיים — אין להכריז GO
1. **deployment-verify:** Vercel מחזיר 401 למסלול GitHub Actions כי ה־Preview מוגן. נדרשת הרשאת Automation ייעודית בלי להסיר SSO; עד אז בדיקת לקוח חיה NOT RUN.
2. **Docker OOM CI:** אירוע Exit 137 אינו הוכחת OOM. יש ריצה שנכשלה כי Docker לא סיפק `OOMKilled=true`; אין לעקוף את הבדיקה.
3. **Oracle Worker:** אין אימות עדכני של Worker, Sandbox, Preview lifecycle ו־queue consumption עבור SHA זה.
4. **FinOps:** יתרת ספק חיצוני אינה מאומתת, אין לאפשר paid E2E או מחיר $0 מומצא.
5. **Golden E2E:** שתי בניות מאומתות ושינוי גרסה נשמרת עדיין לא בוצעו ב־Preview הנוכחי.
6. **חדש מול קיים:** PR #21/#24/#25 נשארים בהיררכיית התלויות; PR #27 לא מוזג.

## קבלה למשפחה חדשה בעתיד
כל Adapter חייב למפות: source contract fingerprint → required capabilities → Agent/Skill registry → provider routes → cost quote/reserve → isolated execution → required family-specific acceptance → private preview/player → stored version → audit evidence. אם שלב חסר, הסטטוס **BLOCKED**. אין לחשוף ״זמין לבנייה״ על בסיס היתכנות בלבד.

## Rollback
ה־PR בטיוטה; ללא migration או שינוי Production. יש להשיב את ענף ה־Preview ל־SHA המאומת הקודם, לבטל דגלי ניסוי בלבד, ולא לגעת בנתוני Neon/R2. כל העלאת מצב ל־LIVE מחייבת ראיה נפרדת מ־Worker ומ־Preview.
