## מצב עדכני — 2026-11-02 (קריאת GitHub; בסיס main d224629d8def0871a0d7e8ca8cc20b958063aad7)

- main: `d224629d8def0871a0d7e8ca8cc20b958063aad7`, מיזוג #207 (repair plan floor). #203 מוזג ב-`ef9d1564a00fca3943dc67485a4fb73afcf7063e`.
- חיפוש PR פתוחים החזיר **45 PRs** בזמן הבדיקה; ביניהם #214, #213, #212, #210, #198, #180, #177. אין להסיק שהרשימה סטטית.
- #177 (חוקי הברזל): OPEN, ללא reviews רשומים; לא מוזג. אין ראיית אישור עצמאי או CI ירוק על head במסגרת הבדיקה הנוכחית.
- #210: הכותרת קובעת DO NOT MERGE לפני deploy הבא; אין לראות בו מאושר.
- Branch protection: לפי דיווח המייסד רק `test` ו-`validate` חוסמים. נדרשת בדיקה ישירה של ההגדרות ושל שבעת ה-contexts; לא בוצע שינוי.
- כשלי CI/מוצר: קיימים דיווחים על כשל OOM drain (exit 137, oom=false) ועל בעיות build/repair/verification. **לא נבדקו כאן לוגי CI עדכניים**, ולכן אין לייחס כשל חדש ל-SHA הנוכחי או להכריז ירוק.
- `docs/AUDIT_2026-11-02.md` לא נמצא ב-main בעת הבדיקה (404); ממצא 5 מיוחס להנחיית המייסד, לא לציטוט מסמך שנקרא.
- הכרעה: HOLD על אכיפת branch protection עד אישור בעלים; HOLD על מיזוג #177 עד בדיקת CI ו-review עצמאי.

# STATE — מצב נוכחי

**מתעדכן בכל שינוי SHA** — יש לעדכן את SHA של main, של כל PR פתוח ושל ריצות ה־CI בכל שינוי רלוונטי; זו דרישת תחזוקה, לא מנגנון אוטומטי.

**עדכון אחרון:** 2026-10-24 (Asia/Jerusalem). **בסיס נתונים:** GitHub `main` `47b477b6295181636a7035397da9aba859ea0d48`; מצב PR/runs נבדק ב-2026-10-24.

| נושא | מצב מאומת / חסם |
|---|---|
| Repository | [Shayfly/desktop-tutorial](https://github.com/Shayfly/desktop-tutorial) |
| main SHA | `47b477b6295181636a7035397da9aba859ea0d48` (אומת באמצעות חיפוש commits ב־GitHub) |
| PR #123 (תיעוד) | [MERGED](https://github.com/Shayfly/desktop-tutorial/pull/123) ל־main; merge commit `47b477b6295181636a7035397da9aba859ea0d48` |
| PR #124 (Repo Control) | [OPEN — Draft](https://github.com/Shayfly/desktop-tutorial/pull/124); טרם נפרס, ללא מיזוג |
| PR #121 (H1/E1) | [OPEN](https://github.com/Shayfly/desktop-tutorial/pull/121); HEAD `667da1a67b3f721a6e7aa03bb6f745427a62a382`; חמישה workflows success; **אין מיזוג** |
| PR #122 (H3) | [OPEN](https://github.com/Shayfly/desktop-tutorial/pull/122); HEAD `bab9df183bdb80a7f2237e2b7ec3e5a3e6f30e12`; ללא אימות live revision |
| S1b | OPEN: `tail_attention`, מיפוי `evidence_durability` ו־`evaluated` בכותב **ובקוראים**; אין להפוך status=True בלי עבודה |
| כרטיס S1b — קורא PASS | `omni_prod/release_policy.py:129–136` קורא `last.passed` בלי `evaluated`. **נכנס ל־S1b: לתקן גם את הקורא, לא רק את הכותב**; עדיין לא תוקן |
| S2 / ביקורת #121 | HOLD עד S1b ירוק, קריאת דיף עצמאית ו־APPROVE מפורש של מאט |
| S8 / diagnostic_agent STALE | לא הוכחו התנאים הנדרשים; לא להצהיר REAL_SERVER_VERIFIED ללא ראיה |
| Worker live revision | UNKNOWN; הלוגים מאשרים service healthy/queue consume אך לא SHA חי |
| H3 רגל שנייה | source_commit של ריצה חדשה עדיין לא התקבל |
| Golden E2E ריצה 3 | NOT RELEASED: נדרשים gate/baseline, בודק חיובי ושלילי ובריף מאושר מראש |
| מוצר לקוח ציבורי ומיוצא | לא הוכח end-to-end (Preview אמיתי + Artifact + ZIP) |

**המספר הבא:** PR מועמד **#125** לאחר #124; המספר הסופי מוקצה ב־GitHub בלבד. **התור הבא לעבודה:** להשלים S1b בענף #121 בדחיפה אחת עם ראיות; לא להתחיל S2 לפני כן.

| כרטיס עתידי — הפרדת זהויות GitHub | קודקס דוחף כיום דרך חשבון `Shayfly`; author=approver ולכן בעל החשבון לא יכול לספק ביקורת עצמאית על ה־PR של עצמו. נדרשות זהות כותב נפרדת לקודקס וזהות GitHub נפרדת למאט. **BACKLOG בלבד — לא מטפלים כעת.** |

**בעל / שער:** קודקס כותב יחיד; מאט מאמת; מנכ״ל מאשר מיזוג. אין דחיפה בזמן CI פעיל ואין מיזוג עצמאי.
