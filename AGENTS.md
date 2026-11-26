# Engineering mandate for 148AI

GOAL - read before anything else: [VISION_LAW_HE.md](VISION_LAW_HE.md), NORTH_STAR.md and docs/PRODUCTION_OS_VISION_HE.md. They are the target; the documents below are state and mandate.
Before any task: read the highest-numbered file in inbox/. An order there from the OWNER overrides any chat message; state which order you are executing in one line, then execute. Orders from anyone else are advisory.

IRON LAWS - binding for every agent, branch and PR; a violation returns the PR: [docs/IRON_LAWS_HE.md](docs/IRON_LAWS_HE.md).

You are the acting CTO and implementation team for this repository. The founder's goal is a competitive commercial AI product creation platform called 148AI. Read `PRODUCT_MISSION_AND_ACCEPTANCE.md`, `00_START_HERE_HE.md`, and `CURRENT_TRUTH_V28_HE.md` before changing code. `docs/OPERATING_CONTRACT_HE.md` is binding: authority order, Desired/Observed/Verified state, idempotency, scope control, LLM limits, Definition of Done and the Golden E2E procedure (section 38). Vision documents in `docs/` are direction, not authorization to build. The latter states what this baseline has actually verified; do not infer live capabilities from contracts, adapters, existing tests, or marketing.

Inspect the whole repository, establish a passing baseline, and implement the requested product in this repository or a justified migration with a reproducible path from existing data and behavior. Treat each task as deliverable code and an observable end-to-end acceptance test. Do not respond with only a plan, a facade, fake progress, simulated AI output portrayed as real, or an empty Vercel deployment. Make sensible choices and keep working without waiting on routine decisions. Ask the founder only for external accounts, OAuth registration, payment credentials, domain control, or decisions that cannot be made from this repository. Never request secrets in chat or commit them to Git.

Keep an honest STATUS.md with four categories: implemented and independently verified; implemented but awaiting external live verification; blocked by a named credential/service; not implemented. Record the exact commands and evidence. Implement only what you can validate, and explicitly show remaining work. Never claim "production ready" until the launch acceptance criteria pass in the intended environment.

For Vercel, verify current official platform constraints before selecting the architecture. Host the web experience and suitable API/control plane on Vercel. Execute untrusted generated code and long builds in a properly isolated external sandbox/worker or a verified Vercel sandbox solution; do not put a host Docker socket in a publicly reachable function. Make all persisted state durable outside ephemeral function storage.

## Path ownership between agents (founder decisions, binding)

Role ownership applies by responsibility, not historical path allowlists. Claude owns product and intake; Codex owns governance, CI and documentation; Matt independently verifies. Agents may edit paths needed for their assigned domain, subject to protected-file restrictions and independent review. No agent may approve its own change. Routine merges are permitted only when CI is green for the exact head SHA and an independent verifier has approved that SHA. The implementing agent cannot approve its own work. CEO approval is required only for irreversible changes: schema changes, provider replacement, or changes to the approval flow. This founder decision (2026-10-27) supersedes earlier blanket CEO-approval requirements for routine merges.

