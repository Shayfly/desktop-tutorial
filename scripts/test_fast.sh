#!/bin/bash
# scripts/test_fast.sh : the fast suite (tests/fast_suite.txt): 60 s hard bound, fails past a 30 s budget (exit 3). Before every push; the full suite
# before every merge (the owner, 2026-11-15 22:50). Prints its own elapsed time as a ::notice line.
set -euo pipefail
cd "$(dirname "$0")/.."
mapfile -t files < <(grep -vE '^\s*(#|$)' tests/fast_suite.txt)
[ "${#files[@]}" -gt 0 ] || { echo "::error title=test_fast::tests/fast_suite.txt lists no file"; exit 2; }
start=$(date +%s%N)
set +e
timeout 60 python3 -m pytest -q -p no:cacheprovider "${files[@]}"
rc=$?
set -e
ms=$(( ($(date +%s%N) - start) / 1000000 ))
[ "$rc" = 124 ] && echo "::error title=test_fast::over the 60 s hard bound (${ms} ms): re-measure tests/fast_suite.txt"
echo "::notice title=test_fast::${#files[@]} files, exit ${rc}, ${ms} ms"
[ "$rc" = 0 ] || exit "$rc"
# the owner, 2026-11-15 23:38: past 30 s the fast suite stops saving time -- it fails, and the list is re-measured
LIMIT_MS=${TEST_FAST_LIMIT_MS:-30000}
if [ "$ms" -gt "$LIMIT_MS" ]; then
  echo "::error title=test_fast::${ms} ms is over the ${LIMIT_MS} ms budget: re-measure tests/fast_suite.txt"
  exit 3
fi
