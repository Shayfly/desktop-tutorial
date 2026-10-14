# V12 — מדריך אינטגרציה ל-V10

## מה V12 מוסיף בפועל

1. State machine קשיח ל-Build Jobs.
2. PostgreSQL repository ל-jobs.
3. Deployment promotion עם pinning לגרסה/build ספציפיים.
4. בסיס ל-Rollback על ידי קידום artifact קודם.
5. Usage metering ל-AI/build/storage/egress.
6. Artifact provenance עם SHA-256 manifest.
7. FastAPI health/readiness router.
8. Schema נוסף ל-usage events.
9. בדיקות יחידה נוספות ל-state/deploy/usage/provenance.

## חיבור ל-V10

### Startup
```python
from omni_prod.config import Settings
from omni_prod.api_routes import create_production_router

settings = Settings.from_env()
app.include_router(create_production_router(settings))
```

### בעת יצירת Build
- צור `build_id`.
- כתוב `queued` ל-PostgreSQL.
- enqueue ל-Redis/RQ.
- החזר ללקוח build_id מיידית.

### בתוך Worker
- transition `queued -> running`.
- materialize source.
- run inside isolated sandbox.
- validation/repair loop.
- package ZIP.
- create SHA-256 provenance manifest.
- upload artifact + manifest.
- transition `running -> ready`.

בכשל:
- transition `running -> failed`.
- שמור error_code מסווג.
- אל תדליף secrets ל-error_message.

### Promotion
קידום ל-production חייב לקבל:
- project_id
- version_id
- build_id
- immutable artifact_key

אין לפרוס "latest" mutable.

### Rollback
Rollback = promotion חדש ל-artifact/version קודמים.
כך נשמר audit trail ואין mutation של היסטוריה.

## מה עדיין חיצוני
- Android private keystore.
- Apple Developer certificates.
- DNS/domain.
- cloud provider account.
- payment processor production credentials.
