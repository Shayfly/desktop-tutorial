#!/bin/bash
# scripts/test_fast.sh : the fast suite (tests/fast_suite.txt). Before every push; the full suite before every merge
# (the owner, 2026-11-15 22:50). 60 s hard bound; past the 30 s budget it FAILS with exit 3 (23:38/23:43: a failure,
# not a warning -- the fix is to drop files by re-measuring, never to raise the budget without a new measurement).
# Prints its elapsed time as a ::notice line and, on a budget failure, the ten slowest files as ::error lines.
set -euo pipefail
cd "$(dirname "$0")/.."
mapfile -t files < <(grep -vE '^\s*(#|$)' tests/fast_suite.txt)
[ "${#files[@]}" -gt 0 ] || { echo "::error title=test_fast::tests/fast_suite.txt lists no file"; exit 2; }
report=$(mktemp)
start=$(date +%s%N)
set +e
timeout 60 python3 -m pytest -q -p no:cacheprovider --junitxml="$report" "${files[@]}"
rc=$?
set -e
ms=$(( ($(date +%s%N) - start) / 1000000 ))
[ "$rc" = 124 ] && echo "::error title=test_fast::over the 60 s hard bound (${ms} ms): re-measure tests/fast_suite.txt"
echo "::notice title=test_fast::${#files[@]} files, exit ${rc}, ${ms} ms"
[ "$rc" = 0 ] || exit "$rc"
LIMIT_MS=${TEST_FAST_LIMIT_MS:-30000}
if [ "$ms" -gt "$LIMIT_MS" ]; then
  echo "::error title=test_fast::${ms} ms is over the ${LIMIT_MS} ms budget: drop files by re-measuring tests/fast_suite.txt"
  python3 scripts/test_fast_slowest.py "$report"
  exit 3
fi
