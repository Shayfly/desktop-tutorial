# 148AI: product mission and acceptance contract

## Objective and current baseline

Create a commercial, polished, Hebrew-first AI product builder for individuals and teams. A user describes a web app, site, or simple game, then receives an editable, running project with real code and a shareable preview. The release must offer a dependable web-app path before claiming broad native, 3D, film, or music creation. Preserve working V28 capabilities where they are useful; remove fake affordances and misleading labels. This document is a task specification, not evidence that these features already exist.

The founder wants the customer experience to feel like a mature software company: fast onboarding, comprehensible progress, high quality output, recoverable errors, clear prices, accessible support, a trustworthy account, and smooth mobile/desktop usage. Public copy must match verified functionality.

## Required customer journeys

1. **Marketing and onboarding:** polished responsive landing page, examples that correspond to real projects, clear capabilities/pricing, terms/privacy, support, Hebrew RTL and English LTR. Onboard a new user into a private workspace with a useful first project. Avoid claims such as "Build Anything" without clear scope disclosure.
2. **Identity:** working registration and login via Google, Apple, and email; session management, verified email, account linking and safe recovery, logout, account deletion/data export. Use a reputable hosted identity platform or properly audited implementation. Configure separate dev/preview/production redirect URLs and verify both Google and Apple callbacks live. Keep provider secrets out of code. If Apple cannot be activated without the founder's developer account, ship the UI in an honest disabled state and name the precise setup step.
3. **Projects:** create/list/search/rename/archive/delete; tenant-scoped persistent data; autosave; versions and restore; file viewer/editor with clear conflicts; actionable onboarding and project settings. Prove cross-user isolation through requests using two real test accounts.
4. **Generation:** user request -> scoped plan -> real model invocation -> source files -> dependency install/build -> tests and automated repair with limited retries -> visible file diff -> functioning preview -> version history -> downloadable complete source. Use model routing with measured usage, configurable caps, retries, cancellation, idempotency, and transparent failure. The platform must not silently fall back to deterministic sample output while labeling the result AI generated.
5. **Preview and publishing:** preview generated code inside an isolated, resource-limited environment with per-project URLs and expiration controls. An owner can reproduce a build, inspect logs, and export source. Support one verified deployment path for generated web apps, with an explicit distinction between preview and production publishing. Respect existing rights/security gates.
6. **Commercial controls:** actual subscription checkout and signed webhooks where credentials are supplied; plan entitlements enforced on the server; quotas and hard spend ceilings; accurate per-user/provider/model costs; clear cancellation, upgrades, billing history, and failed-payment behavior. Free tier must have a sustainable fixed limit. Avoid fictional gross-margin promises.
7. **Operations:** structured logs/tracing, error monitoring, admin access controls, abuse/rate limiting, queue visibility, incident signals, backups and restore exercise, vulnerability review, dependency pinning, migrations, staging versus production, CI checks, and rollback. Add a support workflow with user-visible error reference IDs.

## Architecture constraint: Vercel and execution

Deploy the public web app to Vercel. Use Vercel Functions only where their current runtime and duration limits fit; place durable database, object storage, queues, build workers and untrusted generated-code execution in services that are appropriate and explicitly configured. Evaluate a managed isolated sandbox versus dedicated workers; document the choice and measured cost. Do not run generated code in the main web server or rely on its local filesystem for durable artifacts. The existing Python/FastAPI code can be kept behind an API/service if it is fit for purpose; migration to a Vercel-friendly frontend is allowed if justified and actually completed, with code and tests.

## Sequencing and honest deliverables

Implement a vertical slice before broadening claims: Google/email sign-in (and Apple once provider credentials exist), persistent account, user prompt, one real generated web app, safe preview, edit/repair, export, and one verified Vercel preview deployment. Then finish billing, reliability, admin, localization, further product types and live provider integrations. This order controls risk; it does not authorize leaving an incomplete vertical slice portrayed as launch-ready.

Maintain `STATUS.md` and `COST_MODEL.md` with observed provider usage and test scenarios, including a heavy user; calculate unit economics using actual prices and workload data. Never assume unlimited free actions. Require configuration examples without credentials, a clean bootstrap command, migrations, Vercel/project setup, and external service setup instructions.

## Release acceptance: objective proof required

- A first-time user can reach a live Vercel preview URL, register with Google, register with Apple after configured, and use verified email login. A second user cannot access the first user's projects or artifacts.
- On the deployed stack, at least three different nontrivial prompts each produce a real repository, a passing build, a working isolated preview, saved project/version history and a downloadable ZIP. A deliberately broken generation runs a repair attempt and reports the real outcome.
- The generated project has meaningful frontend and server/data behavior where requested; no canned single-page HTML is counted as a successful arbitrary app.
- Provider calls, credit deductions and estimated actual costs can be reconciled for each build; a budget-exhausted user cannot trigger billable generation. Payment entitlement changes require verified server-side events.
- CI passes on a clean checkout; tests cover auth/tenant access, generation failure/retry, sandbox limits, subscription authorization and export. A deployed browser E2E test records the actual URL, environment, timestamp, and result.
- Backups are restored into a separate environment, secrets never appear in logs or exports, generated-code execution is isolated, and a rollback procedure is exercised before public traffic.
- Explicitly list anything that requires founder-owned OAuth, Apple developer account, payment account, AI provider, domain or production environment access. Provide setup links/instructions and verify once supplied; do not fake completed integrations.

## Final report format

Provide: current public preview URL; commit/revision; exact setup and test commands; evidence per acceptance criterion; costs measured for the test workloads; remaining blockers by owner; and a candid conclusion: local demo, working staging product, or verified public production service. If an acceptance criterion fails, it must appear as incomplete with the failing evidence and next concrete fix.


## M4.95 universal creation scope truth

148AI's long-term Creation OS scope includes Web/SaaS, Backend/API, Database, Android, iOS, Desktop, generated AI Agent products, Automation products, 2D/3D games, Multiplayer, images, textures, 3D meshes/scenes, rigging/animation, audio/SFX, Voice/TTS/STT, Music, Video/Film and integration-driven products. These are canonical scope families, not launch claims.

Current status must use only `LIVE`, `PARTIAL`, `NOT_CONFIGURED`, `NOT_IMPLEMENTED`, or `BLOCKED`. M4.95 is primarily a capability/provider/cost/evidence foundation. Web/SaaS has the strongest existing implementation but remains `PARTIAL` until a public production vertical slice is independently verified. Commercial media/3D providers are `NOT_CONFIGURED`; multiplayer, complete generated Agent/Automation targets, and several ecosystem capabilities remain `NOT_IMPLEMENTED`. Source presence, an enum, a plan, or an API key alone is never sufficient to mark a capability `LIVE`.
