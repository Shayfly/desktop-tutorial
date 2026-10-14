# V10 Recovery & Parity — אמת טכנית

## מה נמצא
- קובץ V10 המקורי עדיין רשום ב-Library: `OmniCreator-Product-V10-PRODUCTION.zip`.
- File ID: `file_0000000015a481f48a0232955a52070e`.
- גודל: 183,817 bytes.
- Validation המקורי נמצא: `VALIDATION-V10.md`, file id `file_00000000506c8210adf8464374c2f550`.

## מגבלת גישה
ה-Library מאשר את קיום V10 ואת המטא-דאטה, אך raw-byte materialization של ZIP הישן נחסם על-ידי שכבת ההרשאות של Project files. לכן V25 לא טוענת שורה-לשורה merge של source V10 שלא נקרא.

## מה כן שוחזר והוכח ב-V25
V25 משתמשת ב-VALIDATION המקורי כחוזה התנהגות ומחזירה את היכולות הבאות כחלק מה-Unified Core:
- generated-app authentication + RBAC
- hosted deployment authentication and data isolation
- authenticated WebSocket
- maps / realtime / payments capability planning
- Android Studio source generation
- explicit Godot 4 source generation
- safe repository patch/add-file contract
- Omni Creator Android source + AAB CI contract
- immutable project versions and deployed-version isolation
- Uber-style HTTP acceptance flow

## V10 baseline המקורי
ה-Validation המקורי תיעד 35/35 PASS, Uber prompt עם modules customers/drivers/rides/payments, capabilities analytics/auth/export/maps/notifications/payments/realtime/roles/search, 42 repository files, preview/export/native/web/promotion, launch score 100, unauthenticated hosted CRUD=401, first app user=admin, authenticated ride CRUD, patch→new version, deployment isolation ו-data persistence.

## V25 parity evidence
- `tests/test_v25_unified_v10_parity.py`
- `LIVE_HTTP_V25.json`
- `BENCHMARK_V25_OFFLINE.json`
- full pytest suite

העיקרון: V10 היא baseline evidence. V25 היא ה-source of truth החדש. אין יותר תלות תפעולית ב-V10 כדי להמשיך לפתח.
