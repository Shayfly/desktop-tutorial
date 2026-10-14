# 148AI Master Specification

**Snapshot:** 2026-10-14  
**Baseline:** PR #30 source head `b5f0625`, stacked on PR #28 source head `e364151`; this document describes repository evidence, not a live-product certification.  
**Authority:** `AGENTS.md`, `PRODUCT_MISSION_AND_ACCEPTANCE.md`, `docs/OPERATING_CONTRACT_HE.md`, and `STATUS.md` govern this snapshot. `STATUS.md` wins whenever a capability claim differs.

## Founder-declared product intent

**Founder-declared product goal:** build 148AI as a Hebrew-first commercial AI product-creation platform. This records product intent only; it is not independently verified legal title, ownership, incorporation, or trademark status. No personal identity numbers or legal records belong in this repository.

## Product outcome

148AI is intended to take an authenticated customer's request, clarify and preserve requirements, present a validated plan and price for customer approval, build a real web product, verify and repair it within bounded policy, and deliver it through a private preview with durable versions and export. Web/SaaS is the initial product path. Other product families in vision documents are scope declarations, not current launch capabilities.

## Current architecture and data flow

```text
Browser (Hebrew-first workspace)
  -> FastAPI control plane on Vercel
     -> authenticated account/project ownership check
     -> PostgreSQL: creator/project state, conversation, immutable brief revisions,
        architect plans, budget reservations and execution evidence
     -> Redis/RQ: reserved intake and build/preview work
        -> private worker host
           -> routed provider gateway (provider credentials stay on the worker)
           -> isolated sandbox runner for generated code/builds
           -> durable object storage for artifacts
```

This is the repository's intended/implemented topology, not proof that every named service is live or correctly isolated in Preview or Production.

### Conversational AI path

1. `omni_prod/assets/app.js` posts customer messages to `POST /api/v28/projects/{project_id}/conversation`.
2. `omni_prod/investor_app.py` authenticates project ownership, rejects stale brief revisions, and delegates to `ConversationSupervisor`.
3. Intent and complexity routing are deterministic. Greetings and non-requirement intents do not spend on a model. Eligible standard or escalated requirement turns may use `ReservedWorkerInterpreter`; a direct provider call from the API host is prohibited.
4. The API constructs a bounded, Hebrew-first contextual prompt, prices a single call, and creates an idempotent durable reservation before enqueueing the `omni-intake` job. The worker holds provider keys and calls the routed gateway.
5. The response is validated as structured data. Requirement evidence must occur in the current customer message; invalid or fabricated proposals are dropped. Deterministic high-confidence statements win conflicts. Model decisions never approve a build or execute a tool.
6. Customer and assistant messages are recorded with brief revision, interpreter, reservation and cost state. The brief is saved as a compare-and-set revision; model context is bounded and is not authoritative state.
7. The customer reviews the summary and plan. A separate, authenticated approval is bound to the exact brief, contract and budget; chat text alone cannot start a build.

Migrations 036 and 037 define durable conversation and reservation storage. Durable Postgres execution is covered by tests that require a real database; this local run did not have one. `STATUS.md` records the current live verification gap.

### Architect, Agent OS, build, repair and preview

- **Architect:** `ChiefArchitect` turns the validated brief/contract into a feasibility assessment, plan and execution graph. Missing or unsupported capabilities remain visible blockers; planning is not evidence that execution succeeded.
- **Agent OS:** registered agents, skills, task classes, permissions and plan-bound task recording constrain execution. A registry entry is not proof that the agent or its dependency works live.
- **Build and repair:** durable work is dispatched to the external RQ worker. Model work is bounded by an authorized reservation and usage ledger. Repair is limited and driven by failed evidence, not claimed progress.
- **Preview:** generated code runs through the separate sandbox/preview infrastructure, not in a public Vercel request. The repository's worker Compose stack places the sandbox runner on a private network and gives that dedicated component the host Docker socket; the socket must never be mounted in a public Vercel Function or exposed publicly.
- **Persistence:** database, queue and object storage are external services in the configured architecture. Function-local files are not durable state. Real account isolation, migrations, queues, object storage, builds, preview and restore still require environment-specific evidence.

## Vercel constraints and deployment boundary

