# Intake budget reservations, complexity routing, requirements preservation (Issue #12)

Status: implemented and tested on real PostgreSQL 16 and real Redis/RQ locally. **Not activated**: no paid model call has been made; every paid flag stays off. Code: `omni_prod/intake/{budget,reservation_worker,worker_route,complexity,lanes,agent,interpreter,mode}.py`, migration `infra/postgres/037_intake_budget_reservations.sql`.

## 1. What existed and what was reused

| Existing piece | Used for | Notes |
|---|---|---|
| psycopg 3 + `DatabasePool` (`omni_prod/db.py`) | all reservation SQL | no ORM added |
| `migrations.py` / `migration_runner.py` (advisory lock, checksums) | migration 037 | additive only |
| transactional-outbox pattern of `build_outbox` + `dispatch_pending_outbox` (`FOR UPDATE SKIP LOCKED`, conditional consumer transition) | `intake_outbox` + `ReservationService.relay_once` | same guarantees, separate table (build outbox is FK-bound to `build_requests`) |
| `credit_reservations` (builds) | **not reused** | one row per build, status RESERVED/SETTLED/RELEASED, no UNKNOWN state, no scopes/rolling window: does not give the required guarantees |
| `RoutedModelGateway` write-ahead `AttemptRecorder` | execution + metering boundary | the worker binds it to the reservation (budget = quote, 1 external call, 0 transient retries, allowed models) |
| `build_approvals` (030) | approvals bound to brief revision/fingerprint/contract/quote | unchanged; chat text never approves |
| `ProjectBrief` revisions + `intake-requirements/1` | single source of truth for requirements | no parallel store |

## 2. Reservation state machine

```
           reserve()                claim()               mark_executing()            settle()
QUOTE ───────────────► RESERVED ──────────────► CLAIMED ────────────────────► EXECUTING ──────────► SETTLED (CONFIRMED | CONFIRMED_ZERO | ESTIMATED, actual_usd NOT NULL)
 (code)                   │  │ release()            │  release() / lease expiry     │  settle(UNKNOWN) or lease expiry (reconcile)
                          │  └─ stale (reconcile) ──┴────────► RELEASED            └──────────► UNKNOWN (actual_usd NULL, quote held)
                          │                                                                       │ resolve_unknown(amount, evidence, who)
                          └─ claim() after max age → RELEASED                                    └──────────► SETTLED
```
* RESERVED/CLAIMED → RELEASED is allowed only because the provider was certainly not contacted: the EXECUTING marker is committed **before** the call.
* EXECUTING never goes to RELEASED. An expired EXECUTING lease becomes UNKNOWN and keeps the full quote counted until `resolve_unknown` is given an amount and billing evidence. Nothing is replayed automatically.
* DB constraints enforce the cost invariants: SETTLED ⇒ amount present; UNKNOWN ⇒ amount NULL + reason; CONFIRMED_ZERO ⇒ amount = 0; CLAIMED/EXECUTING ⇒ claim token + lease.
* Every transition writes an `intake_reservation_events` row (append-only audit).

Counted amount per scope: RELEASED → 0, SETTLED → `actual_usd`, every other state (incl. UNKNOWN) → `quoted_usd`. The rolling 24 h scope counts settled rows reserved within 24 h and **every** unsettled row regardless of age.

Scopes (sorted text = lock order):
* production lane: `daily:global` (rolling 24 h, all projects) and `project:<account>:<project>` (lifetime cap per project)
* campaign lane (acceptance tests): `campaign:<id>` (hard cap, ≤ $10 in code) and `campaign-test:<id>:<account>:<project>` (per-test allocation). Campaign rows never touch `daily:global`, and production rows never touch campaign scopes.

## 3. Lock order and why it is deadlock-free

Locks taken by each operation:

| Operation | Locks (in order) |
|---|---|
| reserve | anchors created in a *separate* short transaction (no lock carried over); then `SELECT … FOR UPDATE` on each scope anchor **one statement per scope, ascending text order**; inserts of new rows |
| settle / release / resolve_unknown | scope anchors of that reservation, ascending order; then the reservation row |
| claim / mark_executing / reconcile→UNKNOWN | the single reservation row only (conditional UPDATE) |
| relay_once | one `intake_outbox` row, `FOR UPDATE SKIP LOCKED` |

Proof sketch: give every lockable object a rank — scope anchors ranked by their text, all ranked below every reservation row, reservation rows below outbox rows. Each transaction acquires locks in strictly increasing rank (scope anchors sorted; the reservation row last; the outbox row only alone). A wait-for cycle would need a transaction to hold a higher-ranked lock while waiting for a lower one, which no code path does. Transactions that lock only one reservation row never request a scope lock afterwards. Hence no cycle exists, so there are no deadlocks. No aggregate is read `FOR UPDATE`: the sums are plain SELECTs taken *after* the anchor locks, so under READ COMMITTED they see every competitor that committed before releasing the anchor. No lock is held during the provider call (claim and mark_executing commit first; settle opens a new transaction afterwards).

