# Hebrew-first live Intake Assistant — activation runbook (prepared, NOT activated)

Status: implemented and tested with test doubles only. **No paid model call has been made.** Activation needs explicit founder approval of the budget below. Until then every conversation answer is deterministic and the UI says so (`interpreter: "deterministic"`).

## What runs when activated
- The customer message is interpreted by a model through the **worker** (RQ queue `omni-intake`, service `intake-worker`); the worker already holds the Gemini key — **no key is copied to Vercel**.
- Task class `conversation`; recommended / cheapest verified model `gemini-3.1-flash-lite` (REAL_EXECUTION_VERIFIED in `PROVIDER_MATRIX.json`). The model actually used is recorded on every message (`interpreter: model:<id>+deterministic`) with its metered cost.
- Prompt `intake-prompt/2-he-first`: Hebrew is the primary language; evidence quotes must be copied in the original script. Every proposal is re-validated on the API side: unknown fields/values and quotes not found in the message are dropped (Hebrew-aware matching ignores niqqud, bidi marks, gershayim/geresh, maqaf variants — letters are never changed). Malformed output, timeouts, queue or provider errors → deterministic answer, conversation continues.
- Bounds per call: message truncated to 4,000 characters, reply ≤ 700 tokens.
- The model never writes the brief or approves anything; the Supervisor's confidence policy still asks for login / personal data / access scope.

## Issue #12 update — every paid call is a durable reservation

Since Issue #12 a paid intake call happens only after a durable reservation. The flow is QUOTE → RESERVE → CLAIM → EXECUTE → SETTLE; see `docs/INTAKE_BUDGET_RESERVATIONS.md`. The reservation transaction is the hard cap check, and the table below is only a pre-check:
- Greetings (LOW turns) never use a model.
- The API additionally needs `OMNI_REDIS_URL` and the database; the worker needs `OMNI_DATABASE_URL`.
- The `intake-maintain` service must run (outbox relay + lease reconciliation).
- `OMNI_INTAKE_CALL_BUDGET_USD` is no longer what bounds a call: the quote is computed per message from the catalog and the source-backed prices (about $0.002–$0.0046 per message).

## Budget controls (all fail closed — `omni_prod/intake/mode.py`)
| Variable | Where | Proposed value | Effect |
|---|---|---|---|
| `OMNI_INTAKE_MODEL=1` | Vercel + worker | — | founder switch (only the literal `1`) |
| `OMNI_INTAKE_VIA_WORKER=1` | Vercel | — | route through the worker |
| `OMNI_INTAKE_MODEL_BUDGET_USD` | Vercel | `0.05` per project (~30 messages) | per-project cap |
| `OMNI_INTAKE_DAILY_BUDGET_USD` | Vercel | `0.50` / rolling 24 h, all projects | global cap |
| `OMNI_INTAKE_CALL_BUDGET_USD` | Vercel + worker | `0.005` | per-message reserve; a call starts only if spent + reserve ≤ cap; also the worker's hard per-call cap |
Spend is read from `intake_messages.cost_usd`; if it cannot be read, the model is not used.

Double gate on merge: deploy-worker will start `intake-worker`, but it only executes jobs the API enqueues, and the API enqueues only when every condition above holds; the worker additionally refuses without its own `OMNI_INTAKE_MODEL=1` and `OMNI_INTAKE_CALL_BUDGET_USD > 0`. Merging therefore costs $0 until the flags are set.

## Cost estimate (source-backed prices, upper-bound token envelope 2,200 in / 700 out)
| Model | $/message |
|---|---|
| gemini-3.1-flash-lite (recommended) | 0.0016 |
| gemini-3.5-flash-lite | 0.0024 |
| gemini-3.8-flash (not a conversation model; price doubles 2027-01-01 → 0.0086, above the reserve) | 0.0043 |

Acceptance test proposal: 15 scripted conversations (10 Hebrew, 5 English), ~20 messages → **≤ $0.05** upper bound (expected ≈ $0.03).

## Activation steps (founder)
1. Approve the budget (proposed: acceptance test ≤ $0.05; then daily cap $0.50).
2. Merge this PR into pre-staging after green CI and review (deploy-worker starts `intake-worker`).
3. Set the non-secret flags above on Vercel (Preview scope) and on the worker host env; no secret changes.
4. Run the acceptance conversations on the integration Preview; check per message `interpreter`, `cost_usd`, and the attempt ledger; compare Hebrew extraction against the deterministic baseline (`python -m omni_prod.intake.benchmark --model` with `OMNI_INTAKE_BENCH_BUDGET_USD`).
5. Kill switch: unset `OMNI_INTAKE_MODEL` (takes effect on the next message).
