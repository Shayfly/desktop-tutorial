# Omni Creator V24 — International Readiness

V24 מרכזת את כל השדרוגים שביקשנו לאחר V23 למוצר אחד: מנוע אוטונומי, איכות, אבטחה, memory, teams, billing, integrations, internationalization, native mobile, game engines, production runtime וראיות מדידות.

## מה אפשר להריץ עכשיו בלי שירות חיצוני

```bash
python -m pip install -r requirements-demo.txt -r requirements-test.txt
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port 8000
```

פתח `http://127.0.0.1:8000`.

ה-Control Center תומך אנגלית/עברית ו-RTL, יודע לייצר offline starter repositories שונים לפי סוג המוצר, להריץ quality/security gates, לשמור versions ו-memory, ולהוריד גרסה כ-ZIP.

## אימות

```bash
python -m pytest -q
python scripts/run_hostile_static_suite.py
python scripts/run_international_gate.py
```

## Live autonomous mode

כדי לעבור מ-offline demonstrator לבנייה AI אמיתית צריך:

- OpenAI-compatible local model endpoint (למשל vLLM עם מודל Open-Weight).
- Docker מקומי מבודד או `OMNI_SANDBOX_RUNNER_URL` של runner נפרד.
- PostgreSQL, Redis/RQ ו-S3-compatible storage.

אחרי חיבור:

```bash
OMNI_ENABLE_LIVE_BUILD=1 python scripts/run_live_benchmark.py
```

הקטלוג מכיל 200 prompts ב-20 קטגוריות. V24 אינה טוענת שה-200 עברו עד שמריצים אותם על GPU + sandbox אמיתי.

## Mobile / Games

V24 מייצרת source starter אמיתי ל-Android, iOS, Godot, Unity ו-Unreal ומגדירה build/signing contracts. Signed AAB/IPA וקונסולות דורשים credentials/toolchains/SDK access חיצוניים ולכן אינם מסומנים כ-live verified בחבילה הזו.

## Production security

Production API דורש token חתום; integrations מקבלים secret references בלבד; sandbox runner נפרד נחתם ב-HMAC; קיימים static hostile tests, secret scan, SBOM, audit/recovery controls ו-CSP קשיח ללא inline JavaScript.
