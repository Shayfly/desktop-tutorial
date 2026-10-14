# Production Gate

## Gate A — Infrastructure
- [ ] PostgreSQL used by control plane
- [ ] Redis queue used by build jobs
- [ ] workers external to API process
- [ ] artifact store persists across restarts
- [ ] backups configured

## Gate B — Sandbox
- [ ] generated code never runs in API process
- [ ] network disabled by default
- [ ] timeout enforced
- [ ] memory enforced
- [ ] CPU enforced
- [ ] PID limit enforced
- [ ] no-new-privileges
- [ ] dropped Linux capabilities
- [ ] ephemeral container cleanup

## Gate C — Security
- [ ] secrets externalized
- [ ] session cookies secure in HTTPS
- [ ] rate limits
- [ ] abuse controls
- [ ] audit events
- [ ] dependency/CVE scanning

## Gate D — Deployment
- [ ] immutable build artifacts
- [ ] version-pinned deployment
- [ ] health/readiness probes
- [ ] canary/rollback mechanism
- [ ] logs + metrics + traces

## Gate E — Mobile
- [ ] Android signing credentials configured
- [ ] signed AAB produced in controlled CI
- [ ] Play internal testing passed
- [ ] iOS macOS signing worker configured
- [ ] TestFlight passed

## Gate F — Billing
- [ ] usage metering
- [ ] plan limits
- [ ] spend guardrails
- [ ] provider cost attribution
- [ ] failed payment handling
