# Omni Creator V27 — Rights & Company OS Reviewer Release

V27 ממשיכה ישירות את V26 ומוסיפה שכבת זכויות/IP ושכבת Operating System לחברת אדם אחד.

## מה חדש
- Rights & IP Engine עם copyright/trademark/persona/voice/performer/music categories.
- Rights Manifest בתוך כל repository.
- US/EU/IL baseline jurisdiction profiles עם מקורות רשמיים.
- Promote/Publish fail-closed כשיש high-risk unresolved rights findings.
- Evidence של לקוח מתחיל `verified=false`.
- Rights reviewer credential נפרד נדרש כדי לאמת evidence.
- Original Alternative: הסרת identifiers של צד שלישי ושמירת mechanics/genre/requirements כלליים ליצירה חדשה.
- Control-plane secret מופרד מ-generated-app runtime secret.
- Company OS: 13 מחלקות ו-Release Council.
- Control Center מציג Rights Status ו-Original Alternative.

## אמת טכנית
V27 אינה ייעוץ משפטי, אינה מאגר כל הזכויות בעולם ואינה מבצעת clearance עולמי אוטומטי. היא שכבת risk triage, provenance, evidence ו-publish gating.

## הפעלה
ראו `RUN_LOCAL_DEMO.md`. לבדיקת V27: `python -m pytest -q`.
