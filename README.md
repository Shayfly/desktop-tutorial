# 148AI V28 — Vercel Launch Candidate

Deployment repository for the current **148AI V28** online review environment.

## What this deployment contains
- Real V28 Python/FastAPI runtime packaged in `omni_prod_runtime.zip`
- Customer-facing 148AI workspace UI
- Account registration and sign-in
- Private projects
- Deterministic/local V28 build path
- Versions/history
- Rights & IP gate
- Preview promotion
- ZIP export
- Integrations and Company OS diagnostics
- Fail-safe Vercel bootstrap and health diagnostics
- GitHub Actions verification gate

## Deployment architecture
Vercel runs `app.py`. The bootstrap validates and lazy-loads the packaged V28 runtime, serves the customer UI at `/`, and passes API/assets/preview/runtime traffic to the V28 FastAPI application.

Health endpoints:
- `/_148ai/health`
- `/_148ai/diagnostic`

## Current production gates
This is a **launch candidate**, not a claim of completed public production infrastructure. The current Vercel review uses memory persistence unless configured otherwise. Persistent PostgreSQL, Redis workers, object storage, real GPU/open-weight model serving, remote sandbox, live media engines, Stripe live billing, transactional email, production domain/DNS/TLS, store signing and full operational monitoring remain separate live-infrastructure gates.

## Verification
The repository CI checks:
- runtime ZIP integrity and required modules
- Python compilation
- browser JavaScript syntax
- customer UI smoke
- V28 runtime import
- `/api/status` runtime API smoke

Canonical full reviewed source remains the archived **148AI V28 Launch Candidate** release package; this repository is the deployment layer.

<!-- GitHub App write-access verification: 2026-10-19 -->