> **Note, 2026-11-25 (the owner's decision governs merges now):** the owner cancelled the independent review ("מבטל את
> הביקורת של מאט", 19:10 UTC) and gave Claude Code a standing approval to merge. A routine merge now needs CI green on
> the exact head SHA and that standing approval; Claude Code's own review by separate reviewer agents is reported in
> the pull request as the author's own check, not as an independent approval (OWNERS.md rule 1, CLAUDE.md section 2
> rule 9, law 7 below; the owner's words in inbox/002). The paragraph above is kept as the record of the 2026-10-27
> rule.

| Role | Responsibility |
|---|---|
| Claude Code | Product and intake |
| Codex | Governance, CI and documentation |
| Matt | Independent verification, no self-approval |

Frozen until the founder says otherwise, regardless of owner:
- the browser-probe step ("Prove the browser sandbox clicks through a product") in `deploy-worker.yml`;
- `.github/workflows/148ai-rebuild-safe-rollback-images.yml`.

Changes to `omni_prod/**` follow role ownership and independent review. CEO approval remains mandatory for schema/data migrations, provider or paid-route changes, client approval-flow changes, new or over-budget spend, or conflicts between evidence and instruction.

Before starting any task, every agent MUST read root `STATUS.md`, `TASKS.md`, and `OWNERS.md`. At task completion, update `STATUS.md` with date, author, verified green/red/blocked status and evidence, and update `TASKS.md` with owner, status, SHA/run links. Do not report success without proof of executed work. Root files are the only shared state; do not create duplicate `docs/state/` files.

Routine reversible PRs may merge only after green CI on exact SHA and approval by a different independent verifier. No force-push to main; never modify `tests/test_evidence_export.py:18`. Separate commits per topic.

> **Note, 2026-11-25:** "approval by a different independent verifier" is replaced by the owner's standing approval
> (the note above, OWNERS.md rule 1). The rest of the line stands: green CI on the exact SHA, no force-push to main,
> `tests/test_evidence_export.py:18` untouched, separate commits per topic.

## Four working rules (founder, 2026-10-20; from docs/HANDOFF_FROM_VENICE_DESKTOP_HE.md §30.5)

A rule without enforcement is a wish. Each rule says what is forbidden, how it is enforced **today**, and where the enforcement is still missing.

1. **The red team does not write the fix.**
   - *Forbidden:* the agent that reported a finding must not author the commit that fixes it.
   - *Enforced today:* **PARTIAL** (corrected 2026-11-21). `.github/workflows/finding-attribution.yml` (`scripts/check_finding_attribution.py`) fails a commit whose `Found-by:` names the same agent as its `Co-Authored-By`. main's branch protection requires `test` and `validate` (C16, live since 2026-10-20; `enforce_admins` off). Every agent still pushes as the same GitHub user, so GitHub itself cannot tell authors apart, and since 2026-11-21 only one agent works (`OWNERS.md`).
   - *Missing:* a separate, non-admin GitHub identity per agent, so that authorship is a fact GitHub records and not only a trailer.

2. **The seam rule.**
   - *Forbidden:* a test at a boundary (sandbox policy, the verification chain, the transport, money) that uses a permissive double instead of the real boundary code.
   - *Enforced today:* **PARTIAL.** These tests cross the real boundary:
     - `tests/test_sandbox_callers_real_policy.py`: the real `RemoteSandboxRepositoryExecutor._run` and `validate_command`;
     - `tests/test_verification_group.py` and `tests/test_round_preflight.py`: the real `investor_app._verification_executor` chain.
   - *Missing:* five fakes still bypass the real validator. They are `tests/test_preview_smoke.py`, `tests/test_browser_probe.py`, `tests/test_visual_qa.py`, `tests/test_behavior_acceptance_in_build.py` (`LocalSandbox`) and `tests/test_acceptance_coverage.py` (`_OkSandbox`). No check rejects a new one.

3. **Status is derived, never hand-written.**
   - *Forbidden:* editing a registry, matrix or status file by hand.
   - *Enforced today:* **ENFORCED in CI.** The committed file must equal what the generator produces, or the `test` and `validate` jobs fail:

     | Generator | Files | Test |
     |---|---|---|
     | `python -m omni_prod.agent_os.audit --write` | `AGENT_OS_REGISTRY.json`, `TRUTH_MATRIX.json` | `tests/test_agent_os.py` |
     | `python -m omni_prod.agent_os.departments --write` | `DEPARTMENT_MATRIX.json` | `tests/test_conversation_os.py` |
     | `python -m omni_prod.registry_audit --write` | `docs/AGENT_SKILL_STATUS.md` | `tests/test_registry_audit.py` |
     | `python -m omni_prod.intelligence.matrix --write` | `PROVIDER_MATRIX.json` | `tests/test_intelligence_plane.py` |

   - *Missing:* `STATUS.md` and the `smoke/*.md` reports are not covered.

4. **A critical path that has not run for 7 days is broken.**
   - *Forbidden:* reporting a critical path (deploy-worker, golden rehearsal, Golden E2E, postdeploy verify-replay, backup-restore) as working when its last successful run is older than 7 days.
   - *Enforced today:* **ENFORCED daily** (corrected 2026-11-21). `.github/workflows/critical-path-freshness.yml` (`scripts/check_critical_path_freshness.py`, since 2026-11-19) marks a path BROKEN when its last green step is older than 7 days.
   - *Missing:* the paths that run only when dispatched (golden rehearsal, Golden E2E) still need someone to run them; `smoke/rehearsal-builds.jsonl` stopped at 2026-10-19 because its job pushed to main, which main's protection rejects.

## Eleven development laws (the owner's directive §2; plan v3 S1.6, 2026-11-25)

Audited on main `9628dcd`; every claim cites the code. Each law gives what is forbidden, how it is enforced **today**,
and what is still missing. One fact applies to all of them: only `test` (`v24-ci.yml`) and `validate`
(`v11-overlay-ci.yml`) are required on main, with no required pull request review, and `enforce_admins` is off
(`CONTROLS.json:855-861`). For the admin identity that merges, every check below is a process rule (CLAUDE.md §2), not a
GitHub rule. "Not required" means a red result does not block a merge.

1. **No dummy or fake code in a production path.**
   - *Forbidden:* a stub, canned output, in-memory store or simulation that staging or production can reach.
   - *Enforced today:* **PARTIAL.**
     - `legacy_paths_guard` (`omni_prod/investor_app.py:113-133`) answers 410 on staging and production for the known
       fake paths (template builds, the in-memory hosted runtime, canned templates, the patch path that skips every gate).
       It is tested in the required `test` job (`tests/test_legacy_paths_guard.py`).
     - `OMNI_CREATOR_PERSISTENCE=memory` is refused only when `OMNI_ENV=production` (`investor_app.py:168-171`). The
       worker runs `OMNI_ENV=staging` (`deploy-worker.yml:104`).
     - `omni_prod/staging_simulation.py` and `omni_prod/recovery_drill.py` ship simulated artifacts in the package. Nothing
       imports them today, so they stay off the production path by convention only.
   - *Missing:* a required check that walks the import closure of the production entry points (`omni_prod.investor_app`,
     `omni_prod.worker`) and fails on a module or symbol from a declared fake list. It can reuse the closure walker of
     `omni_prod/pipeline_identity.py`. The `memory` refusal should also cover staging.

2. **No capability is marked active without proof of execution.**
   - *Forbidden:* a registry or status that says a capability works (VERIFIED, REAL_SERVER_VERIFIED, LIVE, AVAILABLE)
     without a run that executed it.
   - *Enforced today:* **PARTIAL.**
     - Statuses are computed. A verified status needs `live` evidence whose implementation files are unchanged since the
       evidence commit (`omni_prod/agent_os/audit.py:64-73`; `omni_prod/registry_audit.py:133-166`; digests in
       `omni_prod/registry_evidence_lock.json`).
     - `inflation_findings` refuses a verified status without evidence. It runs in the required `test` job, step
       "Capability auditor (agent 47)" (`v24-ci.yml:118-119`).
     - The evidence itself is a run id typed into code (`omni_prod/agent_os/evidence.py`). Nothing looks the run up or
       checks that it was green.
     - `AGENT_OS_REGISTRY.json` and `TRUTH_MATRIX.json` are compared by counts only (`tests/test_agent_os.py:42`, `:268`).
     - `omni_prod/agents_registry.py` keeps 11 hand-written PARTIAL statuses on the product path.
   - *Missing:*
     - a check that resolves every `Evidence.ref` run id through the Actions API and requires success on the cited commit,
       as `tools/drill_runs_from_github.py` already does for drills;
     - full-row comparison of the two registries;
     - derived or removed statuses in `agents_registry.py`.

3. **No agent is marked active only because it has a prompt.**
   - *Forbidden:* counting an agent as working when all it has is an instruction to a model.
   - *Enforced today:* **PARTIAL.**
     - Agent OS holds a guidance-only agent at IMPLEMENTED: "model instruction only" (`omni_prod/agent_os/audit.py:57-61`).
     - registry_audit gives a role with no runtime binding DEFINED (`registry_audit.py:207-208`): 42 of 61 roles.
     - "Prompt only" is recognised by the import path of `skills_runtime` alone, so another wrapper around a prompt counts
       as IMPLEMENTED (inferred).
     - The recorder writes which agent actually ran (`agent_runs`, `agent_tasks`; `infra/postgres/034_agent_runtime.sql`),
       but no auditor reads those tables.
   - *Missing:* a check that keeps an agent at IMPLEMENTED or below until its own `agent_tasks` rows from real builds
     show an output that another agent verified.

4. **No Skill is marked connected without proof that it ran and affected the result.**
   - *Forbidden:* showing a skill as CONNECTED or applied when no build shows that it ran and changed what was delivered.
   - *Enforced today:* **NOT ENFORCED.** The code defines CONNECTED the other way:
     - Runtime prompt skills default to CONNECTED with no evidence (`vstatus or CONNECTED`, `registry_audit.py:314`).
       Today 14 of 20 are CONNECTED with verification "none".
     - For roles, CONNECTED means "configuration observed or unit tests only" (`registry_audit.py:15`, `:223-224`).
     - #525 records execution, not effect (`skills_runtime.py:1007-1028`; `product_review.py:237-250`), and no status
       reads that record.
     - `applied_skills()` reports every web skill as applied, unconditionally (`skills_runtime.py:1032-1033`).
   - *Missing:* CONNECTED derived from stored builds (`build_jobs.evidence_json` → `product_review[].skill_execution`).
     Each skill needs a probe that completed in a real build and a finding that a later round cleared (the effect).
     `applied_skills()` should report only the skills that ran.

5. **No test is weakened to get a green result.**
   - *Forbidden:* deleting, loosening, skipping or neutralising a test or a CI step so that red reads green.
   - *Enforced today:* **PARTIAL.**
     - Every deleted line needs a declaration bound to the sha256 of exactly those lines (`scripts/deletions_declared.py`,
       job `light`, `v24-ci.yml:53-63`). `light` is not required, and the reviewer field is a string (law 7).
     - The negative controls run in job `negative-controls` (`v24-ci.yml:162-187`), as three parallel shards since the
       change of 2026-11-26: the checks `negative-controls (1)`, `negative-controls (2)` and `negative-controls (3)`.
       None of them is required. The required `test` job only checks that the specs still apply
       (`tests/test_negative_controls_apply.py`).
     - The regression guardian keeps a minimum test count per area, but reads the minimum from the branch itself
       (`omni_prod/agent_os/meta.py:69`).
     - A weakening that only adds lines passes every check: a new `skip`, `xfail`, `continue-on-error` or `|| true`.
   - *Missing:* a required check that diffs the PR against main and fails on new skip or xfail markers,
     `continue-on-error` or `|| true`, unless declared and signed. The regression floor should be read from main
     (CLAUDE.md §4). `light` and the three checks `negative-controls (1)`, `(2)` and `(3)` should be required. A rule
     that required the old single check `negative-controls` would block every pull request: no job reports a check by
     that name any more.

6. **No hiding of failures, deleting of evidence or inventing of results.**
   - *Forbidden:* a failure that does not surface, evidence that is removed, or a result that no run produced.
   - *Enforced today:* **PARTIAL.**
     - The CI scripts fail closed: an empty or missing junit report is not a pass (`scripts/junit_report.py`).
     - `critical-path-freshness.yml` goes red daily on a broken path, but it opens no issue and blocks no merge or deploy.
     - A deleted text line needs a declaration. A deleted binary under `docs/evidence/` or `smoke/` passes, because
       `deletions_declared.py:43` skips `--numstat` "-" rows (inferred).
     - The evidence run ids are not checked (law 2). `STATUS.md` and `smoke/*.md` are hand-written.
   - *Missing:*
     - count deleted binaries in evidence paths;
     - open an issue on a broken freshness path, as the drills do;
     - resolve every run id cited in `STATUS.md` and the evidence records.

7. **No self-approval: an author does not approve their own work.**
   - *Forbidden:* the author of a change approves, signs or verifies it.
   - *Enforced today:* **PARTIAL** (string checks only; GitHub enforces nothing).
     - A declaration's reviewer must differ from its author (`scripts/deletions_declared.py:74-76`;
       `scripts/identity_declared.py:42-44`), but it is a free-text field in a file the author edits. The
       `signature_note` that CLAUDE.md §8 requires is read by no code.
     - `finding-attribution.yml` (not required) fails a commit whose `Found-by:` and `Co-Authored-By:` name the same
       agent. A commit without `Found-by:` passes.
     - There is no required review and no CODEOWNERS (`CONTROLS.json:855`), and every agent pushes as one GitHub user.
     - Plan v3 (2026-11-25) had ChatGPT review every pull request on its full head SHA. The owner cancelled that
       review the same evening (OWNERS.md, rule 1). What remains is CI on the exact SHA, the owner's standing approval,
       and a review that Claude Code runs on its own branch with separate reviewer agents. That review is the author
       checking its own work; nothing independent of the author approves a merge today.
   - *Missing:* an approval that GitHub records from an identity other than the one that pushed, such as a required
     review on main or a signed approval verified against a key the author does not hold.

