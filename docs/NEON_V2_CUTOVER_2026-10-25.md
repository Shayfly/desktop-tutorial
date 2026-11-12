# Neon v2 cutover and awake audit — 2026-10-25

## Observed cutover state

Owner authorized a new **free** `148ai-db-v2` project in `aws-eu-central-1`, pooled runtime URL with `sslmode=require`, repository migrations and Vercel Production/Preview cutover. Old `148ai-db` must remain intact. No paid plan is authorized.

Creation through the Neon connector returned `action restricted; reason:"organization is managed by Vercel"`. No project was created. Available Vercel connector operations do not include provisioning a Neon marketplace resource. Browser fallback reached Vercel login; the secure method-selection request selected Google, but the subsequent identifier request returned `declined`. Authentication did not complete. No retries after that refusal.

Consequently **no database/environment cutover, no migrations against a new project and no COMPATIBLE verification of a new project have occurred**. Existing Vercel environment variables and the old database are unchanged. The new project is intentionally a new empty database: applying migrations would not copy old users/projects/data. The old database remains retained for later recovery.

## Database usage facts (Neon API read-only)

Project: `quiet-hat-61884615` (`148ai-db`), organization `org-soft-bar-82890573`, Frankfurt, free_v3.

| Metric | Current API value |
|---|---:|
| compute_time_seconds | 397077 |
| CU-hours | 110.299 |
| aggregate active_time_seconds | 1586732 |
| aggregate active hours | 440.759 |
| main branch CU-hours | 104.729 |
| preview branch CU-hours | 5.570 |
| period end | 2026-11-01T00:00:00Z (02:00 Israel) |

The API values do not substantiate the owner's cited 191.9 CU-hours or 5 November reset. Record the discrepancy rather than substituting it for observed values.

Both endpoints use fixed 0.25 CU. CU-hours are not wall-clock uptime, and project usage sums branches. One continuously active 0.25-CU endpoint uses 6 CU-hours/day, exhausting 100 CU-hours in about 16.7 days.

## What prevents idle suspension

`autosuspend=0` means the provider default of 300 seconds; `-1`, not zero, disables suspension. Do not change a default that is already five minutes. Official references: https://neon.com/docs/cli/branches and https://neon.com/docs/introduction/scale-to-zero.

| Source | Behavior | Evidence and limits |
|---|---|---|
| intake-maintain | DB relay/reconcile queries every 10s, including an empty queue | `infra/worker-host/docker-compose.yml:107`; `omni_prod/intake/reservation_worker.py:185`; query implementations `omni_prod/intake/budget.py:435` and `:504` |
| janitor | DB maintenance/recovery queries every 60s | compose lines168–180; `omni_prod/maintenance.py:38`, `:207`, `:293` |
| persistent pools | min2/max10 connections per process, opened eagerly, checkout health query | `omni_prod/db.py:17`; global pool in `investor_app.py:151`. Idle sockets alone are not proven to account for compute use |
| Production Smoke | DB schema checks and synthetic auth writes per main push/manual run | No cron in this workflow; intermittent wakeups |
| deployment verification | DB schema and synthetic persistence checks per deployment/manual run | Intermittent wakeups |
| backup/restore | Daily 02:17 UTC | Wakes DB; not a continuous-activity explanation |
| repo-control health | Every10min, checks repository existence | No Neon query |
| preview-router health | Every30s, plain `ok` response | No DB query |
| PostgreSQL CI | Local PostgreSQL service at127.0.0.1 | Not production Neon |
| idle RQ worker | Polls Redis | Not a PostgreSQL idle poll |

Historical runtime corroboration: Worker diagnostics run39956258956 / job120422739301 at2026-10-23T12:50Z lists janitor and intake-maintain containers Up5hours; janitor reports every60s. Deploy run39917160829 / job120293094407 identifies worker DB as old floral-bread pooled endpoint (fingerprint d2eb0b8c775f). Current25October process state is not verified.

**Inference:** SQL every10/60seconds prevents the required300-second idle window while these services are running. Merely moving to a pooled endpoint does not remove those queries. No polling, pool-size or autosuspend settings were changed during this audit, as the owner required findings before changes.

## Additional cutover dependency

Updating Vercel alone leaves worker-host `.env` pointed to the old database. Queued build IDs created in v2 would then not be found by that worker. Worker connection alignment must be coordinated before an E2E build. Blindly moving both background pollers also recreates continuous activity on v2. No worker configuration was changed.

## Quota diagnosis code change

Previously `/api/v28/deployment` returned only `UNREACHABLE / PoolTimeout`, while driver logs showed a provider quota refusal. The patch adds:

- `QUOTA_EXCEEDED`, `error_code=DATABASE_QUOTA_EXCEEDED`, normalized `provider_status=402` for explicit provider quota refusal or an actual HTTP402. `provider_status_basis` distinguishes a real HTTP status from PostgreSQL message normalization.
- Ordinary connection/pool timeouts remain `UNREACHABLE / DATABASE_UNREACHABLE`.
- Only after a real pool timeout with no retained cause, one connection-only diagnostic probe with connect_timeout2seconds recovers the driver's refusal. This is a libpq connection timeout, not a hard overall request deadline; multiple resolved addresses can extend elapsed time. No query, transaction, business operation or write is replayed. Healthy checks never probe.
- Public diagnostics and verification evidence contain only whitelisted codes, never exception text, URLs or credentials. Metadata endpoint HTTP200 is preserved so deployment verification can read its schema diagnosis.

No intake, pricing or UI implementation is changed. This patch does not itself restore database service or prove a cutover.

## Patch verification

- Focused database/schema/fingerprint/verification suite: 65 passed,71 subtests passed,19.42s.
- Full pytest: 2009 passed,187 skipped,424 subtests passed,0failures/0errors in160.24s. One upstream Starlette deprecation warning remains.
- `python -m compileall -q omni_prod tools tests` and `git diff --check`: passed.
- `python tools/generate_neon_bootstrap.py --check`: bootstrap up to date. Manifest matches37migration files, latest041.
- Independent read-only review: no blocking correctness/secret-disclosure finding; eight focused quota tests passed. Per-address timeout caveat recorded above.
- Code is prepared for review; no claim of production deployment or live new-database compatibility is made.
