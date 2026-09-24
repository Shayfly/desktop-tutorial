> **חומר גלם — לא לשימוש מול משקיע ללא בדיקה מול `STATUS.md` הנוכחי קודם.** ראו `GOVERNANCE.md`.

# דמו לגיס / משקיע

1. חלץ את ה-ZIP.
2. הרץ `python -m pip install -r requirements-demo.txt`.
3. הרץ `./scripts/verify_v23.sh` כדי לאמת את הקוד והבדיקות.
4. הרץ `./scripts/run_prelaunch_demo.sh`.
5. פתח `http://127.0.0.1:8080`.
6. כתוב רעיון למוצר ולחץ על Build verified offline demo.
7. הצג את ה-Spec, repository, acceptance mapping ו-readiness gates.
8. אם קיימים Docker + GPU/model endpoint, הפעל `OMNI_ENABLE_LIVE_BUILD=1` והריץ `/api/live/build`.
9. לאחר חיבור מודל אמיתי, הרץ `scripts/run_live_benchmark.py` על 30 תרחישים.

## מה אומרים בדמו
"אנחנו לא מוכרים wrapper למודל אחד. Omni היא שכבת orchestration שממירה intent לחוזה מוצר, מייצרת repository, מריצה בדיקות, מתקנת ומגבילה עלות. המודל שמתחת ניתן להחלפה."

## מה לא אומרים עדיין
- לא אומרים שהמערכת כבר בונה כל מוצר בעולם ללא כשל.
- לא אומרים שהמודל שלנו אומן מאפס.
- לא אומרים שה-Benchmark החי עבר עד שהוא באמת רץ עם GPU/Docker.
- לא מתחייבים לשווי חברה מסוים.