8. **No exposure of API keys, secrets or customer data.**
   - *Forbidden:* a key, a secret or a customer's personal data in the repository, a log, an artifact or an evidence file.
   - *Enforced today:* **PARTIAL.**
     - `scan_tree` (`omni_prod/secret_scan.py:90-113`) runs in the required `test` job (International gate,
       `v24-ci.yml:121-124`). It scans the checked-out tree only, skips `tests/` and `.md`, and has no Google `AIza…`
       pattern of its own.
     - Logs pass through one redaction layer in the API and the worker (`omni_prod/secret_redaction.py`). Nine workflows
       carry their own `sed` redactors with different patterns, and none is tested.
     - Nothing scans for personal data.
   - *Missing:*
     - a required scan of every changed file, all suffixes, including `.md` and `tests/`, with the redaction layer's
       patterns;
     - one shared redactor for workflow output;
     - personal-data patterns for `docs/evidence/` and `smoke/`.

9. **No parallel system built when an existing infrastructure can be upgraded.**
   - *Forbidden:* a second registry, redactor, runner or state file beside one that could have been extended.
   - *Enforced today:* **NOT ENFORCED.** Two narrow parity checks exist: the evidence-export redactor
     (`tests/test_redaction_single_layer.py`) and the build's secret probes reusing `secret_scan`. Main holds today:
     - three agent registries (`agent_os/agents.py`, `agent_catalog.py`, `agents_registry.py`);
     - four skill lists (`agent_os/skills.py`, `skill_catalog.py`, `skills_registry.py`, `skills_runtime.py`);
     - two status vocabularies;
     - nine workflow-local redactors.
     The system map (S1.5, `omni_prod/system_map.py`) maps those vocabularies onto the plan's six states without
     adding a third; the mapping is in `docs/SYSTEM_MAP.md`, the full map is built in CI (artifact `system-map`).
   - *Missing:* a declared map from each shared concern to its one module, and a check that fails a diff adding a second
     implementation (a new `*_registry.py`, a new redaction regex outside `secret_redaction.py`, a new status enum).

