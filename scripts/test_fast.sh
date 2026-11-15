#!/bin/bash
# scripts/test_fast.sh : the fast suite (tests/fast_suite.txt), bounded at 60 s. Before every push; the full suite
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
[ "$rc" = 124 ] && echo "::error title=test_fast::over the 60 s bound (${ms} ms): re-measure tests/fast_suite.txt"
echo "::notice title=test_fast::${#files[@]} files, exit ${rc}, ${ms} ms"
exit "$rc"
