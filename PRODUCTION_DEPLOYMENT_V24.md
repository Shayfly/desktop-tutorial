# Omni Creator V24 — production deployment model

## Trust boundaries

1. **Public API/UI node** — never receives a Docker socket.
2. **Control plane** — PostgreSQL, Redis/RQ and S3-compatible immutable artifacts.
3. **Sandbox runner node** — dedicated isolated host/runtime. API calls it using HMAC-authenticated requests (`OMNI_SANDBOX_RUNNER_URL` + `OMNI_SANDBOX_SHARED_SECRET`).
4. **Model endpoint** — OpenAI-compatible local/open-weight inference endpoint. It can live on a GPU provider or a private GPU host.
5. **External model fallback** — off by default and fail-closed behind budget/call limits.

`docker-compose.international.yml` contains a staging convenience sandbox runner that mounts the host Docker socket. That is **not** the preferred production topology. The canonical `docker-compose.production.yml` requires a dedicated sandbox URL instead.

## Required production gates

- HTTPS and explicit `OMNI_ALLOWED_ORIGINS`.
- 64+ character `OMNI_SECRET_KEY` and 32+ character sandbox shared secret.
- PostgreSQL migrations 001–010 applied under migration lock.
- Redis/RQ live integration green.
- S3 round-trip/integrity green.
- GPU/local-model live benchmark executed.
- Live sandbox hostile suite green on the isolated runner.
- Android signing and iOS signing are configured only in secret-managed CI.
- Backups + restore drill completed.
- Load test and SLO thresholds recorded before public launch.
