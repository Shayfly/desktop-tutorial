# Issue 29 recovery verification — 2026-10-14

This follow-up is based on the latest PR #28 source head, `e364151` (`fix/docker-oom-rehearsal-20261013`). It does not merge or deploy that branch.

## CI and registry status

At `e364151`, the source CI and synthetic merge-candidate compatibility checks passed. The merge-candidate run [38469185825](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469185825) ran the full suite on the synthetic merge tree: **1,677 passed, 172 skipped, 320 subtests passed**. The `v24-ci` run [38469185912](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469185912) also passed.

The Agent OS consistency check exposed a Windows-only false stale status: Git checked out LF source files with CRLF, while the freshness auditor hashed raw working-tree bytes. `omni_prod/registry_audit.py` now normalizes CRLF before hashing, and `tests/test_registry_audit.py` covers line-ending-only changes. This keeps evidence freshness consistent with Git's normalized source content without treating actual code changes as fresh.

The separate [deployment verification run 38469273807](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469273807) is **blocked**, not green: the protected Preview returned HTTP 401 because no valid Vercel automation-bypass token was supplied. The verifier correctly stopped before its authenticated journey; weakening this gate would turn an unverified deployment into a false success.

## Application-flow evidence

| Area | Verified in this run | Not verified here |
|---|---|---|
| AI conversation | Local conversation, language/UX, retry, and deterministic intake regression tests passed. | A real model-backed conversation and durable production persistence. |
| Architect approval | Requirements, brief fingerprints, plan binding, and approval-policy unit tests passed. | Live PostgreSQL approval/revision transactions; no `M4D2_DATABASE_URL` was configured. |
| Build, repair, and cost | Worker/build state, repair-round, acceptance, and metered-cost regression tests passed. | A real queued build using paid model providers or production cost settlement. |
| Preview | Preview access, router, and smoke regressions passed. | A live Docker preview or authenticated private Preview; Docker is unavailable in this Windows environment. |

The portable local regression set completed with **250 passed, 48 skipped, and 70 subtests passed**. Tests requiring Linux worker-host shell/container behavior and POSIX preview-storage semantics were excluded from that clean run; an initial Windows run confirmed those host assumptions (`bash`/container commands, `/root` paths, and `os.chown`). The upstream Linux merge-candidate run includes the full suite. Skipped tests and mocked-provider tests are not evidence of live infrastructure.

## Readiness

The source and merge-compatibility CI gates are green at the inspected PR head, and the Windows registry-freshness mismatch is covered by a regression test. Authenticated deployment verification, real PostgreSQL durability, worker-host recovery, paid model execution, and live Docker preview remain open operational gates. No production changes or paid provider calls were made.