The repository configures `app.py` as a Vercel Function with `maxDuration: 60` seconds. Vercel's official [Function limits](https://vercel.com/docs/functions/limitations) documentation, checked 2026-10-14 (page updated 2026-08-24), lists 300 seconds as the default; Pro/Enterprise limits are 800 seconds maximum with an 1800-second extended maximum in Beta, subject to platform eligibility. The official [Python runtime](https://vercel.com/docs/functions/runtimes/python) documentation (updated 2026-08-12) supports ASGI/WSGI frameworks including FastAPI.

These limits do not justify running long builds or untrusted generated code in the web request. The selected repository path keeps chat bounded, queues durable work, and uses a separately hosted worker/sandbox. Actual Vercel plan, deployment, runtime behavior and service connectivity are not independently verified here. Never use Vercel's ephemeral filesystem as durable project, conversation, or build storage.

## Capability truth as of this snapshot

| Capability | Repository state | Evidence boundary |
|---|---|---|
| Hebrew-first customer chat and deterministic requirements flow | Implemented; locally regression-tested | No claim of authenticated staging use |
| Provider-backed intake | Implemented behind explicit flags, budget caps, durable reservations and worker routing | A real customer/model response is **BLOCKED / NOT VERIFIED**; see `STATUS.md` |
| Conversation and brief persistence | PostgreSQL repositories and migrations implemented | Local PostgreSQL absent; restart durability and tenant isolation not live-verified |
| Validated requirements and separate customer approval | Implemented; regression-tested | Staging approval transaction is not live-verified |
| Architect plans, feasibility and execution graphs | Implemented/tested | A plan is not a completed product build |
| Agent OS task controls and evidence | Implemented/tested | Live worker execution and recovery are not verified |
| Build, bounded repair and sandboxed preview | Partial repository path and tests exist | No current authenticated staging Golden E2E |
| Account, billing, external identity, public publishing | Adapters/contracts exist in places | Live service setup/verification remains partial or blocked as recorded in `STATUS.md` |
| Android/iOS, media, 3D and other non-web families | Product direction/catalog coverage varies | Not a verified launch capability; see `CURRENT_TRUTH_V28_HE.md` |

## Non-negotiable constraints and governance

1. Security, privacy, legal, tenant isolation and an authorized budget outrank model output, tools and defaults.
2. Keep **Desired**, **Observed** and **Verified** state separate. Configured, queued, provider-success, build-complete and preview-loaded are not equivalent to independently verified product acceptance.
3. Missing credentials, unavailable durable state, unknown price, exhausted caps, stale approvals, invalid model output, timeouts and uncertain provider outcomes fail closed and remain explicit. Never report a fake provider success or silently present deterministic fallback as model output.
4. Every paid call must be pre-priced, durably reserved, idempotent and reconciled. The intake worker uses one bounded provider call without automatic retry; unknown cost is not zero. Provider keys stay out of the browser, Vercel API environment, source, logs and documentation.
5. Model output is untrusted data. It cannot change policy, cost limits, acceptance criteria, confirmed requirements, approval state or execution state. Evidence is checked against the current message; material changes require explicit customer confirmation.
6. No generated-code execution in the public web function. Do not expose the worker Docker socket. Keep durable data outside function-local storage.
7. Do not make paid provider calls, change staging/production flags, bypass protected Preview authentication, deploy or merge without the required authorization and acceptance evidence.
8. Keep changes scoped to the first failing transition. Do not expand product-family claims or architecture before the current Golden E2E gate passes.

## Acceptance criteria

### First conversational slice: Customer Message -> Confirmation

The staging acceptance must use an authorized authenticated customer and prove, in one replayable evidence record:

- a nontrivial Hebrew and English requirement turn traverses the actual browser, API and worker route;
- the real provider is contacted once through an active, priced catalog route, with a durable reservation, provider request correlation and reconciled usage/cost under the approved hard caps;
- contextual response uses the current project brief and bounded prior conversation without treating history as new evidence;
- response schema and each applied requirement pass evidence/value validation; fabricated proposals are rejected;
- customer and assistant turns plus the resulting immutable brief revision survive a database restart and remain tenant-scoped;
- the UI identifies model-backed replies separately from deterministic fallback and messages that did not use a model;
- a complete, feasible plan requires a separate explicit customer confirmation bound to the exact revision/contract/quote; no build begins before that confirmation.

Stubbed providers, in-memory stores, configured secret names, deployment readiness, mocked browser routes and unit tests are useful regression evidence but do not pass this staging acceptance. Do not weaken the protected deployment gate to obtain a pass.

