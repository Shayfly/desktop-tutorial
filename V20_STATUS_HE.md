# Omni Creator V20 — Observability + Recovery Gate

- Request ID generation/preservation.
- HTTP response `X-Request-ID`.
- Metrics registry + Prometheus text endpoint.
- HTTP request count, 5xx count and latency observations.
- SLO evaluation by error rate and p95 latency.
- Structured events with secret redaction.
- Backup manifest with SHA-256 and size verification.
- Backup/restore drill simulation.
- Production DB schema for backup records and operational events.

Live release validation must verify request IDs and metrics on the exact clean-extracted ZIP.
