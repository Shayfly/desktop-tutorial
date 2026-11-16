#!/bin/bash
# scripts/commit_resolved.sh WORKTREE : commit a conflict resolution ONLY when every check passes
# (the owner, 2026-11-15 22:17 / 22:24). Exit codes are documented in docs/ops/conflict-commit.md -- keep them there.
#   0  committed
#   2  usage (no WORKTREE)
#   3  a conflict marker is left: ^<<<<<<< or ^>>>>>>> anywhere; ^======= only in a file that also has one of those
#      (a lone ======= is a markdown rule, not a marker)
#   4  a changed .json file does not parse
#   5  paths are still unmerged in the index
# Any failure exits BEFORE `git commit`; nothing is committed on a failed check.
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: scripts/commit_resolved.sh WORKTREE"; exit 2; }
cd "$1"
files=$(git diff --name-only --diff-filter=U; git diff --cached --name-only)
markers=0
for f in $(printf '%s\n' $files | sort -u); do
  [ -f "$f" ] || continue
  n=$(grep -cE '^(<<<<<<<|>>>>>>>)( |$)' "$f" || true)
  if [ "$n" != "0" ]; then n=$((n + $(grep -cE '^=======$' "$f" || true))); fi   # ======= counts only beside <<< / >>>
  if [ "$n" != "0" ]; then echo "::error title=conflict marker::$f has $n marker line(s)"; markers=$((markers + n)); fi
done
[ "$markers" = "0" ] || { echo "refusing to commit: $markers conflict marker line(s)"; exit 3; }
for f in $(printf '%s\n' $files | sort -u | grep '\.json$' || true); do
  python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "$f" \
    || { echo "::error title=invalid json::$f"; exit 4; }
done
git add $(printf '%s\n' $files | sort -u)
[ -z "$(git diff --name-only --diff-filter=U)" ] || { echo "refusing to commit: unmerged paths remain"; exit 5; }
git commit -q --no-edit
echo "committed $(git log --oneline -1)"
