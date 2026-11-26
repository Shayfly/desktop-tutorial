<!-- The delivery report of the owner's plan (section 17). Every section below is required, once, and checked on each
push and each edit of this text (scripts/check_pr_report.py, the "PR report" workflow). Every piece of evidence refers
to the head SHA of this PR. Write "none" or "not measured" with the reason where a field has nothing; never leave it
empty. Text inside these comment marks is not shown and does not count. A GitHub revert with its generated body and a
dependabot pull request need no report. -->

## Task ID
<!-- The plan's task id(s), for example S1.7; the PR title names one of them. Outside the plan: "none: <the reason>"
(a hotfix, an owner's order, a warehouse item); the title then needs no id. -->

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
<!-- There is no independent reviewer: the owner cancelled that review on 2026-11-25 (OWNERS.md rule 1). Write who
reviewed the head SHA and how: Claude Code's own review by separate reviewer agents, what they checked, what they found
and what was fixed. Say that it is the author's own check, not an independent approval. -->

## Blockers
<!-- What still blocks it and who must act; "none" if none. -->

## Status
<!-- One of the three words first, then the reason, for example: "HOLD: waiting for CI on the head SHA". -->
