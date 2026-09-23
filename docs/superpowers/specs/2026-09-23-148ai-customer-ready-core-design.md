# 148AI Customer-Ready Core — Design Spec

**Status:** approved direction
**Branch:** `repair/investor-demo-alpha`

## Goal
Turn the current V28 web shell into a customer-usable pilot that proves the 148AI core works online end-to-end.

## Definition of Done
A new user can:
1. Register or sign in.
2. Refresh or hit another serverless instance without losing authentication.
3. Enter a natural-language prompt without creating a project first or choosing Web/Mobile/Game/etc.
4. Have 148AI create/select the project and infer the product shape automatically.
5. See visible build stages: planning, generation, running, testing, repairing, ready/failed.
6. Have the generated product actually executed in an isolated runtime before it can be marked ready.
7. Open a working interactive preview of the generated product.
8. Request a natural-language change to the same project.
9. Receive a new immutable version.
10. View version history and restore a prior version.
11. Export the selected version while authenticated.
12. Sign out, sign back in, and see the same projects and versions.
13. Switch to Hebrew and receive real translated UI with RTL, not only a dir/lang change.
14. Pass an automated integration/E2E acceptance flow against the deployed environment.

A green unit-test count alone is not sufficient for completion.

## Current model policy
This milestone does **not** require connection to a live external AI model. The immediate goal is to prove the full 148AI product workflow using the current local/deterministic generation capabilities.

Real model providers and model routing are a later milestone, after the customer-ready core is demonstrably working. The architecture implemented now must not block adding those providers later.

## Verified current problems
- `app.py` defaults `OMNI_CREATOR_PERSISTENCE` to `memory`, which is not reliable as the source of truth on serverless infrastructure.
- Build currently requires a manually created/selected project.
- Product-type chips are primary UI even though the current build payload does not use them.
- The locale selector only changes `lang`/`dir`; it does not translate visible copy.
- Export uses browser navigation instead of an authenticated fetch.
- The main runtime is packaged inside `omni_prod_runtime.zip`, so offline capability claims must be re-proven through the deployed customer flow.
- Live usage showed registration succeeding followed by protected requests returning 401, requiring root-cause verification of durable auth/session state.

## Architecture
Use a hybrid salvage approach: keep the useful V28 capabilities that can be proven live, but replace the weak live shell around them.

Keep:
- 148AI brand and visual direction.
- working runtime capabilities and sound API contracts.
- project/version/build concepts where they can use durable shared state.

Replace or rework:
- process-memory account/project/session state.
- manual project-first UX.
- mandatory product-type selection.
- fake/incomplete locale switching.
- unauthenticated export navigation.
- success states that do not prove preview usability.
- any build path that can mark a project ready without executing and validating the generated output.

Do not block this milestone on live external AI models, music/video/3D engines, signed app-store binaries, enterprise billing, or large-scale GPU/model infrastructure.

## Persistence and auth
Production must use a durable shared database for users, sessions, projects, versions, builds and deployment metadata. PostgreSQL-compatible storage is preferred because the repository already includes `psycopg`.

Production must fail closed when durable persistence is required but unavailable. Memory mode may remain explicit for local tests only.

Required now:
- email/password registration and login
- durable session validation
- logout/session invalidation
- ownership checks on project/version/export/preview operations

OAuth providers, email verification and password reset are the next auth milestone and must not block the first customer-ready core.

## Prompt-first product flow
The main screen centers on one prompt: “What do you want to build?”

Build flow:
1. Validate prompt.
2. Auto-create a project when no project is active.
3. Infer product category/platform/capabilities.
4. Create normalized Product Spec + Acceptance Contract.
5. Generate the project using the currently available local/deterministic generation path.
6. Materialize the generated files into an isolated execution workspace.
7. Start/run the generated product with bounded time and resources.
8. Execute validation/tests against the running/generated result.
9. Detect failures and run the existing repair path where supported.
10. Re-run after repair.
11. Persist every build stage and terminal state.
12. Only after successful execution and validation expose Preview, Improve, Versions, Restore, Export and supported Deploy actions.

