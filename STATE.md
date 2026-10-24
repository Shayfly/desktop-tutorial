# STATE — מצב נוכחי

**מתעדכן בכל שינוי SHA** — יש לעדכן את SHA של main, של כל PR פתוח ושל ריצות ה־CI בכל שינוי רלוונטי; זו דרישת תחזוקה, לא מנגנון אוטומטי.

**עדכון אחרון:** 2026-10-24 (Asia/Jerusalem). **בסיס נתונים:** GitHub `main` `9f9ccfbb58a2c3f4b77053fe5aebb31aa1f0d967`; מצב PR/runs נבדק ב-2026-10-24.

| נושא | מצב מאומת / חסם |
|---|---|
| Repository | [Shayfly/desktop-tutorial](https://github.com/Shayfly/desktop-tutorial) |
| main SHA | `9f9ccfbb58a2c3f4b77053fe5aebb31aa1f0d967` (אומת באמצעות חיפוש commits ב־GitHub) |
| PR #121 (H1/E1) | [OPEN](https://github.com/Shayfly/desktop-tutorial/pull/121); HEAD `667da1a67b3f721a6e7aa03bb6f745427a62a382`; חמישה workflows success; **אין מיזוג** |
| PR #122 (H3) | [OPEN](https://github.com/Shayfly/desktop-tutorial/pull/122); HEAD `bab9df183bdb80a7f2237e2b7ec3e5a3e6f30e12`; ללא אימות live revision |
| PR #125 (M7, קלוד) | [OPEN](https://github.com/Shayfly/desktop-tutorial/pull/125); ענף `feat/m7-intake-conversation`; HEAD `d3ba3a8ec56914ba5623c0ff3c500dac2c6d6c29`; test/validate/pg ירוקים; ממתין לביקורת מאט; קבצים: `omni_prod/intake/`, `omni_prod/conversation/` + קובץ בדיקות חדש בלבד; לא נוגע ב־#121/#122/במריץ; **אין מיזוג** |
| S1b | OPEN: `tail_attention`, מיפוי `evidence_durability` ו־`evaluated` בכותב **ובקוראים**; אין להפוך status=True בלי עבודה |
| כרטיס S1b — קורא PASS | `omni_prod/release_policy.py:129–136` קורא `last.passed` בלי `evaluated`. **נכנס ל־S1b: לתקן גם את הקורא, לא רק את הכותב**; עדיין לא תוקן |
| S2 / ביקורת #121 | HOLD עד S1b ירוק, קריאת דיף עצמאית ו־APPROVE מפורש של מאט |
| S8 / diagnostic_agent STALE | לא הוכחו התנאים הנדרשים; לא להצהיר REAL_SERVER_VERIFIED ללא ראיה |
| Worker live revision | UNKNOWN; הלוגים מאשרים service healthy/queue consume אך לא SHA חי |
| H3 רגל שנייה | source_commit של ריצה חדשה עדיין לא התקבל |
| Golden E2E ריצה 3 | NOT RELEASED: נדרשים gate/baseline, בודק חיובי ושלילי ובריף מאושר מראש |
| מוצר לקוח ציבורי ומיוצא | לא הוכח end-to-end (Preview אמיתי + Artifact + ZIP) |

**המספר הבא:** מספור PR הבא *המועמד* הוא **#123** לפי חיפוש PRs שבו #122 הגבוה ביותר. GitHub יקצה מספר סופי רק עם יצירת PR; אין להניח שיוקצה דווקא #123. **התור הבא לעבודה:** להשלים S1b בענף #121 בדחיפה אחת עם ראיות; לא להתחיל S2 לפני כן.

**בעל / שער:** קודקס כותב יחיד; מאט מאמת; מנכ״ל מאשר מיזוג. אין דחיפה בזמן CI פעיל ואין מיזוג עצמאי.
