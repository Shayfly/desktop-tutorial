<!-- The delivery report of the owner's plan (section 17). Every section below is required and checked on each push and
each edit of this text (scripts/check_pr_report.py, the "PR report" workflow). Every piece of evidence refers to the head
SHA of this PR. Write "none" or "not measured" with the reason where a field has nothing; never leave it empty. -->

## Task ID
<!-- The plan's task id(s), for example S1.7. The PR title names it too. -->

## Requirement
<!-- The original requirement, quoted from the plan or the owner's message, with its date. -->

## Baseline
<!-- The state before this change: main SHA, what was broken or missing, and how that was seen (run id, log line, row). -->

## Architecture
<!-- The approach chosen and why; the alternatives that were rejected. -->

## Implementation
<!-- What was actually done, per commit. -->

## Code
<!-- Links to the new modules and the changed files at the head SHA. -->

## Diff
<!-- Files added, changed and deleted against the base SHA; every deleted line declared in docs/identity/allowed-deletions.json. -->

## Dependencies
<!-- New or changed packages, services, secrets (names only), migrations; "none" if none. -->

## Security
<!-- Risks, permissions, data touched, and how each is limited. -->

## Tests
<!-- Commands, SHA, environment, counts (passed / failed / skipped / expected failures), negative controls with their results. -->

## Evidence
<!-- Raw evidence: run ids, log lines, read-only database rows, screenshots. A mock is not evidence of a live connection. -->

## Cost
<!-- Spend measured or reported by the provider, kept apart from estimates; "none" if nothing was spent. -->

## Performance
<!-- Before and after measurements in the same environment, or "not measured" with the reason. -->

## Deployment
<!-- Whether this reaches production with its merge ([release]) and what is deployed today. -->

## Rollback
<!-- How to undo it: revert commit, flag, down migration, previous deployment. -->

## Reviewer
<!-- The independent reviewer (ChatGPT, plan v3) and the full SHA the review covers; "pending" until then. -->

## Blockers
<!-- What still blocks it and who must act; "none" if none. -->

## Status
<!-- PASS, FAIL or HOLD, as the first word. -->