### Continue to Architect -> Agent OS -> Build -> Repair -> Preview

After the conversational slice passes in staging, extend the same evidence chain: bound approval -> durable build admission and reservation -> plan-bound agent tasks -> real multi-file output -> dependency/build/test results -> bounded repair or evidence that repair was unnecessary -> isolated private preview -> durable project version, browser check and source export. Verify retry/recovery, tenant isolation, secret redaction, actual cost settlement and rollback. No stage may claim success without its own verified evidence.

### Public-launch gates

Before claiming a working staging product or public production service, also meet the objective auth, second-user isolation, persistent history, multi-prompt build/preview/export, repair, billing/entitlements, spend reconciliation, backup restore, rollback and security acceptance in `PRODUCT_MISSION_AND_ACCEPTANCE.md`. Mark unmet requirements individually as blocked or not implemented.

## Roadmap and stop/go gates

| Order | Milestone | Go condition |
|---|---|---|
| 1 | Authorize and verify the real conversational intake path in Preview | Valid protected-Preview access, worker switch/queue and database ready, usable provider credential and approved caps; complete the criteria above without bypassing authentication |
| 2 | Prove validated brief -> Architect plan -> explicit approval -> Agent OS execution record | Same authenticated project/revision; persisted, replayable plan and permission/ownership evidence |
| 3 | Prove one bounded real build and a real failure/repair path | Durable admission/reservation/attempt ledger, isolated worker, actual model usage and passing objective checks |
| 4 | Prove private Preview, durable version, modify/repair, recovery and export | Isolated generated-code execution, real browser evidence, durable artifacts and recovery after worker/runtime restart |
| 5 | Complete identity, tenant-isolation, commercial and operational launch gates | External OAuth/billing/provider/domain setup and independent deployed verification; no production claim before all required gates pass |
| 6 | Expand supported product families | A complete, costed, isolated Golden E2E per family; registry presence alone is not a go condition |

## Current milestone evidence and blockers

At source head `b5f0625`, verifier run [38488792854](https://github.com/Shayfly/desktop-tutorial/actions/runs/38488792854) stopped at protected Preview authentication (HTTP 401). After an authorized Vercel automation bypass secret was configured, verifier run [38517442457](https://github.com/Shayfly/desktop-tutorial/actions/runs/38517442457) reached Preview and passed deployment identity plus synthetic API/authentication checks, but failed `schema_compatible`: the API reports migrations 1–38 absent, including required `038_conversation_attachments`. The verifier makes no provider call or build. No real provider-backed customer conversation, verified durable persistence, requirements/quote approval, or build has been observed. Since Preview branches share the database and the documented migration route drains/replaces worker services, do not apply migrations or deploy a worker without explicit operational approval.

This Windows worktree has no Postgres URL, Redis URL, provider API key, intake activation flags or Docker runtime. Vercel automatically created PR Preview deployments; no worker deployment or paid provider call was made. The exact runnable local results and external dependencies are kept in `STATUS.md`.

### Isolated Staging authorization and boundary

The founder reports an existing Neon project/branch (`148ai-db` / `preview-isolated-2026-10-12`) and Upstash database (`148ai-preview-isolated`, Frankfurt/Free). These identifiers are founder-provided, not independently verified; Neon branch parent/data lineage and both provider resource IDs versus Production remain unconfirmed. `infra/staging/README_HE.md` and `infra/staging/.env.example` prepare a local-only setup boundary. Read-only GitHub metadata shows no `Staging` environment, no Actions Variables, and no Staging/Neon/Upstash-named secrets. Vercel settings were not accessible from this worktree.

On 2026-10-14 the founder authorized planning, code preparation, and tests that do not modify existing infrastructure for a new isolated Staging environment. No database, Redis, worker, Vercel environment, secret, or billing resource has been created or changed. The existing worker-host example and backup/deploy workflows target the current shared Preview/Production services and must not be reused for the new environment. `omni_prod.isolation_check` now compares a labeled Staging env file against both existing targets and treats a different logical database or Redis database number on the same endpoint as SHARED. Different hostnames are necessary but not sufficient proof: the managed-resource identities must also be confirmed in the provider consoles. Migrations remain blocked until isolated Postgres and Redis resources, a dedicated worker path, and a fresh restore-verified backup of the exact Staging target are independently confirmed.
