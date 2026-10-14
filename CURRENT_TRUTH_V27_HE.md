> **היסטורי — לא המצב הנוכחי.** הוחלף על ידי `CURRENT_TRUTH_V28_HE.md` ולאחר מכן על ידי `STATUS.md` (עבודת M1–M3 מעל בסיס V28). ראו `GOVERNANCE.md`.

# V27 — Current Truth

## מוכח בקוד/בדיקות
- כל V26 נשמרת כרגרסיה.
- Rights & IP Engine עם findings, evidence, target markets ו-Publish Gate.
- Rights Manifest נכתב לתוך repository.
- Promote נחסם כאשר high-risk rights findings אינם פתורים.
- Verified evidence יכול לפתור finding תואם; user claim לא מאומת אינו מספיק.
- Original Alternative מסיר identifiers שנמצאו ומייצר brief ליצירה מקורית; אינו מוצג כפתרון משפטי אוטומטי.
- US/EU/IL jurisdiction baseline profiles ומקורות רשמיים.
- Company OS עם 13 מחלקות, founder-only decisions ו-Release Council.
- Company OS תפעולי: signal triage, P0-P3 priority, automated-vs-founder routing, CEO brief ו-release-council evaluation.
- Tenant isolation חל גם על rights status/evidence.
- Full regression: 209 PASS + 9 Live-only skipped, 0 failures בסביבת הבדיקה הנוכחית.

## לא מוכח / לא נטען
- המנוע אינו עורך דין ואינו נותן clearance משפטי סופי.
- entity detection הדטרמיניסטי הוא baseline ולא מאגר של כל אדם/מותג בעולם.
- אין כרגע חיפוש live אוטומטי בכל מאגרי trademarks/copyrights/collecting societies בעולם.
- אין כרגע OCR/forensic similarity service מלא למלודיה/וידאו/3D/לוגו.
- אין טענה שכל דיני כל המדינות מכוסים.
- Company OS אינו מחליף רואה חשבון, עורך דין או אישור אנושי לפעולה בלתי הפיכה.
- Open-weight GPU אמיתי, real multimodal GPU, Docker hostile runtime, Postgres/Redis/S3 live stack, creator persistence production, signed Android/iOS, payments ו-public TLS/domain עדיין live gates חיצוניים.

## מסלול להמשך
- לחבר model/entity recognition שמוסיף findings אך לא יכול להסיר deterministic blockers.
- לחבר trademark clearance/search providers לפי jurisdiction.
- להוסיף provenance/content credentials/watermarking engines.
- לשמור evidence במסד production מוצפן/object vault.
- להוסיף human legal-review workflow לארגונים.
- לחבר Company OS ל-production telemetry, support inbox, finance/vendor ledger ו-release CI אמיתי.
