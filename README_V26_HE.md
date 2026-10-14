# Omni Creator V26 — Universal Pro Reviewer Release

V26 היא חבילת הביקורת המאוחדת לפני חיבור כל התשתיות החיות. היא מוסיפה מעל V25 שכבת מוצר למשתמש קצה: חשבונות יוצר, בעלות ובידוד פרויקטים, Build/History/Edit/Restore/Export/Deploy, מוח כיסוי אוניברסלי וחוזה Creative Assets לגרפיקה, סאונד, מוזיקה, קול, וידאו ו-3D.

## הפעלה מקומית
```bash
python -m pip install -r requirements-demo.txt
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port 8000
```
פתחו `http://127.0.0.1:8000`.

## אימות
```bash
python -m pytest -q
node --check omni_prod/assets/app.js
python scripts/run_v26_release_gate.py
```

## עקרון אמת
V26 לא טוענת שנכס גרפי/קולי נוצר כאשר הוא רק תוכנן. `/api/v26/projects/{id}/live-build` נכשל סגור אם מודל מקומי וסנדבוקס אמיתי אינם מחוברים.
