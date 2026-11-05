# Intake experiments — main b97114c, 2026-10-27

Author: Claude (agent). Machine runs of `ConversationSupervisor` with in-memory stores and the deterministic interpreter (no model, $0) — the same path production uses, since `OMNI_INTAKE_MODEL` is set on Vercel for Preview only.

**Not a conversation with a person.** No full transcript with a non-technical user exists in this repository (searched `docs/evidence`, `smoke`).

Re-run from the repo root: `OMNI_TEST_HERMETIC=1 python3 docs/evidence/intake-2026-10-27/no_questions.py` and `.../lang.py`.

## Findings

1. Deleting the fixed question catalog (`discovery.QUESTIONS`) does not crash the conversation, but it stops asking: the brief is `complete=True` from the first message, every reply is "לא זיהיתי פרטים חדשים", and the gap detector still picks a question (`languages`) that is never shown. Completeness is decided by the catalog, not the detector.
2. The first Hebrew reply states the assumption "שפה: עברית" and asks "באיזו שפה יהיו הטקסטים?" in the same message.
3. An English request is assumed to want a Hebrew product ("language: Hebrew"); an Arabic request gets a half-Hebrew reply and a Hebrew product assumption.

## 1. Same conversation with and without the fixed question catalog
```
=== with catalog: QUESTIONS=16
> אני רוצה אתר לתיירים שמגיעים לעיר
< בחרתי עבורכם (אפשר לשנות בכל רגע): קהל: לקוחות או קהל רחב מהאינטרנט; שפה: עברית; תאריכים: אין תאריכים. עוד 9 החלטות כאלה בלשונית "דרישות". באיזו שפה יהיו הטקסטים? (כי זה קובע את השפה ואת כיוון הכתיבה של כל העמודים.) אפשר גם לכתוב "תחליט אתה".
  complete=False asked=['languages'] detector_q=languages actions=[]
> תחליט אתה
< האתר רק מציג מידע, או שגם נשמר בו משהו מהמבקרים — טופס, הזמנה או רשימה? (כי זה קובע אם יש מאגר נתונים בכלל.) אפשר גם לכתוב "תחליט אתה".
  complete=False asked=['content_only'] detector_q=content_only actions=[]
> תחליט אתה
< יישמרו פרטים אישיים כמו טלפון או מייל? (כי זה משנה מה נשמר ומי רואה את זה.) אפשר גם לכתוב "תחליט אתה".
  complete=False asked=['personal_data'] detector_q=personal_data actions=[]
=== catalog deleted: QUESTIONS=0
> אני רוצה אתר לתיירים שמגיעים לעיר
< לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".
  complete=True asked=[] detector_q=languages actions=[]
> תחליט אתה
< לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".
  complete=True asked=[] detector_q=content_only actions=[]
> תחליט אתה
< לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".
  complete=True asked=[] detector_q=style actions=[]
```

## 2. First message in three languages
```
> أريد موقعًا لصالون الحلاقة الخاص بي 
< lang=he | בחרתי עבורכם (אפשר לשנות בכל רגע): קהל: צוות פנימי (עובדים / אני); שפה: עברית; תאריכים: תאריכים עתידיים עד שנה קדימה. עוד 9 החלטות כאלה בלשונית "דרישות". هل ستُحفظ بيانات شخصية مثل الهاتف أو البريد؟ (لأن هذا يغيّر ما يُحفظ ومن يراه.) يمكنك أيضًا أن تكتب "قرر أنت".

> I want a website for my barbershop 
< lang=en | I chose for you (change anything any time): audience: Customers / the public; language: Hebrew; dates: No dates. 9 more such decisions are in "Requirements". Does the site only show information, or does it also save something from visitors — a form, a booking or a list? (because it decides whether there is a database at all.) You can also say "you decide".

> אני רוצה אתר למספרה שלי 
< lang=he | בחרתי עבורכם (אפשר לשנות בכל רגע): קהל: לקוחות או קהל רחב מהאינטרנט; שפה: עברית; תאריכים: אין תאריכים. עוד 9 החלטות כאלה בלשונית "דרישות". האתר רק מציג מידע, או שגם נשמר בו משהו מהמבקרים — טופס, הזמנה או רשימה? (כי זה קובע אם יש מאגר נתונים בכלל.) אפשר גם לכתוב "תחליט אתה".

```
