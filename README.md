# 148AI — Customer-Ready Core

Deployment repository for the current 148AI customer workflow.

## Customer flow

The primary product path is now:

`Sign up / Sign in → Prompt → Auto-create project → Generate → Validate → Run/Test → Repair when supported → Ready → Preview → Improve → Versions/Restore → Export`

The customer does not need to choose Web/Mobile/Game/SaaS before building. The deterministic/local generator is used for this milestone; live external AI models are intentionally deferred until the product flow is proven end to end.

## Architecture

Vercel runs `app.py`.

- `/` and `/ui/*` serve the customer-facing prompt-first workspace.
- `/api/live/*` is the durable customer state layer for accounts, sessions, projects, builds, build events, versions, preview and export.
- `/preview/live/*` serves validated generated static/web artifacts through high-entropy preview handles.
- Legacy V28 runtime routes remain behind the final catch-all for deterministic generation and advanced compatibility.
- `omni_prod_runtime.zip` remains the deterministic generation engine for this milestone.

The customer state source of truth is never allowed to silently use process memory in production.

## Required production environment

Set:

- `OMNI_ENV=production`
- `DATABASE_URL=<PostgreSQL connection URL>`

If `OMNI_ENV=production` is set without `DATABASE_URL`, `/api/live/*` fails closed with HTTP 503 and a configuration error. Health endpoints remain available for diagnosis.

Local development may omit `DATABASE_URL`; in that case `MemoryStore` is used only for local/test execution.

## Current execution boundary

The first customer-ready execution target is deterministic static/web output.

Before a build becomes `ready`, 148AI:

1. validates ZIP integrity and size,
2. rejects absolute paths, traversal and symlink entries,
3. requires a usable `index.html` entry point,
4. applies only narrow deterministic repairs where safe,
5. extracts to a bounded temporary directory,
6. validates generated JavaScript with `node --check` when JavaScript is present,
7. persists the artifact/version only after validation succeeds.

Current pilot artifact cap: **5 MiB** stored in PostgreSQL `BYTEA`. Object storage is a later infrastructure milestone.

## Build timeline

Persisted customer-visible stages are:

- `planning`
- `generating`
- `running`
- `testing`
- `repairing` when required
- `ready`
- `failed`

A failed artifact is never promoted as the active project version.

## Languages

The primary customer workspace currently ships complete English and Hebrew copy for this core flow. Hebrew uses RTL. Additional locales remain a later QA milestone rather than being represented as complete before they are verified.

## Health and diagnostics

- `/_148ai/health`
- `/_148ai/diagnostic`

Health reports both deterministic runtime state and live-core persistence configuration.

## Verification

GitHub Actions verifies:

- the complete Python test suite,
- runtime ZIP integrity and required modules,
- Python compilation,
- browser JavaScript syntax,
- customer UI smoke,
- V28 runtime import and `/api/status`,
- live-core configuration/auth/ownership,
- prompt-first project creation,
- deterministic generation bridge,
- artifact safety/execution,
- persisted build timeline,
- secure preview/restore/export,
- English/Hebrew UI contract and RTL.

## Deferred infrastructure

Not represented as completed in this milestone:

- external AI model/router and GPU serving,
- Redis/worker orchestration for asynchronous long builds,
- object storage,
- OAuth providers and full email verification/reset lifecycle,
- image/audio/music/video engines,
- live Stripe billing and reconciliation,
- signed Android/iOS store publishing,
- production monitoring/backups at public scale.

Those layers are added after the current customer flow passes deployed end-to-end acceptance with durable PostgreSQL state.