Technical selectors move to Advanced and become optional overrides only if they actually affect build configuration.

## Real execution and isolation
A generated project is not considered successful merely because files were produced.

For this milestone, 148AI must execute the generated output in an isolated runtime appropriate to the generated project type. The first supported customer path may be limited to the project types the current runtime can execute reliably, but that limitation must be explicit rather than simulated.

The execution layer must:
- use a per-build temporary workspace
- enforce a hard timeout
- limit child-process execution to an allowlisted runner path
- capture stdout/stderr and exit status
- avoid exposing 148AI auth tokens, database credentials or unrelated environment secrets to generated code
- persist a concise execution result linked to the build/version
- fail the build when execution or required validation fails

A Preview may only point at output from a build that reached the required successful execution state.

## Build timeline and failure recovery
The customer must always be able to tell what 148AI is doing.

Canonical visible stages:
`Planning → Generating → Running → Testing → Repairing → Ready`

A build can also enter `Failed` with a concise customer-safe error summary.

Requirements:
- the current stage is persisted, not only held in browser memory
- page refresh does not erase the known build state
- terminal `Ready` and `Failed` states are explicit
- a failed build must never be presented as ready
- retry starts from the existing project context and records a new build attempt
- where the repair loop is available, repair attempts are visible in the timeline
- raw secrets, internal stack traces and credentials are not exposed to customers

## Preview and changes
Preview must be an interactive generated product, not a JSON dump. A successful build maps to a specific version and preview target.

A follow-up prompt modifies the same project, produces a new version, runs the same execution/validation/repair loop, and leaves previous versions restorable.

## Versions, restore, export
- Versions are immutable snapshots.
- Active version is explicit.
- Restore never destroys history.
- Export uses authenticated fetch/blob download and is tied to a specific version.
- Preview/export default to the active version unless another version is deliberately selected.

## Localization
English and Hebrew must be complete for the primary customer flow before claiming them ready. Hebrew must use correct RTL. Locale choice must persist across reloads. Missing keys fall back predictably.

The historical 20-locale target remains, but no locale is called ready until its visible strings and layout are verified.

## UX
Logged-out: brand, concise promise, auth, language selector.

Logged-in: large natural-language prompt, recent projects secondary, Build as primary action, no mandatory technical choices.

Build in progress: visible persisted stage state and clear failure/retry handling.

Build complete: Preview, Improve, Versions, Export, supported Deploy.

Rights/IP, Integrations and Company OS remain Advanced controls.

## Observability and security
Add structured logs for auth, project creation, build start/stage/completion/failure, execution result, preview, restore and export. Include correlation/build IDs, never secrets.

Every project/version/preview/export action validates ownership. Generated previews and execution workspaces must not receive 148AI credentials. Production must not silently fall back to memory persistence.

## Testing
Required tests include:
- production persistence fails closed without durable config
- separate app instances share durable session/project state
- cross-user project access is rejected
- prompt-first build auto-creates a project
- generated output is actually executed before a build can become ready
- an execution failure produces a persisted failed state
- a successful execution records the expected stage progression
- retry/repair creates a new build attempt without deleting project history
- build failures are visible and not reported as ready
- authenticated export succeeds and unauthenticated export fails
- restore preserves history
- English/Hebrew translation key coverage and Hebrew RTL

Integration acceptance:
register/login → prompt → auto-project → generate → run → test/repair if needed → ready → preview metadata → change → new version → restore → export → sign out/in → same state.

The deployed browser flow must pass before promotion.

## Deployment
Implement on `repair/investor-demo-alpha` using small test-backed commits. Deploy a preview environment before production when Vercel access is available. Do not call the milestone complete until the deployed E2E path passes.

## Next milestone after the core
After this customer-ready core is stable: production migrations/DB operations, Redis workers/queues, artifact object storage, real model providers and routing/failover, stronger production-grade sandboxing, billing/credits, OAuth/email lifecycle, monitoring/backups, creative media engines, signed mobile pipelines and store integrations.
