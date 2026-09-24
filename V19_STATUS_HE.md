# Omni Creator V19 — Reliability / Transactional Outbox

- Transactional outbox contract with deterministic dedupe key.
- Batch claim contract using `FOR UPDATE SKIP LOCKED`.
- Retry scheduling with bounded backoff.
- Dead-letter decision model.
- Worker lease and reclaim model.
- Circuit breaker: closed/open/half-open.
- Recovery simulation included in release validation.
