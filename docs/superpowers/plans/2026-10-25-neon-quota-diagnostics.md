# Neon cutover and quota diagnostics implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution, with a read-only parallel consumption audit.

**Goal:** Establish a new free Frankfurt database and distinguish confirmed quota exhaustion from connectivity failure without changing intake, pricing or UI.
**Architecture:** Preserve the old database. Apply repository migrations and verify checksums on a new empty database before switching Vercel runtime connections to its pooled TLS URL. Preserve schema metadata HTTP 200; expose a safe quota error category and normalized provider status 402 within schema diagnostics. A pool timeout does not retain its driver cause, so perform one bounded connection-only probe on that failure path; never retry writes.
**Tech stack:** Python/FastAPI, psycopg, Neon, Vercel.
**Spec:** Owner instruction dated 2026-10-25 in this session.

## Constraints and review focus

- No paid upgrades; no deletion of old project; no copying inaccessible old data is claimed.
- No intake, pricing, UI, polling or autosuspend changes without reporting findings.
- SQL migration uses direct connection; application uses pooled connection with sslmode=require.
- Confirmed provider HTTP 402 or explicit Neon quota message -> QUOTA_EXCEEDED; a generic timeout remains UNREACHABLE.
- Never emit DSNs, credentials or raw exception messages. Unknown failures must not be labelled quota.
- Healthy schema checks must not add probes or queries.

## Tasks

- [ ] Create free project via Vercel (Neon API creation is restricted for this Vercel-managed org); authentication currently blocked.
- [ ] Bootstrap empty schema using committed migrations; compare version set and exact checksums.
- [ ] Update Vercel Production and existing Preview database variables, deploy, verify COMPATIBLE and new DB fingerprint. Worker cutover remains explicitly separate.
- [x] Add failing tests for direct/caused quota, real pool timeout plus driver quota, ordinary timeout, healthy no-probe and secret-safe evidence.
- [x] Implement narrow failure categorization in schema diagnostics and preserve category in deployment verification evidence.
- [ ] Run focused and full tests, independent review, publish a reviewable PR without merging.
- [ ] Report awake audit and migration blocker; preserve old configuration and project.
