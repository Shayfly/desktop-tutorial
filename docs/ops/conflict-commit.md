# Commit a conflict resolution — `scripts/commit_resolved.sh`

The owner, 2026-11-15 22:17 / 22:24. The commit after a conflict resolution depends on **verification, not on the order of commands**. The trigger: in #393, a resolution step failed and the `commit` ran anyway, with conflict markers in `allowed-deletions.json`. Nothing was pushed.

## Usage

```bash
# after resolving every conflict in the worktree, instead of `git add` + `git commit`:
scripts/commit_resolved.sh <worktree>
```

The script runs with `set -euo pipefail`, checks, and only then runs `git add` and `git commit --no-edit`.

## Exit codes (reserved: no other script may use them with another meaning)

| code | meaning | commit? |
|---|---|---|
| 0 | every check passed; committed | yes |
| 2 | usage: no worktree given | no |
| 3 | a conflict marker is left. `^<<<<<<<` or `^>>>>>>>` anywhere; `^=======` only in a file that also has one of these (a lone `=======` is a markdown rule) | no |
| 4 | a changed `.json` file does not parse | no |
| 5 | paths are still unmerged in the index | no |

Each failure prints a `::error title=…::` line naming the file.

## Evidence (2026-11-15, a temporary repo with a real conflict)

- No argument: exit 2.
- Before resolution: exit 3 (`x.json` 3 lines, `r.md` 4 lines).
- `r.md` resolved with its `=======` rule kept, `x.json` still in conflict: exit 3, `x.json` only.
- Broken json: exit 4.
- Correct resolution: exit 0 and a commit.
- Mutation: the previous rule (`=======` anywhere) refuses a resolved `r.md` with exit 3; the current rule commits it.
- Exit 5 is **not tested**: after the script's own `git add`, no unmerged path is left in any case I could produce. It is kept as a last guard.
