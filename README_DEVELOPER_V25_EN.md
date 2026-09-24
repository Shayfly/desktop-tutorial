# Omni Creator V25 — Developer Handoff

V25 is the current source of truth. It retains the V11–V24 production/international stack and adds a unified behavior path reproducing the capabilities documented in the historical V10 validation.

## Verify
```bash
python -m pip install -r requirements-demo.txt -r requirements-test.txt
python -m pytest -q
python scripts/run_v25_release_gate.py
```

## Run
```bash
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000`.

## Unified HTTP flow
- `POST /api/v25/build`
- `POST /api/v25/projects/{project_id}/patch`
- `POST /api/v25/projects/{project_id}/promote`
- `GET /api/v25/projects/{project_id}/export`
- hosted app: `/hosted/v25/{deployment_id}`
- generated app auth/data: `/runtime/v25/{deployment_id}/...`
- authenticated websocket: `/runtime/v25/{deployment_id}/ws?token=...`

## Important truth boundary
The legacy V10 ZIP metadata and validation are visible in the user's Library, but raw-byte materialization of that old Project file is blocked. Therefore V25 does not claim a line-for-line source merge. It implements V10's documented behavioral contract and enforces it through parity tests.

Live GPU model, Docker hostile execution, live PostgreSQL/Redis/S3, signed mobile binaries and console certification remain environment/credential-dependent gates.
