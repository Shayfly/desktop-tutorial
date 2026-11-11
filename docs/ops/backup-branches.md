# Backup branches (Neon 148ai-db-v2)

Rule (Michael 2026-11-11): **a backup branch gets an expiry only after its milestone has been stable for 30 days.**
Until then it has none. Expiry is never set when the backup is made.

| Backup | Restore anchor for | Made | Expiry |
|---|---|---|---|
| `backup-before-live-core` | live_core (decision #232) | 2026-11-03 | none — removed 2026-11-11 (was 2026-11-17) |
| `backup-before-042` | migration 042 | 2026-11-04 | none — removed 2026-11-11 (was 2026-11-18) |
| `backup-before-cleanup-73-2026-11-11` | cleanup 73 | 2026-11-11 | none |

A backup branch is never named `preview/*`, so the preview-branch hygiene (`neon-preview-branches.yml`) never touches it
(tested: `tests/test_neon_preview_branches.py::test_main_and_backups_are_never_candidates`).

When a milestone has been stable for 30 days, set the expiry in a PR that updates this table.