Evidence:
* `ConcurrencyTests.test_mixed_lifecycle_100_operations_keep_every_cap`: 110 concurrent mixed operations (reserve, claim, execute, settle, UNKNOWN, release, reconcile); PostgreSQL's own `pg_stat_database.deadlocks` stays unchanged.
* `test_deadlock_detector_is_live_negative_control`: opposite-order locking *does* deadlock and the counter rises by exactly 1, so the zero above is meaningful.

## 4. Budget and retry safety guarantees

* **Quote = full envelope.** One external call; `transient_retries=0` (the OpenAI-compatible routes have no provider idempotency key, so a retry could double-bill); no fallback call (`max_external_calls_per_build=1`).
  - The quote is the maximum worst case over every allowed model.
  - Input is bounded by prompt bytes + 64 (the gateway's own bound); output by `max_tokens`, which includes reasoning tokens for these routes (`ceiling_basis` is stored in every quote).
  - Missing catalog, price or eligible model → `QuoteUnavailable` → no call.
* **The gateway cannot exceed the quote.** On the worker, the external budget equals the quoted amount. A route whose worst case is higher is refused before contact (test: `test_route_above_quote_is_refused_before_contact`, 0 provider calls).
* **Caps hold under concurrency.**
  - 60 concurrent reserves on a project cap of 10 units: exactly 10 succeed.
  - 55 concurrent reserves across projects on a daily cap of 7: exactly 7 succeed.
  - 60 concurrent campaign reserves of $0.90 on $10: exactly 11 succeed, and the production daily scope is unchanged.
  - 50 concurrent conversation turns with a daily cap of 5 quotes: ≤ 5 reservations; the rest answer deterministically.
* **No silent $0.**
  - Provider-reported cost → CONFIRMED.
  - Reported tokens × source-backed price → ESTIMATED.
  - Provider never contacted (no write-ahead attempt) → CONFIRMED_ZERO.
  - Timeout, HTTP 429/500 or any missing usage after contact → **UNKNOWN**, with NULL amount and the quote held. This holds even though `RoutedModelGateway._release_rejected` sets its internal metered cost to 0 for HTTP errors: intake metering ignores that and requires reported usage.
  - The intake path no longer turns a missing provider cost into `'0'`.
* **Idempotency.**
  - 50 concurrent reserves with one key produce 1 reservation; the same key used for another project raises `IdempotencyConflict`.
  - Duplicate settlement of the same outcome returns the stored result; a different outcome or a wrong claim token raises `StaleClaim`.
* **Duplicate delivery.** 50 concurrent deliveries of one reservation invoke the provider once. On real Redis/RQ, 3 deliveries with the same job id plus one with a different id invoke it once (counted in Redis and by EXECUTING events).
* **Crash safety.**
  - Crash after claim, before the EXECUTING marker: reconcile releases (certain no contact).
  - Crash after the marker: reconcile marks UNKNOWN and holds the funds.
  - A late worker cannot resume an expired lease.
  - Outbox: Redis down → the row stays pending; replay delivers it. A crash between enqueue and commit causes a re-delivery, which the claim deduplicates.
* **Tenant isolation.**
  - Scope keys contain the account id, so the same project id under two tenants gets separate caps.
  - `get(…, account_id=)` hides other tenants' reservations.
  - Ids containing `:` are refused, preventing scope injection.
* **Fail closed everywhere on the API side.** A quote/budget/DB/schema error, an unreachable queue, or no reservation service → deterministic answer, $0 (an enqueue failure releases the reservation immediately).
* **No unreserved path.** The legacy message-only worker job refuses. A direct model gateway on the API host is refused by `mode.resolve`.

## 5. Complexity classification and lanes

`omni_prod/intake/complexity.py` (deterministic, $0) classifies each turn as LOW / MEDIUM / HIGH / RISKY. It uses:
- the message;
- the last 4 turns;
- the last assistant actions;
- the customer's confirmed fields.

The rules:
* **RISKY:** payments/money/cost, deletion/destructive actions, secrets/credentials, personal data/permissions/security, approvals/publishing. Negation does not lower the risk. A short reply (≤ 4 words or an affirmation such as "כן", "ok", "👍") right after an assistant turn that raised any of these is also RISKY.
* **HIGH:** at least 2 architecture/integration/scale signals, a long multi-part spec, or a contradiction with a confirmed field.
* **LOW:** only an exact greeting/thanks with no sensitive context in recent turns.
* **MEDIUM:** everything else. Ambiguity is never LOW.

`omni_prod/intake/lanes.py`:
* LOW → deterministic, no model.
* MEDIUM/HIGH/RISKY → standard lane, task `conversation`, mandatory floor **70** (unchanged).
* RISKY → model proposals for material fields are only pre-selected and asked, never applied.
* Low-risk sub-70 lane: disabled. It needs a qualification record (≥ 150 Hebrew cases, ≥ 95 %, zero sensitive false negatives, verified pricing, no tool permissions) and none exists. Even when qualified it serves LOW only.

Corpus: `tests/test_intake_complexity.py`, 129 turns with conversation context (109 Hebrew or mixed Hebrew/English; 15 LOW, 36 MEDIUM, 7 HIGH, 71 RISKY); 71 sensitive cases, 0 false negatives. The corpus was written by the implementer; it is a regression net, not evidence of real-world coverage.

## 6. Requirements preservation

* A value the customer confirmed (`answer` or `message` source) is never overwritten by a model proposal. Nor is a material field (login, personal data, access scope) overwritten by a deterministic one. Either becomes a **conflict**: the confirmed value stays, and the reply says "קודם נקבע … עכשיו הבנתי … לא שיניתי — מה נכון?" and asks that question first.
* A non-material change in the customer's own words is applied and reported ("עדכנתי").
* Model output validation is strict:
  - top-level object;
  - lists for `proposals`/`requirements`;
  - typed fields, at most 30 proposals and 12 requirements;
  - size cap 50k characters;
  - `delegate_rest` must be boolean;
  - evidence must appear in the message (Hebrew-aware normalization).
* Free-text model "requirements" never become brief fields or contract entries.
* The Chief Architect still receives `intake_requirements.build(brief)`: validated, `intake-requirements/1`, bound to the brief fingerprint. Approvals remain the server-bound `build_approvals` (any brief/plan/budget change invalidates them; existing real-PG tests in `tests/test_discovery_and_approval.py`).

## 7. Migration 037 and rollback

* Additive:
  - 5 new tables;
  - 2 nullable columns on `intake_messages`;
  - `intake_messages.cost_usd` becomes nullable (NULL = UNKNOWN).
* Applied by the existing runner (advisory lock + checksum).
* The Neon bootstrap was regenerated with `tools/generate_neon_bootstrap.py` and verified on an empty PostgreSQL with `infra/staging/verify_neon_bootstrap.py` (33 migrations).
* Upgrade test: a 036 database with data, then 037 → data intact; a second run applies nothing.
* Compatibility: deterministic turns never write the new columns, so the new code still works on a 036 database (paid turns cannot run without 037: a reservation error fails closed).
* Rollback of code: the previous release ignores the new tables. Reading a NULL `cost_usd` shows "None" only in the message view. SQL sums ignore NULL; the authoritative amount is the reservation.
* Rollback of schema (manual, only after no reservation is RESERVED/CLAIMED/EXECUTING/UNKNOWN):
  ```sql
  UPDATE intake_messages SET cost_usd = 0 WHERE cost_usd IS NULL;   -- only after UNKNOWNs were resolved
  ALTER TABLE intake_messages ALTER COLUMN cost_usd SET NOT NULL;
  ALTER TABLE intake_messages DROP COLUMN IF EXISTS reservation_id, DROP COLUMN IF EXISTS cost_state;
  DROP TABLE intake_reservation_events, intake_outbox, intake_reservation_scopes, intake_reservations, intake_budget_scopes;
  DELETE FROM schema_migrations WHERE version = 37;
  ```

## 8. Operations

* `intake-maintain` compose service: `python -m omni_prod.intake.reservation_worker maintain --loop 10` (outbox relay + lease reconciliation; no provider call).
* Unknown costs: list `state='UNKNOWN'` rows and resolve each one with `ReservationService.resolve_unknown(id, cost_state, actual_usd, evidence, resolved_by)` from the provider billing export.
* Campaign lane variables:
  - `OMNI_INTAKE_CAMPAIGN_BUDGET_USD` (clamped to ≤ $10);
  - `OMNI_INTAKE_CAMPAIGN_TEST_BUDGET_USD` (per-test allocation).
  Selecting the campaign lane needs a code path that passes `lane='campaign'`; nothing in the customer flow does.

## 9. Residual risks / not verified

* No live provider call has been made, so the following are unmeasured:
  - real Hebrew extraction quality;
  - real billed tokens versus the quote bound (overruns are detected and flagged at settlement, not prevented);
  - whether `max_tokens` bounds Gemini Flash-Lite thinking in billing.
  The first paid acceptance test must check `output_overrun` = false.
* `RoutedModelGateway._release_rejected` still assumes HTTP errors are free for the **build** pipeline's in-memory budget. Intake does not rely on it; changing it for builds is outside this issue.
* Rolling-window membership uses `reserved_at`. A call reserved 23:59 h ago and settled later drops out at 24 h after the reservation.
* A campaign/acceptance entry point (who may run the campaign lane) is not wired to any endpoint yet.
* DNS rebinding and the other verifier risks from PR #11 are unrelated to this PR.
