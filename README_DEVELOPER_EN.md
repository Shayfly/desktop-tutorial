# Omni Creator V24 — Developer Handoff

V24 is a cumulative international-readiness release built on V23. It is designed to be audited, not trusted by assertion.

## Reproduce the validated local suite

```bash
python -m pip install -r requirements-demo.txt -r requirements-test.txt
python -m pytest -q
python scripts/run_hostile_static_suite.py
python scripts/run_international_gate.py
```

## Run the Control Center

```bash
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port 8000
```

Key routes:
- `/api/status`
- `/api/demo/build`
- `/api/live/build`
- `/api/international/readiness`
- `/api/benchmark/catalog`
- `/api/integrations`
- `/api/source/mobile/android`
- `/api/source/mobile/ios`
- `/api/source/game/godot|unity|unreal`
- `/api/projects/{project}/history`
- `/api/projects/{project}/versions/{version}/download`
- `/_omni/metrics`

## Important truth boundary

This package contains working code and locally validated flows, but this validation host does not have the live GPU model, Docker daemon, PostgreSQL, Redis or S3 services. Those live gates are intentionally skipped/fail-closed rather than simulated as success. Signed mobile binaries are also not included.

Use `docker-compose.international.yml` for staging experimentation. For production, use a dedicated sandbox runner and the canonical `docker-compose.production.yml`; do not expose a public API container with a host Docker socket.

## M4.95 capability-provider foundation

M4.95 adds a provider-neutral capability layer. Canonical capability, skill, agent, provider-definition and cost truth is generated/checked with:

```bash
python -m omni_prod.truth_lock --write
python -m omni_prod.truth_lock --check
```

Provider integrations must register behind `CapabilityProvider`; canonical capability keys never contain vendor brands. A paid external adapter must provide both durable submit idempotency and durable result retrieval by `provider_task_id` so a worker/process restart cannot create duplicate spend or lose a completed result. The compatibility `HTTPMediaCapabilityProvider` and `LLMCapabilityProvider` keep synchronous results in process memory and therefore are not valid paid crash-resumable commercial adapters.

Provider credentials are passed only by secret reference through `CredentialBinding` (`PLATFORM_MANAGED`, `CUSTOMER_CONNECTED`, `BYOK`). Raw secret values must not be persisted in capability rows, artifacts, logs, exports or readiness APIs. M4.95 implements the binding abstraction; full per-customer OAuth/BYOK onboarding remains a later integration milestone.

Large provider artifacts may use file-backed `ProviderArtifactPayload` and an artifact store `put_file`/streaming path. Do not convert large GLB/video/audio payloads into one in-memory byte buffer merely to hash or store them.

Commercial provider price catalogs remain `NOT_CONFIGURED` until real supplier pricing/contracts are entered and versioned. `UNKNOWN_NOT_APPROVED` is never treated as zero, and an estimate/reservation is never recorded as provider-reported actual cost.
