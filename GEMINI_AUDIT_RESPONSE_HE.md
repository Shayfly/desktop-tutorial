# תגובת Omni Creator לביקורת Gemini

## ממצאים שאומצו ותוקנו ב-V21
1. **Connection Pooling** — נכון. V20 פתחה connection ישיר. V21 מוסיפה `DatabasePool` מבוסס `psycopg_pool`.
2. **Production adapter wiring** — נכון שצריך fail-closed wiring. V21 מוסיפה `production_adapters.py`, וב-Production אין בחירה אוטומטית ב-memory adapters.
3. **Live integration tests** — נכון. נוספה סוויטה opt-in אמיתית עבור PostgreSQL / Redis / S3.
4. **Circuit breaker distributed state** — נכון עבור multi-instance. נוסף `RedisCircuitBreaker`.
5. **Sandbox hardening** — למרות שה-Sandbox כבר היה Docker isolated, נוספו non-root user, memory-swap cap, ulimit, tmpfs hardening ו-environment מצומצם.

## טענות בביקורת שלא תאמו את V20 בפועל
1. `db.py/get_db_connection` — symbol כזה לא היה קיים. `db.py` השתמש ב-`psycopg.connect`.
2. `storage.py/S3StorageAdapter` עם local fallback — לא היה. V20 השתמשה ב-`boto3` ישירות וללא fallback מקומי.
3. `sandbox.py/execute_code` שרץ בתוך Python process — לא היה. V20 כבר השתמש ב-`docker run` עם:
   - `--network none`
   - `--read-only`
   - `--security-opt no-new-privileges:true`
   - `--cap-drop ALL`
   - CPU / Memory / PID limits
4. `metrics.py/log_metric` — symbol כזה לא היה. V20 כבר כללה `render_prometheus()` ו-endpoint `/_omni/metrics`.
5. `intent.py` / `planner.py` — אינם חלק מ-overlay V20 שנמסר לביקורת ולכן לא היה ניתן לאמת אותם מתוך החבילה.

## מה עדיין לא מסומן PASS
- Docker hostile-code live test.
- PostgreSQL / Redis / S3 live integration בסביבה הזו.
- Load test אמיתי.
- merge פיזי ל-V10.
- signed Android AAB / iOS IPA.

כל אלה נשארים gates חיצוניים ולא הומרו ל-PASS באמצעות mocks.
