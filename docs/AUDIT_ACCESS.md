# Audit access — where everything is (for independent review)

No secrets, keys or customer data are in this file or in the linked runs.

## Repository and branches
- Repository (private): https://github.com/Shayfly/desktop-tutorial
- **Active branch: `milestone/pre-staging-2026-10-05`** — https://github.com/Shayfly/desktop-tutorial/tree/milestone/pre-staging-2026-10-05
- The GitHub *default* branch is still `main` (last commit `e8f2949`, 2026-09-22). `main` is old and is neither the work base nor a merge target. A reviewer who opens the repository without choosing a branch sees September; select the active branch (or the owner may switch the default branch in the repository settings).
- Claude's task branch: `claude/g0-baseline-2026-10-09` (fast-forward merged into the active branch after CI).

## What runs where
- Build worker host (Oracle, self-hosted GitHub runner): worker, sandbox runner (no network), preview worker/router, Caddy. Deployed by workflow `Deploy build worker` on every push to the active branch that touches `omni_prod/**` or `infra/worker-host/**`. Previews: `https://prv-<id>.151-145-89-132.sslip.io` (private by default).
- Vercel project `148aiv28` (web UI + API), deployed from the active branch; protected by Vercel Authentication.
- State: Neon PostgreSQL (migrations `infra/postgres/*.sql`, applied by the deploy), Upstash Redis (queue), Cloudflare R2 (artifacts, build-round snapshots, backups).

## Truth documents (active branch)
- `STATUS.md` — newest section first; four categories (verified / awaiting live verification / blocked / not implemented).
- `AGENT_OS_REGISTRY.json`, `docs/AGENT_OS_REGISTRY.md` — 52 agents, 427 skills; status computed by `python -m omni_prod.agent_os.audit --write` from code + configuration + fresh evidence; CI fails on inflation.
- `PLATFORM_CAPABILITY_MATRIX.json`, `PLATFORM_REGRESSION_MATRIX.json`, `GOLDEN_E2E_MATRIX.json`, `FAILURE_INJECTION_MATRIX.json`.
- `omni_prod/agent_os/evidence.py` — every LIVE claim's run id, commit and exactly what it asserted; `omni_prod/registry_evidence_lock.json` — file digests per evidence commit (a code change makes the evidence stale automatically).

## Evidence runs (GitHub Actions; results are in each run's Annotations)
- Free real-server checks: workflow `Post-deploy checks`, stage `free` (latest: run 37966155212).
- Golden SaaS build (paid): run 37961193099. Crash recovery: run 37954236866 (+ inspect 37955419872).
- Backup/restore: workflow `Backup and restore test`, run 37962179844.
- Spend audit: stage `spend-audit`, run 37966168410.
- Gate replay over all stored versions: stage `gate-replay`, run 38071513038. Re-verification of stored versions through the production chain: stage `verify-replay`, run 38072167057.
- CI: workflows `v24-ci` (tests + regression guardian + capability auditor), `V11 Overlay CI`, `Neon bootstrap CI`.

## Reproducing locally
`python -m pytest -q` (needs Python 3.12 and `requirements-production.txt` + `requirements-test.txt`); `python -m omni_prod.agent_os.audit` (no write) prints the computed counts and any inflation.