10. **No moving to the next stage before the previous stage's acceptance conditions are met.**
    - *Forbidden:* starting stage N+1, of the plan or of the merge → release → deploy chain, while a condition of stage
      N is unmet.
    - *Enforced today:* **PARTIAL** (merge and release only).
      - `test` and `validate` are required for a non-admin; `drill-c16.yml` re-proves that twice a month.
      - The worker and Vercel deploy only on a `[release]` title or a manual dispatch (`scripts/release_gate.py`;
        `scripts/vercel_ignore_build.mjs`). The deploy does not read v24-ci's result for the SHA it deploys.
      - Plan stages: no file records their acceptance conditions. From plan v3, every pull request names its task, or
        says "none: <reason>" when it is outside the plan (`.github/pull_request_template.md`,
        `scripts/check_pr_report.py`, S1.7; the "PR report" check is not required). The title carries the stage, but
        no check yet compares stages.
    - *Missing:* a machine-readable stage file (stage id, acceptance conditions as test or workflow ids, status derived
      from their runs), with a check that fails a pull request of stage N+1 while stage N is open. The deploy job should
      read the required checks of its SHA.

11. **Every code change is reproducible, testable and revertible.**
    - *Forbidden:* a change that cannot be rebuilt from the repository, has no test that runs in CI, or cannot be undone.
    - *Enforced today:* **PARTIAL.**
      - Testable:
        - the full suite runs in the required `test` and `validate` jobs;
        - every test file must be run by some job (`scripts/ci_test_coverage.py`);
        - PostgreSQL tests run only in `intake-budget-pg.yml`, which is not required;
        - nothing requires a change to `omni_prod/` to bring a test or a mutation (CLAUDE.md §3).
      - Reproducible:
        - Python dependencies are pinned at the top level without hashes, and actions by major tag.
        - A fresh database is rebuilt and its migration checksums verified only on PRs that touch `infra/postgres/`.
      - Revertible:
        - the worker's images are saved before every deploy and restored after a failure (`deploy-worker.yml:120-121`,
          `:279-281`);
        - down migrations exist only for 042–045 of 41 forward files;
        - nothing requires a down file for a new migration.
    - *Missing:* a required diff check that fails on a new migration without a down file and its test, on an
      `omni_prod/` change with no test or control changed, or on an unpinned dependency, plus a hashed lockfile.

**Discrepancies found by this audit:**
- **Rule 3 above ("Status is derived") is stronger than the tests.** `AGENT_OS_REGISTRY.json` and `TRUTH_MATRIX.json`
  are compared by counts only. `PLATFORM_REGRESSION_MATRIX.json`, `PLATFORM_CAPABILITY_MATRIX.json` and
  `GOLDEN_E2E_MATRIX.json` have no currency test.
- **`omni_prod/agent_os/recorder.py:7-8` claims more than the code does.** It says the auditor reads `agent_tasks` as
  runtime truth; no auditor reads it.
- **`light` and `negative-controls` are not required checks**, although `v24-ci.yml:39-40` says an undeclared deletion
  "fails HERE".
- **IRON_LAWS law 28 ("all CI green including pg") is not enforced:** `pg` is not required (`CONTROLS.json:394-395`).
- **`docs/SECRETS_POLICY.md:78` cites an old trigger and line for the secret scan.**
