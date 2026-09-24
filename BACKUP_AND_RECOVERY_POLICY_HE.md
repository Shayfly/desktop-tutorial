# מדיניות גיבוי ושחזור — Omni Creator

מ-V25 ואילך אין Release בלי ארבע שכבות שמירה:

1. **Release ZIP immutable** — קוד מלא + tests + docs + infra.
2. **SHA-256** — checksum חיצוני של ה-ZIP ושל כל קובץ בתוך Release Manifest.
3. **Recovery Package** — Release נוכחי + Release הורה + validation + lineage + recovery index.
4. **Persistent Library copies** — עותק Release ועותק Recovery תחת תיקיות release/backup נפרדות.

## כלל שחרור
Release חדש לא מחליף Release ישן. הוא מקבל שם חדש ו-checksum חדש. אין overwrite על היסטוריה.

## בדיקות לפני גיבוי
- fresh extraction
- compileall
- full pytest
- secret scan
- release-manifest verification
- deterministic benchmark
- V10 parity gate
- HTTP acceptance

## שחזור
במקרה של אובדן סביבת עבודה:
1. קח את ה-Release ZIP האחרון מה-Library.
2. אמת SHA-256 מול `RECOVERY_INDEX.json`.
3. חלץ לתיקייה חדשה.
4. הרץ `python -m pytest -q`.
5. הרץ `python scripts/run_v25_release_gate.py`.
6. אם ה-Release האחרון פגום, חזור ל-parent ZIP הכלול ב-Recovery Package.
