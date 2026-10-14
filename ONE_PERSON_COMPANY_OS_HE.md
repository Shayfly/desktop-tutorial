# Omni Creator — Company OS לחברת הייטק של אדם אחד

המבנה אינו מנסה לגרום למייסד לבצע ידנית עבודה של 13 עובדים. כל מחלקה מוגדרת כ-workflow, agents, gates, dashboards ו-artifacts. המייסד נשאר נקודת ההחלטה בנושאים בלתי הפיכים, משפטיים, כספיים ואסטרטגיים.

## 1. Founder / CEO / Strategy
**אם היו עובדים:** הנהלה, אסטרטגיה, הקצאת הון, סדרי עדיפויות, משקיעים, שותפים.
**אצלנו:** Weekly CEO Brief אוטומטי, scorecard, risk register, roadmap tradeoffs.
**רק המייסד מחליט:** שינוי אסטרטגיה, הוצאה מהותית, חוזה, השקעה, public launch, legal-risk override.

## 2. Product
**אם היו עובדים:** PMs, specs, roadmap, customer discovery, acceptance criteria.
**אצלנו:** Prompt→Spec, Acceptance Contract, backlog, feedback clustering, release definition.
**מדדים:** accepted builds, activation, task success.

## 3. AI / Research
**אם היו עובדים:** model researchers, inference, fine-tuning, routing, evals.
**אצלנו:** Model Router, benchmark runner, repair evals, cost optimizer, training-data export.
**מדדים:** first-pass success, repair rounds, cost per accepted build.

## 4. Engineering
**אם היו עובדים:** frontend/backend/mobile/game/platform engineers.
**אצלנו:** specialist agents + CI + architecture contracts + code review gates.
**מדדים:** regression rate, cycle time, tests, build success.

## 5. Design / Creative
**אם היו עובדים:** UX/UI, motion, brand, 3D/audio/video creators.
**אצלנו:** design system, Creative Director, Media Gateway, accessibility and anti-template checks.
**מדדים:** design acceptance, task completion, accessibility defects.

## 6. QA / Evals / Release
**אם היו עובדים:** QA, automation, release managers.
**אצלנו:** pytest, E2E, clean-ZIP verification, benchmark suite, hostile tests, release manifest.
**חוק:** release לא יוצא עם gate אדום.

## 7. Security / Privacy
**אם היו עובדים:** AppSec, cloud security, privacy engineers, incident response.
**אצלנו:** tenant isolation, sandbox, secret scan, RBAC, audit chain, rate limits, abuse controls.
**רק המייסד:** security-risk acceptance או incident disclosure מהותי.

## 8. Legal / IP / Compliance
**אם היו עובדים:** counsel, IP, privacy/compliance.
**אצלנו:** Rights & IP Engine, rights manifest, provenance, consent/license records, jurisdiction profiles.
**לא אוטומטי:** ייעוץ משפטי מחייב, חתימת חוזה, filing, high-risk legal override.

## 9. DevOps / SRE / Platform
**אם היו עובדים:** cloud, SRE, database, release engineering.
**אצלנו:** Docker, remote sandbox, Postgres/Redis/S3 adapters, metrics, backups, restore drills, rollback.
**מדדים:** uptime, p95, queue time, recovery time.

## 10. Data / Analytics
**אם היו עובדים:** product analysts/data engineers.
**אצלנו:** event schema, usage metering, cost attribution, human evaluation, build analytics.
**מדדים:** retention, activation, accepted-build rate, cost/build.

## 11. Finance / Operations
**אם היו עובדים:** CFO/finance/ops/procurement.
**אצלנו:** vendor ledger, usage/cost reports, budget alerts, gross-margin model.
**רק המייסד:** בנק, מס, תשלום, התחייבות חוזית ורכישה גדולה.

## 12. Customer Success / Support
**אם היו עובדים:** support, solutions, customer success.
**אצלנו:** ticket classification, diagnostics bundle, known-issue retrieval, bug reproduction, docs updates.
**מדדים:** resolution time, repeat issue rate, CSAT.

## 13. Growth / Sales / Partnerships
**אם היו עובדים:** marketing, sales, partnerships, PR.
**אצלנו:** רק אחרי Product Truth — case studies, sales CRM, launch content, experiments.
**חוק:** claim שיווקי חייב להיות מגובה בנתון/בדיקה.

# Release Council אוטומטי
לפני כל גרסה ציבורית חייבים להיות ירוקים לפחות:
1. Product acceptance.
2. Engineering tests/backward compatibility.
3. QA/Evals.
4. Security/Tenant Isolation.
5. Rights/IP publish gate.
6. Infrastructure readiness.
7. Backup/restore evidence.

# לולאת עבודה יומית לחברה של אדם אחד
1. המערכת אוספת failures, feedback, security alerts, rights alerts ועלויות.
2. היא מייצרת Priority Brief.
3. המייסד מאשר את ה-Top priorities.
4. agents מבצעים build/test/repair.
5. QA + Security + Legal/IP + Infra gates רצים אוטומטית.
6. רק release ירוק נארז, מקבל checksum ונשמר ב-Release + Backup.
7. Dashboard מתעדכן עם איכות, עלות, latency, incidents ו-blockers.

# מה אסור לאוטומציה להחליט לבד
- העברה/תשלום כסף.
- חתימה על חוזה או תנאים משפטיים בשם החברה.
- הצהרה משפטית שזכויות "מאושרות" בלי evidence/reviewer.
- פרסום release עם blocker קריטי.
- מחיקת נתוני לקוחות באופן בלתי הפיך ללא authorization.
- שינוי אסטרטגי מהותי או התחייבות למשקיע/לקוח.

# מה ממומש ב-V27 ולא רק מתואר
- `triage(signals)` מנתב אירועים למחלקה המתאימה ונותן P0–P3.
- Security/rights/cost/strategy incidents יכולים להיכנס אוטומטית ל-Founder Approval Queue.
- `ceo_brief(...)` מרכז Top Priorities, metrics והחלטות שמחכות למייסד.
- `evaluate_release(...)` מריץ Release Council על Product, Engineering, QA, Security, Rights/IP, Infrastructure ו-Backup/Restore.
- גם אם כל ה-gates הטכניים ירוקים, Public Launch נשאר אישור מפורש של המייסד.
- API זמין תחת `/api/v27/company-os/*` כדי שבהמשך telemetry, support, CI, billing ו-monitoring יוכלו להזין את המערכת ישירות.
