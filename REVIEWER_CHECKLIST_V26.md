# V26 Reviewer Checklist

1. Run `python -m pytest -q`; confirm no failures.
2. Run `python scripts/run_v26_release_gate.py`.
3. Start Uvicorn and use the browser UI: register → create project → build → history.
4. Register a second account and verify it cannot access the first account's project.
5. Inspect `account_tenant.py`, `v26_platform.py`, `universal_brain.py`, `media_pipeline.py`, `media_gateway.py`.
6. Verify live build fails closed without `OMNI_ENABLE_LIVE_BUILD=1`.
7. Configure a local OpenAI-compatible model + sandbox and run `/api/v26/projects/{id}/live-build`.
8. Configure a self-hosted media service implementing `POST /v1/assets/generate`; test image/audio asset materialization.
9. Run live Postgres/Redis/S3/Docker integration suite.
10. Review the explicit production blockers in `CURRENT_TRUTH_V26_HE.md`; do not treat skipped gates as PASS.
