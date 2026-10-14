# Omni Creator V25 — Unified Core

V25 מאחדת את שכבות V11–V24 עם שחזור התנהגותי של היכולות המוכחות של V10.

## מה חדש
- Unified Prompt Planner עם דרישות שלא נזרקות גם אם מודל AI נכשל.
- Generated repository factory רחב יותר.
- Hosted generated-app runtime עם auth/RBAC.
- first registered user = admin.
- deployment-scoped tokens ו-data isolation.
- authenticated WebSocket runtime.
- immutable deployment snapshot גם אחרי שינוי project.
- V10 Android release contract משוחזר ומוקשח.
- Godot 4 source מפורש.
- V10 parity test suite.
- 200-case deterministic benchmark.
- release/recovery policy מחייבת.

## מצב אמת
V25 היא source tree מאוחד ועובד. היא עדיין לא טוענת:
- live local Open-Weight GPU benchmark — חסר GPU endpoint אמיתי.
- Docker hostile runtime PASS — חסר Docker daemon בסביבת הבנייה הנוכחית.
- live PostgreSQL/Redis/S3 integration PASS — השירותים אינם רצים כאן.
- signed AAB/IPA — דורש credentials/toolchains פרטיים.
- console-certified Unreal/Unity game — דורש SDK/רישוי platform-holder.

## הרצה
```bash
python -m pip install -r requirements-demo.txt -r requirements-test.txt
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port 8000
```

## בדיקה
```bash
python -m pytest -q
python scripts/run_v25_offline_benchmark.py
python scripts/run_v25_release_gate.py
```
