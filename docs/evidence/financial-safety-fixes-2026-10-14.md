# 148AI Financial Safety Fixes — 2026-10-14

[מהתיעוד] G3 remains the completed failure experiment with financial acceptance FAIL: the defect was proven. Historical evidence is unchanged in PR #35 at commit 70e3b7efc2910373824330d2205a57f52d492948. G4 is the corrections and proof. This report covers two targeted defects and a recovery race; it does not certify all four original G4 defects.

## Corrections

[מהקוד] `omni_prod/build_control.py`, `omni_prod/worker_tasks.py`, `omni_prod/routed_gateway.py`: write-ahead journal failure propagates before provider dispatch, blocks fallback, and rolls back this unspent authorization. Final terminal telemetry remains best effort. The production build worker installs the mandatory callback.

[מהקוד] `omni_prod/attempt_ledger.py`: mandatory persistence locks the running build then its active reservation, inserts evidence in that transaction, and refuses an inactive build/reservation. This serializes with recovery and reservation release.

[מהקוד] `omni_prod/subscription_store.py`: release retains a RESERVED reservation when durable provider attempts show known paid cost or uncertain authorized liability. Query/schema failure propagates and does not free funds.

[מהקוד] `omni_prod/maintenance.py`: lost-worker recovery checks durable exposure under the job lock, quarantines exposed work instead of requeueing, and retains the reservation. The locked decision rechecks heartbeat freshness and current cancellation/recovery values.

## Measured proof

[מהתיעוד] Two financial integration tests failed on the original source: two provider charges instead of one in the intact-ledger case, and two instead of zero with the rejected journal write. On the corrected code both passed.

[מהתיעוד] Three additional tests failed with the previous behavior: journal failure swallowed by BuildControl, paid fallback after journal rejection, and termination after a concurrent heartbeat refresh. All three pass with the corrections. The heartbeat test uses real PostgreSQL and commits the refreshed heartbeat between candidate selection and recovery's locked decision.

[מהתיעוד] Focused final run: 115 passed, 3 skipped, 6 subtests passed, 34.15 seconds. Independent review found the heartbeat race, then confirmed its correction with no remaining material finding in the reviewed paths.

| Scenario | Provider receipts | Simulated cost | Reservation | Account reserved amount | Recovery enqueue |
|---|---:|---:|---|---:|---:|
| Durable journal, worker killed before response | 1 | $0.02 | RESERVED | $0.10 / 10 credits | 0 |
| Journal write rejected before dispatch | 0 | $0 | RELEASED | $0 / 0 credits | 0 |

[מהתיעוד] The first case has one UNKNOWN attempt authorized at $0.05 and job error `provider_liability_unknown`; liability remains held, not falsely settled. The second ends with `attempt_ledger_unavailable` and no provider cost. Raw snapshots and exact tested file SHA-256 identities are in `docs/evidence/financial-safety-fixes-2026-10-14.json`. The embedded case source_sha identifies the base fixture schema; it is not the patched code identity.

## Boundaries and remaining gates

[מהתיעוד] Real local PostgreSQL 17.11, loopback HTTP fake provider with separate durable SQLite journal, physical worker kill, production build-worker core and maintenance. Controlled queue delivery; no Redis/RQ transport, API admission, sandbox, staging or production deployment. Commercial provider calls: 0. These results certify the tested build path, not modification or other paid capability journals.

[הסקה] Held UNKNOWN evidence prevents freeing the reservation but does not replace reconciliation. Provider-side idempotency and a separate company-loss ledger remain unresolved. G4 full remains open; G2, G5–G7 are not certified. Actual cost per independently accepted product remains unknown.

[מהתיעוד] Full Windows run: 1,656 passed, 66 failed, 0 errors, 181 skipped, 330 subtests passed; 296.35 seconds. Four new failure names relative to the historical baseline were two stale generated registry reports and two QA cursor fixtures missing the new exposure-query answer. Reports were refreshed and fixtures explicitly return False for no exposure; existing release assertions remain intact. Subsequent affected regression run: 69 passed, 9 skipped in 10.01 seconds. The remaining 62 failure names also appear in the original baseline; their causes are not fully classified. This is not a fully green full-suite run. G2 remains blocked.

[מהקוד] Exact correction locations: journal guard at `omni_prod/build_control.py:45`, `omni_prod/worker_tasks.py:652` and `:975`, `omni_prod/routed_gateway.py:200`, `omni_prod/attempt_ledger.py:277`; exposure/recovery at `omni_prod/subscription_store.py:10` and `:396`, `omni_prod/maintenance.py:158` and `:168`.

[מהתיעוד] Earlier interrupted broad runs are not used as evidence. Historical G3 acceptance remains FAIL; the corrected two-scenario acceptance passes. No merge or production change.
