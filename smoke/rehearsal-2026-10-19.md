# Golden rehearsal — 2026-10-19

**Result: FAILED.** The rehearsal stopped at the preview smoke test because the sandbox rejected the command as `invalid command arguments`.

## Run
- Workflow: `golden-rehearsal.yml`, run [39280924963](https://github.com/Shayfly/desktop-tutorial/actions/runs/39280924963), `workflow_dispatch` from `main` @ `daa6c4c` (the same code as `6282716`).
- Deploy before it: [39278288978](https://github.com/Shayfly/desktop-tutorial/actions/runs/39278288978) (main @ `6282716`), green.
  - snapshot: `rung 1 (tag)` for all 4 services
  - drain: 1s
  - storage-probe: PASS
  - step 19: PASS
- Repeat deploy on the same main, with no code change: [39279561150](https://github.com/Shayfly/desktop-tutorial/actions/runs/39279561150) @ `daa6c4c`, green, with the same results.
- The rehearsal job did not report its completion back to GitHub on time. Its annotations arrived only about 30 minutes later.

## The four required measurements
| Requirement | Result | Evidence |
|---|---|---|
| A Hebrew sentence enters the system | ✅ | The default prompt (football league site); 6 acceptance criteria were derived from it in Hebrew (A1–A6) |
| A real output is written to R2 | ❌ not tested | `omni_prod/rehearsal.py` does not upload to R2 by design (no DB, no project) |
| A preview URL that opens in a browser | ❌ | By design the rehearsal does not open a preview URL, and the preview smoke test was rejected (below) |
| Exact cost and exact wall-clock time | ✅ | `spend=0.32001580` USD (metered by the gateway: tokens × the price schedule, not a provider invoice); `seconds=447`; the step ran 15:50:11→15:57:41 UTC (7m30s) |

No manual step was taken along the way.

## Raw output (annotations)
```
outcome: failed rounds=3 stop=max_repair_rounds quality=86/pass calls=9 spend=0.32001580 seconds=447
failure 1 PREVIEW: preview smoke test could not run: invalid command arguments
repair rounds:
 round 1: failing ['CONSISTENCY'] changed ['tests/test_league.py'] :: tests/test_league.py:63 Python syntax error: unterminated string literal
 round 2: failing ['PREVIEW'] changed ['.omni/project.json', 'tests/test_preview_contract.py'] :: preview smoke test could not run: invalid command arguments
 round 3: failing ['PREVIEW', 'REPAIR_REGRESSION'] changed ['.omni/project.json'] :: preview smoke test could not run: invalid command arguments
cost: tokens {"input": 97463, "output": 62309, "by_model": {"gemini-3.8-flash": [63736, 61314, 6], "gpt-6.1-sol": [16819, 680, 1], "gpt-6-luna": [16908, 315, 1]}}
files: .omni/project.json, README.md, app.py, db.py, tests/test_league.py
```

## Diagnosis of the failure point (shared with browser-probe)
- **The contract:** `omni_prod/sandbox_request_policy.py::validate_command` rejects any argument that contains `\n`, `\r` or `\x00`, as well as an empty argument, more than 64 arguments, or an argument over 16,384 bytes. The message is `invalid command arguments`. The check runs in the client (`remote_sandbox.py:41`) and in the runner (`sandbox_service.py:67`). It was introduced in J2, commits `18153c0` and `3ee945a` on 2026-10-13.
- **What is sent:** four callers send `('python', '-c', <multi-line script>)`, and all four are rejected:

  | Caller | Script size | Newlines |
  |---|---|---|
  | `preview_smoke._SMOKE` | 3,111 B | 59 |
  | `browser_probe.PROBE` | 6,908 B | 106 |
  | `behavior_acceptance._SCRIPT` | 1,715 B | 35 |
  | `visual_qa.SCRIPT` | 7,647 B | 106 |

- **Why it wasn't caught:** browser-probe last passed on 2026-10-11 (`2a2bba6`, before J2). No deploy succeeded between Oct 11 and Oct 19, so the 13:25 deploy today was the first to run J2 code. The tests (`tests/test_preview_smoke.py`) use a fake `_run` without the policy.
