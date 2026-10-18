# Production Smoke — 2026-10-18T20:48:03Z

run: 39164936805
```
GET /api/v28/deployment\nHTTP: 200\nBODY_RAW: {"source_commit": "f53b6dd81164f7bbaadca59e6757e0c59c544a40", "environment": "production", "branch": "main", "schema": {"required": 41, "required_name": "041_company_loss_ledger", "applied_max": 41, "missing": [], "unknown_applied": [], "status": "COMPATIBLE", "compatible": true, "schema_migrations_present": true, "db_host": "ep-floral-bread-b1weu1th.c-5.eu-central-1.aws.neon.tech", "db_fingerprint": "5fabb3bf756d"}}
CHECK deployment schema: PASS
GET /api/v28/me\nHTTP: 401\nBODY_RAW: {"detail": "authentication required"}
CHECK unauthenticated me: PASS
::add-mask::eyJhbGciOiJIUzI1NiIsInR5cCI6Ik9NTkkifQ.eyJzdWIiOiJ1c3JfTWFXc0k5Mlc1UUQyak1qZiIsIm9yZyI6IjE0OGFpLWNvbnRyb2wiLCJyb2xlIjoiY3JlYXRvciIsImV4cCI6MTc5Mjk2MTI3Niwic2lkIjoic2VzX01qai1hbjNZVE1EY2oyZlNDU3hfWU5YSSJ9.HyPzqDq71aVjv0UchCYSM3760thq7hI1YDxRiCdAVrE
POST /api/v28/auth/register\nHTTP: 200\nBODY_RAW: {"user": {"id": "usr_MaWsI92W5QD2jMjf", "email": "smoke-1792356475-8daefbe6a8e4@example.com", "created_at": "2026-10-18T20:47:55.940281+00:00"}, "token": "[REDACTED]", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["deterministic/local zero-paid-provider builds", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}}
CHECK register: PASS
::add-mask::eyJhbGciOiJIUzI1NiIsInR5cCI6Ik9NTkkifQ.eyJzdWIiOiJ1c3JfTWFXc0k5Mlc1UUQyak1qZiIsIm9yZyI6IjE0OGFpLWNvbnRyb2wiLCJyb2xlIjoiY3JlYXRvciIsImV4cCI6MTc5Mjk2MTI3OCwic2lkIjoic2VzX2dxcjhmNUhHSnYtU0hZblVWUzZSVEpMeSJ9.dPxlNYmLfA_xq6ItttdUX65XYlHEvi54Ri4g8HSTEaA
POST /api/v28/auth/login\nHTTP: 200\nBODY_RAW: {"user": {"id": "usr_MaWsI92W5QD2jMjf", "email": "smoke-1792356475-8daefbe6a8e4@example.com"}, "token": "[REDACTED]", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["deterministic/local zero-paid-provider builds", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}}
CHECK login and Set-Cookie: PASS
GET /api/v28/me\nHTTP: 200\nBODY_RAW: {"id": "usr_MaWsI92W5QD2jMjf", "email": "smoke-1792356475-8daefbe6a8e4@example.com", "created_at": "2026-10-18T20:47:55.940281+00:00", "subscription": {"plan": {"code": "free", "name": "Free", "monthly_price_usd": "0", "annual_price_usd": "0", "included_credits": 150, "max_projects": 2, "seats": 1, "allowed_cost_classes": ["zero"], "branding": "required", "removable_branding": false, "white_label": false, "priority": "standard", "features": ["deterministic/local zero-paid-provider builds", "version history", "rights/IP checks", "export with 148AI branding", "community/self-service support"], "status": "prelaunch-proposed"}, "credits_used": 0, "credits_remaining": 150, "cycle": "2026-10"}, "status": "PENDING_VERIFICATION", "email_verified": false, "email_verified_at": null}
CHECK authenticated me: PASS

| Test | PASS/FAIL | HTTP |
|---|---|---|
| deployment schema | PASS | 200 |
| unauthenticated me | PASS | 401 |
| register | PASS | 200 |
| login and Set-Cookie | PASS | 200 |
| authenticated me | PASS | 200 |
```
