-- Internal read-only export. One row per build, phase, route and cost basis;
-- intake reservations have their own run IDs and are never allocated to a build by guesswork.
-- Run on a 148AI operational database, e.g. psql "$DATABASE_URL" -f scripts/observed_model_costs.sql
WITH llm AS (
    SELECT a.build_id, a.task_type AS phase, a.provider, a.model,
           CASE
               WHEN a.reconciled_cost_usd IS NOT NULL THEN 'RECONCILED'
               WHEN a.provider_reported_cost_usd IS NOT NULL THEN 'PROVIDER_REPORTED'
               WHEN a.metered_cost_usd IS NOT NULL AND a.input_tokens IS NOT NULL
                    AND a.output_tokens IS NOT NULL AND a.price_catalog_version IS NOT NULL THEN 'USAGE_PRICED'
               WHEN a.outcome = 'error' AND a.metered_cost_usd = 0 THEN 'RECORDED_ZERO'
               ELSE 'UNKNOWN'
           END AS basis,
           coalesce(a.reconciled_cost_usd, a.provider_reported_cost_usd, a.metered_cost_usd) AS usd,
           a.attempt_id AS event_id
    FROM task_attempts a WHERE a.kind = 'provider_call'
), media AS (
    SELECT u.build_id, 'media' AS phase, u.provider,
           coalesce(u.usage_json->>'model', u.evidence_json->>'model') AS model,
           CASE WHEN u.actual_cost_usd IS NOT NULL THEN 'PROVIDER_REPORTED'
                WHEN u.usage_json->>'cost_basis' = 'computed_from_usage'
                 AND u.usage_json->>'computed_cost_usd' ~ '^[0-9]+([.][0-9]+)?$' THEN 'USAGE_PRICED'
                ELSE 'UNKNOWN' END AS basis,
           coalesce(u.actual_cost_usd, CASE WHEN u.usage_json->>'computed_cost_usd' ~ '^[0-9]+([.][0-9]+)?$'
                                      THEN (u.usage_json->>'computed_cost_usd')::numeric END) AS usd,
           u.event_key AS event_id
    FROM provider_usage_events u
    UNION ALL
    SELECT p.build_id, 'media', p.provider, NULL, 'UNKNOWN', NULL, p.id
    FROM provider_execution_attempts p
    WHERE NOT EXISTS (SELECT 1 FROM provider_usage_events u
                      WHERE (u.build_id, u.requirement_id, u.provider) = (p.build_id, p.requirement_id, p.provider))
), build_costs AS (
    SELECT 'build' AS run_type, b.id AS run_id, b.created_at AS run_at, b.status AS run_status,
           (b.evidence_json->>'external_model_calls')::integer AS worker_llm_calls,
           e.phase, e.provider, e.model, coalesce(e.basis, 'NO_RECORDS') AS basis,
           count(e.event_id) AS records,
           sum(e.usd) FILTER (WHERE e.basis <> 'UNKNOWN') AS known_usd
    FROM build_jobs b
    LEFT JOIN (SELECT * FROM llm UNION ALL SELECT * FROM media) e ON e.build_id = b.id
    GROUP BY b.id, e.phase, e.provider, e.model, e.basis
), intake_costs AS (
    SELECT 'intake' AS run_type, i.id AS run_id, i.reserved_at AS run_at, i.state AS run_status,
           NULL::integer AS worker_llm_calls, 'conversation' AS phase, i.provider, i.model,
           CASE WHEN i.state = 'SETTLED' AND i.actual_usd IS NOT NULL THEN
                 CASE i.cost_state WHEN 'CONFIRMED' THEN 'PROVIDER_REPORTED'
                                   WHEN 'CONFIRMED_ZERO' THEN 'RECORDED_ZERO'
                                   WHEN 'ESTIMATED' THEN 'USAGE_PRICED' ELSE 'UNKNOWN' END
                ELSE 'UNKNOWN' END AS basis,
           1::bigint AS records,
           CASE WHEN i.state = 'SETTLED' AND i.cost_state IN ('CONFIRMED','CONFIRMED_ZERO','ESTIMATED')
                THEN i.actual_usd END AS known_usd
    FROM intake_reservations i WHERE i.state IN ('EXECUTING', 'SETTLED', 'UNKNOWN')
), ledger AS (
    SELECT * FROM build_costs UNION ALL SELECT * FROM intake_costs
), coverage AS (
    SELECT ledger.*, sum(known_usd) OVER run AS run_known_subtotal_usd,
           sum(records) FILTER (WHERE phase IS DISTINCT FROM 'media') OVER run AS llm_records,
           bool_or(basis = 'UNKNOWN') OVER run AS has_unknown,
           bool_or(basis = 'NO_RECORDS') OVER run AS no_records
    FROM ledger WINDOW run AS (PARTITION BY run_type, run_id)
), priced AS (
    SELECT coverage.*, CASE
        WHEN no_records AND worker_llm_calls = 0 THEN 'ZERO_EXTERNAL_RECORDED'
        WHEN no_records THEN 'UNKNOWN'
        WHEN has_unknown OR (run_type = 'build' AND worker_llm_calls > coalesce(llm_records, 0))
            THEN CASE WHEN run_known_subtotal_usd IS NULL THEN 'UNKNOWN' ELSE 'PARTIAL' END
        ELSE 'PRICED_RECORDS' END AS run_coverage
    FROM coverage
)
SELECT run_type, run_id, run_at, run_status, worker_llm_calls, phase, provider, model, basis,
       records, known_usd, run_coverage, run_known_subtotal_usd,
       CASE run_coverage WHEN 'PRICED_RECORDS' THEN run_known_subtotal_usd
                         WHEN 'ZERO_EXTERNAL_RECORDED' THEN 0 END AS run_cost_usd
FROM priced
ORDER BY run_at DESC, run_type, run_id, phase, provider, model, basis
