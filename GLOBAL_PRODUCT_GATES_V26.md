# Global Product Gates — V26

Before worldwide public launch, all of these must be green:

- Creator identity persistence: PostgreSQL + email verification + password reset + session revocation.
- Tenant isolation: DB-level owner/org filters + adversarial cross-tenant tests.
- AI brain: live Open-Weight model benchmark on the 200-case catalog with measured success/cost/latency.
- Creative engine: live original image/audio/music/voice/video/3D generation with provenance and rights metadata.
- Execution: isolated remote sandbox; no Docker socket exposed to public API.
- Storage/queue: live PostgreSQL, Redis/RQ, S3/MinIO with backup/restore drills.
- Mobile: reproducible signed Android/iOS builds and store delivery workflow.
- Payments: production checkout/webhooks, idempotency, fraud/abuse controls.
- Security: external penetration test, rate limits, WAF/CDN, TLS, secret rotation, dependency scanning.
- Reliability: load/failure tests, SLOs, alerting, rollback/canary, multi-region plan when scale requires.
- International: accessibility audit, timezone/currency/locale behavior, privacy/terms/data-residency review.
