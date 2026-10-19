# deploy-worker — known flakes and working rules

## F1: exit 255 in step 4 ("Confirm deployment scope") right after a push
| # | Run | Started | What preceded it |
|---|---|---|---|
| 1 | 39275019633 | 2026-10-19 15:06:39Z | a force-push to the branch about a minute earlier |
| 2 | 39295236360 | 2026-10-19 17:34:21Z | 22 seconds after the PR #67 merge, while 5 CI workflows were starting |

- **Symptom:** `Process completed with exit code 255` in 0 seconds. There is no `::error` annotation, which means neither of the `grep` checks in the step fired.
- **The same step passes when re-run:** both times, a second dispatch minutes later passed, with the same commit and the same `.env`. A read-only probe on the host passed every check in the step: compose config rc=0, `OMNI_ENV=staging`, `OMNI_INTAKE_MODEL=1`.
- **Cause:** not yet known. The job log can't be read from the agent environment (blob 403).
- **Working rule (founder, 2026-10-19):** dispatch deploy-worker only after CI on the commit has settled, meaning no `in_progress` / `queued` runs on it.
- **Third time:** stop and investigate. Do not dispatch again.

## F2: a job finishes on the runner but stays `in_progress` on GitHub
- **Run:** rehearsal 39280924963. Its step finished at 15:57:41Z, but the job stayed `in_progress`, held the self-hosted runner for about 30 minutes, and then closed as `failure`. Its annotations arrived only once it closed.
- **Meanwhile:** other self-hosted jobs stay in `queued`. `cancel` / `force-cancel` return 409 ("completed") on the run.
- **What to do:** wait for the job to close. The step's output is also in the runner's page logs (`/home/omni/actions-runner/_diag/pages/*.log`).

## F3: GitHub keeps at most 10 annotations of each level per step
Lines beyond that are dropped, for example in the snapshot step (4 services × 3 rungs). A missing annotation does not mean a missing event.
