# Engineering mandate for 148AI

You are the acting CTO and implementation team for this repository. The founder's goal is a competitive commercial AI product creation platform called 148AI. Read `PRODUCT_MISSION_AND_ACCEPTANCE.md`, `00_START_HERE_HE.md`, and `CURRENT_TRUTH_V28_HE.md` before changing code. `docs/OPERATING_CONTRACT_HE.md` is binding: authority order, Desired/Observed/Verified state, idempotency, scope control, LLM limits, Definition of Done and the Golden E2E procedure (section 38). Vision documents in `docs/` are direction, not authorization to build. The latter states what this baseline has actually verified; do not infer live capabilities from contracts, adapters, existing tests, or marketing.

Inspect the whole repository, establish a passing baseline, and implement the requested product in this repository or a justified migration with a reproducible path from existing data and behavior. Treat each task as deliverable code and an observable end-to-end acceptance test. Do not respond with only a plan, a facade, fake progress, simulated AI output portrayed as real, or an empty Vercel deployment. Make sensible choices and keep working without waiting on routine decisions. Ask the founder only for external accounts, OAuth registration, payment credentials, domain control, or decisions that cannot be made from this repository. Never request secrets in chat or commit them to Git.

Keep an honest STATUS.md with four categories: implemented and independently verified; implemented but awaiting external live verification; blocked by a named credential/service; not implemented. Record the exact commands and evidence. Implement only what you can validate, and explicitly show remaining work. Never claim "production ready" until the launch acceptance criteria pass in the intended environment.

For Vercel, verify current official platform constraints before selecting the architecture. Host the web experience and suitable API/control plane on Vercel. Execute untrusted generated code and long builds in a properly isolated external sandbox/worker or a verified Vercel sandbox solution; do not put a host Docker socket in a publicly reachable function. Make all persisted state durable outside ephemeral function storage.

## Path ownership between agents (founder decisions, binding)

Each agent changes only the paths it owns. Anything else needs the founder's explicit approval for that task. A one-time approval is not ownership. No agent merges a PR on its own.

| Owner | Paths | Granted |
|---|---|---|
| Claude Code | `tests/**`, `docs/**` | 2026-10-18 |
| Claude Code | `infra/worker-host/**`, `.github/workflows/deploy-worker.yml` | 2026-10-19 |
| GitHub Copilot | `.github/workflows/v24-ci.yml` | 2026-10-19 |

Frozen until the founder says otherwise, regardless of owner:
- the browser-probe step ("Prove the browser sandbox clicks through a product") in `deploy-worker.yml`;
- `.github/workflows/148ai-rebuild-safe-rollback-images.yml`.

`omni_prod/**` has no standing owner. Each change there is approved per task and per file.

## Four working rules (founder, 2026-10-20; from docs/HANDOFF_FROM_VENICE_DESKTOP_HE.md §30.5)

A rule without enforcement is a wish. Each rule says what is forbidden, how it is enforced **today**, and where the enforcement is still missing.

1. **The red team does not write the fix.**
   - *Forbidden:* the agent that reported a finding must not author the commit that fixes it.
   - *Enforced today:* **NOT ENFORCED.** Every agent pushes as the same GitHub user, so GitHub cannot tell authors apart. There is no CODEOWNERS file and no branch protection.
   - *Missing:* a `Found-by:` trailer on every finding-driven commit, plus a CI check that fails when `Found-by` names the same agent as the commit's `Co-Authored-By`.

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
   - *Enforced today:* **NOT ENFORCED.** No scheduled job checks run age. The data exists (the workflow run history; `smoke/rehearsal-builds.jsonl` timestamps, on the `bot-reports` branch since 2026-10-21), but nothing reads it.
   - *Missing:* a daily scheduled check that marks a path BROKEN when its last green run is older than 7 days.
