# 148AI — נספח הנדסי מחייב: שילוב ליבת Build–Test–Repair–Verify בלי לפגוע במערכת הקיימת

**תאריך:** 13.10.2026  
**סוג מסמך:** Technical Integration Specification + Execution Handoff + Acceptance Gates  
**סטטוס:** SPECIFIED / IMPLEMENTATION NOT CLAIMED. המסמך איננו שינוי Runtime, איננו הוכחת יכולת LIVE.  
**תוכנית אב:** docs/ENGINEERING_RECOVERY_T01_T09_2026-10-13.md (Issue #23, Draft PR #24).  
**נספח מוכנות לבנייה:** docs/PROTOTYPE_READINESS_AND_BLOCKER_DIAGNOSTICS_P0_HE_2026-10-13.md (Issue #26).  
**ענף קוד שנבדק:** fix/148ai-t01-ci-recovery-2026-10-13 @ 2353c60f9cfd23e35078ce1517244f15b7c97fad. הוא PR #25, ועדיין DRAFT.  
**ענף מסמכי הביצוע:** audit/148ai-engineering-recovery-t01-2026-10-13 (PR #24).  
**Production main:** לא לשנות. בכל יישום יש לקרוא HEAD מחדש, לסמן שינויים מאז נקודת הייחוס, ולא להעתיק פתרונות ישנים באופן עיוור.

## החלטת ה-Architecture Review

**לא להכניס את קובץ הדוגמה orchestrator_build_loop.py כמנוע FastAPI עצמאי נוסף.** זה ייצור מסלול ביצוע מתחרה למנוע ול-Worker הקיימים, עם ניתוק ממנגנוני אישור, billing, גרסאות, אבטחה ו-Preview. כן לאמץ את הרעיונות הטובים שבו **בתוך** החוזים של המערכת הקיימת:

1. קלט/פלט מובנה לסוכן תיקונים, באמצעות schema מאומת וגרסה.
2. תיקון ממוקד על בסיס אבחנת שגיאה וצילום מצב קוד קטן, ולא שליחת כל הפרויקט.
3. מספר ניסיונות תיקון ותקציב קשיחים, עם stop-loss ו-failure fingerprints.
4. Sandbox Backend שניתן להחלפה; E2B רק PoC מדיד, לא תלות מחייבת.
5. בנייה, בדיקות, תיקון חוזר ואימות **אמיתי** לפני READY.
6. Debuggability: ראיות, קבצים שהשתנו, סיבת חסימה, עלויות, ושקיפות לקוח/מנהל.
7. בידוד שירות ה-Preview מסביבת ה-Build, כדי ש-URL חי לא ימות עם יציאת בלוק הקשר.
8. המשך תהליך דרך Worker durable ו-Neon, לא await של בנייה ארוכה בתוך בקשת HTTP.

**אין להעתיק** import של google.genai או Anthropic/OpenAI ישירות לקוד הליבה; קריאות ספקים נשארות דרך Provider Router. **אין לקרוא** BackgroundTasks כמנגנון Durable Queue; השאירו Redis/RQ+Postgres Outbox. **אין** להכניס shell command חופשי או raw stdout עם סודות למסך משתמש.

## A. Gap Analysis של קוד הדוגמה שסופק

| נושא | יתרון לשמר | כשל במימוש שסופק | החלטת שילוב |
|---|---|---|---|
| Standalone core | טסטביליות ו-injection | FastAPI/E2B/SDK צמודים ללולאה | Core domain טהור עם Protocols; FastAPI משמש רק adapter |
| Structured output | תיקון צפוי | Pydantic מתאר fixed_code יחיד אך אין Provider call; ה-repairer זורק NotImplementedError | Parsed multi-file patch, schema version, strict validation/limits |
| Context optimization | חיסכון בטוקנים | בחירת קובץ לפי basename; fallback לקובץ האחרון; תלות רב-קובצית נשברת | error taxonomy + artifact/log parser + dependency hints; ask targeted repair or escalate UNKNOWN |
| Max retries | חסם על לולאה | 3 ניסיונות Build אבל תיקון אחרי כשל שלישי אינו נבדק | Initial build + עד 3 **repair rounds**, כל round כולל verify חדש; stop before unpaid/unauthorized call |
| E2B isolation | הפרדת קוד לא אמין | שימוש ב-async with Sandbox לא מבוסס; SDK sync/async עשוי להיות שונה לפי גרסה | Adapter/POC עם SDK pinned; ללא החלפת Sandbox הקיים לפני isolation/price proof |
| install/build | צעד קומפילציה | npm install ו-npm run build הינם strings חופשיים בלי allowlist או manifest | פרויקט Manifest מפוקח: argv arrays, pinned dependencies, timeouts, no shell injection |
| Preview | כוונה להחזיר URL | npm run dev נעשה ללא health; port=3000 מנוחש; חיי Sandbox מסתיימים עם ההחזרה | Existing Preview Runtime נפרד; health, access token, TTL, isolation ו-readiness |
| Durable state | API async | מצב בזיכרון, אין lease/heartbeat/checkpoint, HTTP מחכה לכל בנייה | RQ job + Postgres job/version/attempt + idempotency; enqueue-only endpoint |
| FinOps | חיסכון בשליחת מידע | אין Quote/Reserve/Meter/Settle, ספק hardcoded שאינו בהכרח כדאי | Gateway/router מול מסגרת ההרשאה הקיימת ו-cost-per-verified-build |
| Testing | loop | רק exit_code של build, ללא unit/browser/security/acceptance | Existing ProjectManifest + quality/security/rights + browser/preview verification |
| Error handling | לוג פשוט | except Exception מחזיר traceback/error string ללקוח, עשוי לדלוף סודות | Error codes מובנים, redacted logs, trace_id, retriable vs terminal |
| Security | סביבה מבודדת | mkdir עם interpolated path וכתיבת נתיבי קבצים ללא validation | normalize_repo_path + symlink escape protection + filesystem/size ceilings |

## B. מפת שימוש חוזר — מבוססת קריאת קבצים בענף PR #25 (לא הבטחת LIVE)

| תפקיד נדרש | רכיב קיים ב-148AI | פעולה מומלצת |
|---|---|---|
| Core build/repair | omni_prod/autonomous_core.py::AutonomousProductEngine.build | **REUSE**. יש כבר initial execution, up to max_repair_rounds, candidate dedup fingerprints, ranking/rollback and round_hook |
| Error decision | omni_prod/repair_loop.py::decide_after_failure; omni_prod/build_budget.py | **REUSE/EXTEND** classification ו-budget stop reasons. אל תיצור מונה ניסיונות נוסף בלתי מסונכרן |
| Controlled execution | omni_prod/sandbox_executor.py::SandboxRepositoryExecutor | **REUSE** ProjectManifest, real verification, anti-fake checks; העשר דו"חות artifacts |
| Sandbox isolation | omni_prod/sandbox.py::build_docker_command; run_sandbox | **REUSE** network none, read-only source, no-new-privileges, cap-drop, cgroups. חיזוק ובדיקות, לא הסרת guardrails לצורך npm install |
| Remote Sandbox | omni_prod/remote_sandbox.py::RemoteSandboxRepositoryExecutor | **ADAPT**. כיום HTTP/HMAC והעברת repository/argv; סביבת בנייה זקוקה לאי-דליפת secrets ולהגבלות payload |
| Remote endpoint | omni_prod/sandbox_service.py | **REUSE** authenticated limited execution; בדוק version parity, isolation ומניעת raw shell |
| File diff/patch | omni_prod/repository_patch.py::{parse_patch,normalize_repo_path,apply_patch} | **REUSE** lexical path validation, multi-file semantics and repository size/file ceilings; בדוק symlinks והקשרים נוספים |
| Durable queue/workflow | omni_prod/worker_tasks.py::{_run_live_build_job,execute_live_build_job}; omni_prod/build_outbox_relay.py | **REUSE** RQ/Postgres admission/idempotent claim, outbox, job/version persistence, capability gates, metering. לא לעקוף דרך HTTP endpoint חדש |
| Customer progress/cancel | omni_prod/build_control.py::BuildControl; BuildControl checkpoint/hooks | **REUSE** steps, cancellability, event visibility; כל stage חייב להיות traceable |
| Build statuses/leases | omni_prod/build_state.py; omni_prod/worker_lease.py | **RECONCILE** current state machine and durable DB transitions before extending statuses. No breaking schema evolution |
| Manifest/acceptance | omni_prod/project_manifest.py | **REUSE** machine-readable build/verify argv + mapping to acceptance IDs and preview contract |
| Preview lifetime | omni_prod/preview_runtime.py::DockerPreviewProvider; omni_prod/preview_router.py; omni_prod/preview_durability.py | **REUSE** separate preview isolation, health checks, TTL/access and durability; E2B preview optional only after POC |
| Provider/router | omni_prod/model_router.py; omni_prod/provider_router.py; omni_prod/model_gateway.py | **REUSE** existing quality/availability routing, accounting and provider error handling; enrich evidence and fallbacks only after audit |
| Authoritative verification | omni_prod/verification_contract.py; existing release gates in worker_tasks.py | **REUSE** fail-closed mandatory-check, checked artifact/hash/time TTL evidence |
| Required readiness UX | omni_prod/creator_plan.py; omni_prod/build_cost_plan.py; omni_prod/assets/app.js, app.css | **ADD** operator/customer readiness fields/codes from Issue #26; ensure build admission parity |

**Important:** Existing files constitute evidence of source implementation, not evidence of all these capabilities working live. Verify wired execution before claiming VERIFIED. Compare against PR #25 changes; this spec does not supersede them.

## C. Target architecture and boundaries

    FastAPI HTTP POST approvals/builds (authorized caller, approved scope, contract hash)
       -> cost quote + reserve + idempotent build_request/outbox transaction in Neon
       -> RQ / durable Worker (checkpoint, lease, heartbeat, retry policy)
       -> existing AutonomousProductEngine with injected components
           -> architect+generator+repairer via existing Model Gateway
           -> repository patches via repository_patch.py
           -> executor via existing isolated sandbox (potential E2B adapter later)
           -> ProjectManifest build + verify + acceptance + browser/quality gates
           -> round evidence, stop-loss and budget accounting
       -> verified artifact, version and generated app spec committed atomically
       -> PreviewProvider.start() separately (private route, TTL, health)
       -> UI progress + readiness + version + modification
       -> settlement reconciliation, failure-safe state and audit trail

### Boundary invariant B1 — Single authoritative execution path

- An HTTP handler never installs dependencies, launches E2B directly, runs long model calls or returns a BuildResult after waiting minutes. It authenticates, authorizes, stores and enqueues, then returns accepted job id and status.
- The Worker is the only component executing code-building DAG tasks. Keep existing resource ceilings and isolation.
- Keep existing build admission's capacity/quote/owner/contract/rights checks, including error codes; don't bypass because "prototype".
- Unit tests must verify no extra endpoint can call an independent engine or bill an account separately.

### Boundary invariant B2 — One frozen scope + one executable approval

- Approved PRD/BuildContract fingerprint, contract version, plan DAG, acceptance IDs and budget quote bind to build_id.
- A repaired artifact is accepted against **the same** approved acceptance criteria; do not silently relax tests.
- Updating plan/requirements invalidates stale approvals and previously quoted budget if scope changed.
- Scope feasibility and admission are separate; show exact reason for blocked pricing (Issue #26).

### Boundary invariant B3 — State and cost are immutable evidence, not volatile memory

- Source of truth Postgres (Neon): BuildJob/BuildAttempt/AgentTask/BuildArtifact/ProjectVersion + cost reservation and usage; Redis for transport and heartbeat, not sole business truth.
- Use idempotency key and optimistic version/fencing token on transition. Exactly-once provider effects are generally not guaranteed; record attempt/request id and settle real incurred costs on ambiguity. Avoid claiming that rerunning a task literally yields identical external responses.
- Never charge twice for a duplicate enqueue, duplicate approval or post-restart replay.
- Preserve partial verified artifacts and snapshots in durable storage, not solely E2B filesystem.

## D. Versioned contracts (proposal, not a claim they already exist)

**Goal:** small additive versioned interface; do not refactor stable code merely to change naming.

### D1. RepairFailure (internal)

    {
      "schema_version": 1,
      "build_id": "bld_...",
      "attempt_id": "att_...",
      "accepted_spec_fingerprint": "sha256:...",
      "repository_fingerprint": "sha256:...",
      "stage": "COMPILE|UNIT|ACCEPTANCE|BROWSER|QUALITY|SECURITY",
      "error_code": "COMPILE_ERROR",
      "exit_code": 1,
      "stdout_tail": "redacted and bounded",
      "stderr_tail": "redacted and bounded",
      "failing_acceptance_ids": ["A1"],
      "candidate_files": [{"path": "src/App.tsx", "reason": "stack frame", "confidence": "HIGH"}],
      "artifact_refs": ["evidence/log/opaque-id"]
    }

- Logs are redacted before persisting/sending to model; no arbitrary huge payloads. Egress and tokens have hard caps.
- A file inferred from the last entry of an unordered map is **not** acceptable evidence. If association ambiguous, use a bounded dependency graph/safe search then escalate or request more evidence, not arbitrary modification.
- Include both stdout and stderr: several frameworks output failures on stdout.

### D2. RepairPatch (model output, versioned and strictly parsed)

    {
      "schema_version": 1,
      "reason_code": "FIX_TYPESCRIPT_IMPORT",
      "base_repository_fingerprint": "sha256:...",
      "changes": [{"path": "src/App.tsx", "operation": "UPSERT", "content": "..."}],
      "repaired_acceptance_ids": ["A1"],
      "summary": "short, non-sensitive",
      "requires_dependency_change": false
    }

- The domain adapter translates changes to existing parse_patch()/FilePatch; never let model output control shell/executable commands.
- Support more than one file per repair. Validate base fingerprint, path count, content size, encoding, NUL/dotdot/symlinks, protected files and changed file authorization; verify no secrets are inserted.
- Pydantic/jsonschema validates structure **after** parsing; upstream Structured Output reduces but never replaces server validation.
- A repair may legitimately change manifest/config after separate explicit policy checks, but cannot silently reduce acceptance scope or remove tests.
- Hash every candidate; no-op/cycle candidates stop without spending another model call.

### D3. ExecutionEvidence (durable and redacted)

    { "schema_version": 1, "build_id": "bld_...", "round": 0,
      "source_sha": "40 hex", "sandbox_adapter": "docker|e2b",
      "workspace_digest": "sha256:...", "checks": [
        {"name":"compile","exit_code":0,"status":"PASS","log_ref":"..."},
        {"name":"acceptance:A1","exit_code":0,"status":"PASS","log_ref":"..."}
      ], "external_model_cost_usd": "0.0123",
      "artifact_digest": "sha256:...", "tested_at":"UTC timestamp" }

- Price strings in Decimal representation, never float arithmetic for billing.
- Outputs reference durable, access-controlled logs/artifacts (no public raw provider response).
- Report both total iterations and repair rounds, their different semantics, and terminal stop_reason.

### D4. Sandbox adapter contract

Provide smallest compatible Protocol/adapter without changing existing call sites first:

    submit_build(repository: RepositorySnapshot, manifest: ProjectManifest,
                 policy: SandboxPolicy, build_id: str) -> ExecutionReport
    get_evidence(run_id: str) -> ExecutionEvidence
    cleanup(run_id: str) -> CleanupReport

The current synchronous execute(repository, spec) remains the compatibility method. Optional async adapter must be invoked by Worker-owned wrapper (thread pool where needed); never block FastAPI event loop with synchronous SDK I/O. Version capability flags rather than pretending Docker/E2B support identical networking, streaming or previews.

### D5. Model Gateway adapter

    repair(spec, repo_summary, failures, limits, provider_policy) -> parsed RepairPatch

- Translate to existing repairer signature via compatibility wrapper rather than rewriting every caller.
- Model chosen by available, quality-approved provider and maximum spend, not hardcoded Claude 3.5 Sonnet. Any named model is example only and must be actively available/priced/commercially permitted before use.
- Provider request IDs, usage accounting, invalid structured output and fallback attempts retained; auth/quota/network errors have distinct reason codes and stop conditions.

## E. Loop semantics to implement/verify

**Exactly:** 1 initial candidate verified + up to MAX_REPAIR_ROUNDS=3 accepted repair *attempts* (up to 4 verification runs). Do not mix max build attempts with max repair rounds.

For each iteration:
1. Fresh (or resumed) immutable workspace snapshot & fingerprint.
2. Validate manifest, allowed commands, source paths and dependency policy.
3. Verify code via existing SandboxExecutor; record executable checks and outputs, stdout+stderr+exit code, acceptance coverage; no marker-only "pass".
4. On pass: run independent QA/security/rights and preview/browser/behavior gates (according to approved product contract); persist artifact, evidence and version only under existing release policy.
5. On failure: classify code error vs infrastructure/transient vs policy/cost blocker. Transient retry uses bounded backoff **only** where idempotency and rate/budget accounting allow; do not send a model repair for transient 429/network without evidence of code fault.
6. Select likely affected files using compiler location, traceback, import graph, previous changes and failure acceptance IDs; if ambiguous, mark diagnostic uncertainty and safely narrow scope.
7. Prepare bounded redacted prompt and invoke selected model through gateway under an already reserved cost budget. Validate structured RepairPatch.
8. Verify changed paths/scope, apply through repository_patch, enforce no-op/cycle detection and unchanged mandatory acceptance criteria.
9. Re-run required checks against the exact candidate, collect separate score; do not adopt regressed artifact (existing engine already supports best-candidate rollback).
10. On repeated failure/no progress/budget cap: terminal status FAILED/BLOCKED with readable reason, final best-safe artifact reference (not published as verified), operator diagnostics and retry plan. Settle real consumed spend; release unused reservation.

**No exceptions:** if final repair round occurs, verify it before status; if model fails, do not claim repaired; if preview cannot start, cannot return verified READY.

## F. Sandbox security and E2B PoC

### F1. Preserve Docker baseline

The existing Docker command uses --network none, --read-only, --cap-drop ALL, --security-opt no-new-privileges, restricted UID, memory/CPU/PID/FD ceilings and read-only source mount. These are not optional or cosmetic.

- Sandbox cannot mount host Docker socket, root, home or worker secrets; no provider API credentials inside generated product.
- Reject absolute and parent-traversal paths, symlink breakout, oversized repositories, accidental .env credentials, binary text substitution, unsafe manifest argv and arbitrary shell interpolation.
- No direct external network for compile/test sandbox. If dependency installation truly needs network, implement **separate** locked-down dependency fetch/build phase via approved registry allowlist, pinned package lockfiles, scoped network policy, cache/provenance and supply-chain scanning; this is a separate security design and gate, never "turn network on" globally.
- Preview sandbox has its own separate policy, not the build sandbox with the network restriction removed.
- Secret injection only through narrowly scoped, audited service proxies where absolutely necessary; no default host env inheritance.
- All artifact transfer runs through path normalization and per-account ownership checks; cleanup is auditable and resilient to crashes.

### F2. Optional E2B adapter, NOT automatic migration

Gate prerequisites before external spend:
- Confirm current official E2B Python SDK version and available sync vs async methods using official documentation and a pinned dependency; sandbox creation/commands/files, timeout behavior, lifecycle/keep-alive, private network controls, artifact and preview URL access must be verified. Do not assume async with Sandbox() is valid.
- Test POC in private staging with synthetic repositories and no customer secrets; verify network deny/egress controls, CPU/RAM caps or explicit alternative, artifact export, preview lifetime and deletion.
- Cost experiment: compare Docker vs E2B by price per **verified** representative build, including repair, bandwidth, startup latency, artifact storage and failed attempts. Keep billing reserves even for experiments.
- If any mandatory isolation/private-preview property is not supported/verified, E2B adapter status stays BLOCKED; do not change default Docker backend. No automatic Hetzner/Oracle host replacement.

## G. Preview correct-by-construction

- Keep existing omni_prod/preview_runtime.py + preview_router.py as independent lifecycle: start only for a version whose required verification gates passed (or keep rejected preview private/internal and explicitly unverified).
- Parse actual start argv, declared port and health_path from validated ProjectManifest/preview contract; never hardcode port 3000 or assume npm run dev.
- Probe real HTTP from outside/inside appropriate boundary; verify stable response, browser render and rights/security checks. Test 401 as privacy signal, not unconditional app failure.
- Persist preview mapping (version id, private token, expiry, container id, health, host/port) and associate with build_id; private by default, TTL with renewal and janitor.
- Return URL only when preview is actually RUNNING and externally health-checked as accessible to its authorized viewer. Frontend updates immediately to progress on accepted enqueue.
- Do not kill the preview server when exiting build sandbox scope. Model generated app data persistence separately from 148AI platform data.

## H. FinOps and provider error truth

- Keep existing quote->reserve->execute->meter->settle; support reconcile for uncertain provider calls. Do not mint fake credits or count QA ledger as provider balance.
- Staging founder QA verified previously active; recorded internal QA total cap is a **shared $10** unless separately configured and verified. This does not establish that every provider has $10 actual remaining. Provide per-provider UNKNOWN where not queryable.
- Budget fields include full-build worst-case ceiling (incl. repair rounds), per-call and per-provider caps, timeout, token maximum, scope; reserve before calls, stop gracefully at the last authorized amount.
- Provider on 429 can mean rate limit; exhausted provider balance requires explicit upstream evidence. Distinguish 402, 429, 401, timeout/5xx, structured-output mismatch and planned spend ceiling.
- Fallback must meet quality, commercial license, privacy and cost constraints; must not silently switch to a weaker/free model if acceptance quality suffers.
- Cost KPI: settled USD / verified usable artifact, with separate attempt failed spend and latency; no smoothing that hides actual spend.

## I. Integrate with founder/customer blocker visibility (Issue #26)

- A blocked build must explain where it failed: REQUEST/CONTRACT, PRICING, PROVIDER, CODE_GENERATION, DEPENDENCY_INSTALL, COMPILE, UNIT_TEST, BEHAVIOR/BROWSER, SECURITY, PREVIEW, SETTLEMENT or UNKNOWN.
- Customer sees plain Hebrew and a safe action; founder sees stage, code, requirement id, artifact hashes, exact config **names** only, source mapping (verified), trace IDs and check timestamps.
- Connect the existing cost_quote_unknown failure path to root cause from capability assignment, provider quote, actual required scope, and alternative contract requiring explicit re-approval; never replace "unknown quote" with price $0 simply to activate a button.
- Show active progress, number of repair rounds, safe last error and remaining authorized spend, without rendering raw prompts or logs containing secrets.
- Mobile iPhone: readiness always accessible, no overlapping contextual panes, composer or bottom navigation; ensure CTA not silently disabled.

## J. Incremental implementation sequence aligned to T01–T09

**J0 / T01 — Inventory and contract protection (free/read-only).**
- Pin code SHA, Preview SHA, current worker image hash, DB schema migration version and runtime config flag names (never disclose keys).
- Verify actual execution path through _run_live_build_job -> components_factory -> AutonomousProductEngine -> SandboxExecutor -> PreviewRuntime, identify any wrappers skipped in real staging.
- Mark each capability DEFINED/IMPLEMENTED/WIRED/VERIFIED/BLOCKED based on evidence. Create baseline tests for no extra billing path, no duplicate HTTP engine and no secret leakage.
- Check PR #24 documentation and PR #25 T01 CI recovery; do not mix unmerged branches without explicit merge-base conflict audit.
**Gate:** Baseline/Gaps signed off, no paid call, no Production mutation.

**J1 / T02 + T03 — Backward-compatible contracts and durable state.**
- Add RepairFailure/RepairPatch/ExecutionEvidence v1 as internal schemas; migrate incrementally using adapters.
- Reuse existing task/lease/checkpoint/outbox tables; add columns/migration only with evidence existing schema is insufficient; forwards/backwards migration test before data writes.
- Add clear versioned stage events in Worker and customer/operator views. Verify caller consent and contract hash.
**Gate:** duplicate requests and worker kill/replay do not double-charge or lose accepted state.

**J2 / T04 — SandboxAdapter compatibility (existing Docker first).**
- Wrap existing RemoteSandboxRepositoryExecutor/SandboxRepositoryExecutor behind small interface without changing default. Preserve isolation, enable artifact/test evidence collection.
- Add integration tests for path traversal/symlinks, denied secrets, no host mounts, resource limits, kill/cleanup. Run E2B as distinct opt-in POC only after Docker baseline passes.
**Gate:** real multi-file repo tests in isolated baseline + escape attempts fail.

**J3 / T05 — Targeted RepairAgent improvements.**
- Add sanitized bounded failures and candidate context; versioned patch parser; preserve old repair interface as compatibility until CI passes.
- Fix any verified iteration/count divergence; no-op/cycle stop; verify final candidate; preserve best-candidate rollback.
- Add unit/component tests with fake gateway (zero provider spend), then one capped live repair fixture after authorization. Avoid using model calls to debug pure Python code.
**Gate:** injected compile/type error repaired without weakening acceptance; 3 max repair rounds; cap/cancel/no-progress proven.

**J4 / T06 — Preview lifetime and workspace.**
- Keep separated preview lifecycle, private routing and health, verify cross-session project version; fix UI "approved → queued" automatic progress and duplicate controls.
- Include mobile iPhone Safari plus desktop browser interaction tests; no misleading READY for failed preview.
**Gate:** exact version serves real HTML + browser works; user requests change and sees updated preview; reload persists.

**J5 / T07 + T08 — Cost/security/recovery hardening.**
- Reconcile existing provider usage with immutable attempts; exact named quota/billing/circuit-breaker errors and alerts; prevent duplicate settlement on repeat request.
- Verify rollback/recovery of worker/preview and backups, no secret exposure in error messages; CI gates on exact deployed SHA.
**Gate:** failure injection + spending proof; no unapproved paid calls.

**J6 / T09 — Golden E2E (two paid builds only inside founder budget).**
- Scenario A: simple travel website: prompt → approved PRD → quote/reserve → files → build → tests → private preview → conversational change → new version → reload and restore.
- Scenario B: intentional failing TypeScript/Python build requiring patch; verify 1–3 repair rounds and correct tool/provider usage, 0 unresolved mandatory checks.
- Capture run IDs, pinned SHA, separate provider and internal QA remaining, actual charged dollars, acceptance artifacts/screenshots, browser/network logs, URLs and session status.
**Gate:** two repeatable independently verified products; no fabricated PREVIEW_READY or budget exceed. If blocked, report status rather than promoting.

## K. Release safety, metrics, rollback

1. All code changes on an isolated feature branch based on the currently selected integration target. **Never edit main in-place.**
2. Prefer feature flags: REPAIR_STRUCTURED_V1=off default, SANDBOX_ADAPTER=e.g. docker default, E2B_POC_ENABLED=off default. Names are proposed flags, not claims that these config keys exist.
3. Phase rollout: schemas + unit tests; staging no paid calls; founder-only real build with signed cap; private Preview; regression suite; PR review; merge only after exact SHA tests.
4. Rollback: disable added feature flag/revert change and restore worker image without deleting project versions or billing ledger. Keep backups and restore drills. Do not replay externally charged calls from unverified outcomes.
5. Key evidence for PR: files changed, backward-compatibility list, migration rollback test, exact test commands/pass counts, active worker image SHA, Vercel deployment SHA, health/Preview evidence, cost evidence, issue links. No screenshots or markdown marked "LIVE" without real run.

## L. Acceptance matrix — mandatory independent evidence

| ID | Test | Expected |
|---|---|---|
| C01 | Existing file/contract tests and CI before change | Baseline failures recorded, no hidden skip |
| C02 | New schemas accept valid multi-file patch and reject malformed/null/path injection | No file corruption/exec |
| C03 | Unknown source file from compiler output | Diagnostic UNKNOWN or justified candidate; NEVER arbitrary last file |
| C04 | npm/pip install from untrusted request | Denied unless separate approved dependency policy/manifest |
| C05 | 1 initial compile fails + correct model patch | Actual sandbox verifies success, same acceptance IDs |
| C06 | Last (third) repair round | Must be verified before READY, no fourth repair |
| C07 | Bad/unchanged/cyclic patch | No-progress stop; best candidate preserved; no repeated charge |
| C08 | Provider 429, 401, exhausted balance, 5xx | Distinct code, verified evidence, bounded safe fallback |
| C09 | Worker killed during/after provider response | Resume; ledger reconciles ambiguity; no second unauthorized call |
| C10 | Duplicate approval/build enqueue and parallel worker claims | One durable job/contract; no double reserve/settle |
| C11 | Docker filesystem, symlink/host, secret and network escape probes | Deny + audit evidence, no API keys in sandbox |
| C12 | Preview sandbox closes; PreviewProvider remains alive | Separate valid URL until TTL; private access enforced |
| C13 | Build returns exit 0 but behavior/security gate fails | NOT READY, no misleading release |
| C14 | Budget cap hit in repair | Stop, settle recorded usage, release unused reserve |
| C15 | Project modification after first preview | New version and browser-visible change, previous version recoverable |
| C16 | iPhone Safari RTL project flow | Banner/plan/CTA/composer and bottom tabs usable, no overlap |
| C17 | Account with no operator entitlement | Cannot access raw diagnostics or secrets |
| C18 | Exact Vercel SHA preview automation behind protection | Authenticated/bypass-scoped verifications, no public unprotect |
| C19 | Two Golden E2E builds, with one injected repair and re-login | Full pinned artifacts + settled cost; real HTTP/browser success |
| C20 | Existing separate PR #25 and docs PR #24 | No accidental feature overwrite; correct merge order and green gates |

### Required commands (examples, adjust to repo test runner)

    python -m pytest -q tests/test_repair_stop_loss.py tests/test_repair_sees_main_file.py
    python -m pytest -q tests/test_v22_sandbox_executor.py tests/test_m49_sandbox_security.py
    python -m pytest -q tests/test_worker_budget_binding.py tests/test_m4_worker.py
    python -m pytest -q tests/test_preview_router.py tests/test_m3_preview_logic.py
    python -m pytest -q tests/test_provider_quota_and_dialects.py tests/test_m5_build_economics.py
    python -m pytest -q tests/test_plan_driven_execution.py tests/test_worker_deploy_recovery.py

Commands listed for developer execution, **not claiming tests run in this document**. Also run complete CI and safe live staging gates where appropriate.

## M. Known uncertainty and explicit non-goals

- The exact E2B SDK/API methods and suitability are **not verified** from this code sample. The given async with Sandbox() and Sandbox.get_host() usage must be reviewed against pinned official SDK docs, not pasted blindly.
- Current active production/private Preview cannot be marked healthy solely because Vercel says READY: history of 401 PROTECTED and blocked user builds.
- The sample's Claude 3.5 / GPT-4o references are examples, not mandatory model policy. Current model availability and price must be resolved at run time from verified catalog.
- Exact provider balances, profitability, all migrations and end-to-end worker recovery are **not demonstrated by this document**.
- Do not build a second subscription system, second job queue, second user auth database, second billing ledger or second code-generation engine.
- Do not treat a locally passing mock as proof of external network access or E2B Sandbox isolation.

## Definitive deliverable to the implementing chat

**First:** read current HEAD and the above existing modules and documents, then prepare a concrete file-by-file PATCH PLAN / conflict-aware integration plan.  
**Second:** implement on a dedicated branch in smallest reversible increments with tests after each increment, with zero external cost until authorized staging test.  
**Third:** provide actual PR link, commit SHA, passing/failing test summary, environment gates, actual Preview and model billing evidence.  
**Never:** claim it is integrated by merely copying this report, creating a new FastAPI route or returning a mocked preview URL.

**Status of this addendum: SPECIFIED and GitHub-documented. Implementation, merge, live E2E and release remain subject to evidence.**
