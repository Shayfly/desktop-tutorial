# Controlled GitHub Actions cost optimization — 2026-10-14

Base: `shayfly-conversation-provider-vertical-slice`, commit `c7df5882a13172e56ce2686db80a3a2034ca56aa`.
Candidate branch: `codex/github-actions-cost-optimization-2026-10-14`.
Review status: draft; Linux service/browser execution is not verified.

## Evidence and cost basis

The latest 100 runs sampled covered 2026-10-14 00:06:20–07:19:51 UTC.
43 successful runs had 123.87 aggregate job-minutes:

| Workflow | Successful sampled runs | Aggregate job-minutes |
|---|---:|---:|
| v24-ci | 13 | 59.80 |
| intake-budget-pg | 11 | 35.80 |
| V11 Overlay CI | 13 | 27.20 |
| Intake architecture gates | 6 | 1.07 |

16 workflow/commit pairs ran successfully for both push and pull_request. Their push sides consumed 53.03 job-minutes.
Example: same commit `19a069f6e6034231e504567a400eb5bd0e3cb78d`, v24-ci push [38517868326](https://github.com/Shayfly/desktop-tutorial/actions/runs/38517868326) consumed 4.50 job-minutes and PR [38517873409](https://github.com/Shayfly/desktop-tutorial/actions/runs/38517873409) consumed 4.77.
These are elapsed runner job times, not billing records. Net savings need measurement after integration and include the added fast/classification/final-gate overhead. No dollar or monthly savings claim is made.

GitHub [upstream run 38532585252](https://github.com/Shayfly/desktop-tutorial/actions/runs/38532585252/job/115747713659) reports: jobs did not start because recent account payments failed or the spending limit needs to be increased. Neither account settings nor spending limits were changed.

## Execution policy

- Full CI: all PRs, pushes to `main` and `milestone/pre-staging-2026-10-05`, and explicit manual dispatch.
- Feature-branch pushes: the separate five-minute fast workflow checks Python, workflow YAML, JavaScript and CI policy tests; it does not download Chromium or start databases.
- Feature PRs run the full suites once per revision rather than repeating them on every feature push.
- Full pytest, unittest, registry/no-inflation, hostile static, international, architecture/product intent and compose checks remain.
- PostgreSQL/Redis/real Docker recovery and customer browser tests skip only when every changed path is a top-level Markdown file or Markdown beneath `docs/`.
- Code, dependencies, SQL, Dockerfiles, workflow metadata, executable docs, unknown paths, renames/deletions and missing/unreadable diffs run heavy checks. Manual dispatch always runs heavy checks.
- Existing required job IDs `pg` and `customer-ui` remain as final checks. They run with `always()` and fail unless classification succeeded and heavy tests succeeded, or classification explicitly established docs-only and the heavy job was skipped.
- Stable integration pushes and PR validation are distinct checks; a PR sourced from an integration branch can intentionally run both.
- Neon bootstrap keeps its existing infrastructure path filter. Repository branch protection cannot be inspected through this connection (403); no new top-level PR path filters were introduced.
- CI concurrency is scoped to workflow plus PR number (or branch ref), not commit SHA or source branch name. New commits cancel obsolete CI; different PRs, including forks with matching branch names, stay separate.
- Merge compatibility now uses a stable workflow/PR group so later source/base revisions cancel stale merge checks.
- Stateful deploy, backup, registry-writing and paid/manual rehearsal jobs retain non-cancellable concurrency and existing triggers. No deployment or paid dispatch was performed.

## Time limits and diagnostics

| Work | Limit |
|---|---:|
| Feature fast job | 5 min |
| Change classification / required final check | 3 min |
| V11 validation | 10 min |
| Full pytest and security checks | 15 min |
| Compose config | 5 min |
| Browser job | 10 min |
| Chromium install / browser test step | 5 min each, within job limit |
| PostgreSQL + Redis + Docker job | existing 20 min |
| Database migration / integration test step | 3 / 12 min |
| Neon bootstrap | 10 min |
| Worker Docker image build, before any drain | 20 min, existing deploy job 60 min |
| One-time rollback image reconstruction step | 25 min, existing job 35 min |
| Merge compatibility | existing 20 min |

Pytest and PostgreSQL JUnit reports upload on `always()`, with seven-day retention. Missing reports are reported rather than fabricated; GitHub job logs remain the source for startup/timeouts before a report exists.

## Validation and limitations

- Red phase: revised CI policies failed against original workflows and missing scope helper.
- Green: `python -m pytest -q -p no:cacheprovider tests/test_ci_scope.py tests/test_ci_workflow_concurrency.py tests/test_ci_yaml_validation.py`: **16 passed, 37 subtests passed**.
- Fast workflow command: `python -m unittest discover -s tests -p 'test_ci_*.py' -v`: **16 passed**.
- `python scripts/validate_workflows.py`: **28 workflows passed** (YAML parsing, duplicate-key rejection, events and jobs). This is not an actionlint result.
- `python -m compileall -q omni_prod tests scripts` and Node syntax checks for both browser scripts plus the browser harness passed.
- Actual final-gate CLI was exercised for successful heavy checks, legitimate docs-only skips, classifier failure, missing output and failed tests; exit codes matched the policy.
- Independent review found a skipped-required-check risk; final always-running checks and failure coverage fixed it. Re-review found no further important issues and independently reran the focused tests.
- Whole-suite baseline: **1,620 passed, 72 failed, 172 skipped**, plus the original concurrency test passed separately. New CI tests were excluded from this baseline.
- Whole-suite final: **1,645 passed, 63 failed, 172 skipped**, 357 subtests passed. No final failing test ID is new relative to the baseline.
- Source download originally introduced terminal newline differences. These were corrected against Git blob hashes, including one original Windows-1252 JSON file. 789 untouched downloaded files match upstream hashes; only the intended eight workflows and original concurrency test differ. Two original logo assets used by tests were restored. Other binary assets were not downloaded and are not changed in the PR.
- Local environment is Windows/Python 3.13, while CI uses Linux/Python 3.12. Temporary-directory access is denied even inside the allowed workspace; Docker/Bash/service integration and several preview tests cannot run here. The complete local suite is **not green**.
- Whole-suite command: `python -X utf8 -m pytest -q -p no:cacheprovider --ignore=pytest-cache-files-kl5ai10v --junitxml=../final.xml`. The ignored directory is a denied transient cache directory created by an earlier local pytest invocation, not repository tests.
- Full Linux, PostgreSQL, Docker and browser execution on the candidate remains blocked by the GitHub account startup error. No reruns were requested to work around the billing block.

## Rollback and follow-up

Revert the optimization commit to restore original triggers/time limits; no data migration is involved.
After the account allows runners to start, verify the draft PR's full checks, a docs-only PR (both required final checks must pass), a failing classifier (required final checks must fail), and two consecutive commits (older CI cancels).
Compare new job-minute totals against this sample, including new fast and final-gate overhead. Keep the PR unmerged until Linux checks are verified.

