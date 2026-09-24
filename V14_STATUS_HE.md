# Omni Creator V14 — Cumulative Orchestrator

## תיקון אריזה חשוב
V14 נבנתה מחדש באופן cumulative משלוש החבילות הקודמות:
- V11 Production Overlay
- V12 Production Control Plane
- V13 Resilience & Cost Control

כך קבצי config/db/queue/storage/sandbox/worker של V11 נמצאים בפועל יחד עם רכיבי V12/V13.

## חדש ב-V14
- Build Orchestrator
- Retry policy + exponential backoff contract
- Error taxonomy
- Repair-loop decision engine
- Per-build AI/time/repair budgets
- Canary evaluation
- Rollback trigger contract
- Orchestration SQL fields/events

## אמת תפעולית
מה שנבדק מקומית: imports/compile/unit tests/ZIP integrity/package completeness.
מה שלא ניתן לאמת בלי תשתית חיצונית: PostgreSQL/Redis/S3 live connections, Docker daemon isolation under real load, DNS/TLS, Android signing, Apple signing, cloud autoscaling, production payment webhooks.
