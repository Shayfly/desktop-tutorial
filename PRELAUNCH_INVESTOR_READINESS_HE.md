> **חומר גלם מ-V23 — לא לשימוש מול משקיע ללא בדיקה מול `STATUS.md` הנוכחי קודם.** ראו `GOVERNANCE.md`.

# Omni Creator V23 — מוכנות Pre‑Launch

## מה קיים בפועל
- חוזה Prompt → Product Spec → Acceptance Criteria.
- Agent contracts ל‑Architect / Generator / Repair.
- מסלול model local-first תואם OpenAI API.
- Zero-Cost Mode שחוסם ספקים חיצוניים כברירת מחדל.
- Router שמנסה local תחילה ומאפשר fallback בתשלום רק לפי policy ותקציב.
- Repository patching מוגן traversal.
- Manifest לבנייה ובדיקות עם קישור ל‑acceptance IDs.
- Docker sandbox contract מוקשח.
- Repair loop עד PASS/FAIL.
- PostgreSQL / Redis / S3 production adapters ותשתיות reliability/observability/recovery מהגרסאות הקודמות.
- Control Center בדפדפן שמציג readiness ומייצר offline verified repository demonstration.
- Benchmark catalog של 30 תרחישים שונים.

## מה עדיין חייב הוכחה חיה לפני טענה של Production
- מודל Open‑Weight אמיתי שרץ על GPU ומבצע את מסלול Architect→Generate→Repair.
- Docker sandbox אמיתי מול generated repositories hostile/untrusted.
- PostgreSQL/Redis/S3 live integration בסביבת staging.
- Benchmark מלא על 30 התרחישים עם שיעור הצלחה, זמן ועלות.
- Deploy ציבורי ו‑beta users אמיתיים.
- Mobile/3D console-grade אינם מוכחים end-to-end ב‑V23.

## כלל
לא מציגים למשקיע capability כקיימת אם היא רק roadmap. כל מסך ודוח מפרידים בין proven, configured ו‑not-yet-proven.
