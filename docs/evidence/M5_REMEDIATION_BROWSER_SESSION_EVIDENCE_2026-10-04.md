# M5 remediation — browser session transport evidence (2026-10-04)

Scope: LOCAL, memory persistence; real investor_app route functions served via a scratchpad Starlette adapter (fastapi not installable), driven by headless Chromium 141 on http://localhost.

```
POST /api/v28/auth/register -> set-cookie: 148ai_session=...; HttpOnly; Path=/; SameSite=strict; Secure
cookie present=True httpOnly=True secure=True sameSite=Strict
js can read cookie=False
localStorage token=None
session survives reload=True
same-origin cookie write status=200
cross-origin cookie write status=403
cookie after logout=[]
signed out after reload=True
```

Not verified here: the deployed HTTPS origin (Task 12), server-side revocation in memory mode (identity service requires PostgreSQL; logout reports server_session_revoked=false there while still clearing the cookie).
