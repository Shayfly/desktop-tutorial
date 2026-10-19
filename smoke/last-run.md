# Production Smoke — 2026-10-19T19:11:43Z

run: 39308870917
```
GET /api/v28/deployment\nHTTP: 200\nBODY_RAW: {"source_commit": "4b019d8fabbf4f2493f47d492c3047a9ccc7f082", "environment": "production", "branch": "main", "schema": {"required": 41, "required_name": "041_company_loss_ledger", "applied_max": 41, "missing": [], "unknown_applied": [], "status": "COMPATIBLE", "compatible": true, "schema_migrations_present": true, "db_host": "ep-floral-bread-b1weu1th.c-5.eu-central-1.aws.neon.tech", "db_fingerprint": "5fabb3bf756d"}}
CHECK deployment schema: PASS
GET /api/v28/me\nHTTP: 401\nBODY_RAW: {"detail": "authentication required"}
CHECK unauthenticated me: PASS
POST /api/v28/auth/register\nHTTP: 200\nBODY_RAW: {"user": {"id": "usr_xd6PwBo94hs8gZXg", "email": "smoke-1792437096-22c777143604@example.com", "created_at": "2026-10-19T19:11:36.373801+00:00"}, "token": "[REDACTED]", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero", "light"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["up to 3 light builds a month", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}}
CHECK register: PASS
POST /api/v28/auth/login\nHTTP: 200\nBODY_RAW: {"user": {"id": "usr_xd6PwBo94hs8gZXg", "email": "smoke-1792437096-22c777143604@example.com"}, "token": "[REDACTED]", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero", "light"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["up to 3 light builds a month", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}}
CHECK login and Set-Cookie: PASS
GET /api/v28/me\nHTTP: 200\nBODY_RAW: {"id": "usr_xd6PwBo94hs8gZXg", "email": "smoke-1792437096-22c777143604@example.com", "created_at": "2026-10-19T19:11:36.373801+00:00", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero", "light"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["up to 3 light builds a month", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}, "status": "PENDING_VERIFICATION", "email_verified": false, "email_verified_at": null}
CHECK authenticated me: PASS

| Test | PASS/FAIL | HTTP |
|---|---|---|
| deployment schema | PASS | 200 |
| unauthenticated me | PASS | 401 |
| register | PASS | 200 |
| login and Set-Cookie | PASS | 200 |
| authenticated me | PASS | 200 |
```
