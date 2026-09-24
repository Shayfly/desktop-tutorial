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
