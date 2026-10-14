# Omni Creator V12 — Release Gate

## Must-pass before real customer data

### Control plane
- [ ] PostgreSQL is the authoritative production DB
- [ ] all build jobs use persistent queue
- [ ] API restart does not lose queued jobs
- [ ] worker restart leaves job recoverable
- [ ] idempotency key on build submission
- [ ] state transition conflicts return safely

### Artifacts
- [ ] immutable artifact keys
- [ ] SHA-256 provenance manifest
- [ ] object versioning / retention
- [ ] artifact malware/dependency scan
- [ ] build logs separated from secrets

### Deployments
- [ ] version + build pinned
- [ ] current production deployment queryable
- [ ] rollback verified
- [ ] deployment isolation verified

### Metering
- [ ] AI input/output usage recorded
- [ ] build seconds recorded
- [ ] storage/egress recorded
- [ ] hard usage caps supported
- [ ] account/project attribution verified

### Security
- [ ] sandbox isolation externally reviewed
- [ ] outbound network policy allowlist where needed
- [ ] secure cookies + CSRF/CORS reviewed
- [ ] rate limiting / abuse protection
- [ ] secret manager in use
- [ ] backups + restore drill

### Mobile
- [ ] signed Android AAB from CI
- [ ] Play internal track install tested
- [ ] iOS signed build from macOS worker
- [ ] TestFlight install tested
