#!/usr/bin/env bash
# M4D.2b dependency-parity runbook (directive item 2: "VERIFY EXACT
# PRODUCTION DEPENDENCY PARITY").
#
# tools/m4d2_setup_live_infra.sh vendored HEAD of each package's default
# branch. This script instead checks out the EXACT git tag/commit matching
# requirements-production.txt's pin for each package (or, where
# requirements-production.txt leaves a transitive dependency unpinned, the
# latest tag satisfying the pinning package's own declared constraint --
# what pip's resolver would pick absent a lock file). It builds a SEPARATE
# vendor directory (/tmp/m4d2b_vendor) so M4D.2's own evidence
# (/tmp/m4d2_vendor, HEAD-based) is left untouched and independently
# re-runnable.
#
# IN A NORMAL ENVIRONMENT (network access to PyPI): this whole script is
# unnecessary -- just `pip install -r requirements-production.txt`. This
# exists only because PyPI, the Debian package mirror, and Docker Hub are
# all confirmed blocked from this sandbox; see
# tools/m4d2_setup_live_infra.sh's own header for the exact verification,
# unchanged here.
#
# Exact pin -> source mapping (requirements-production.txt, 2026-09-22):
#   fastapi==0.128.2        -> github.com/fastapi/fastapi      tag 0.128.2
#   psycopg[binary,pool]
#     ==3.3.6                -> github.com/psycopg/psycopg      tag 3.3.6
#                                (psycopg_pool is a separate, independently
#                                versioned package in the SAME repo with no
#                                version pin inside psycopg's own [pool]
#                                extra -- pool-3.3.3 is simply the latest
#                                tag, i.e. what pip's resolver would pick)
#   redis==8.1.0             -> github.com/redis/redis-py       tag v8.1.0
#   rq==2.12.0                -> github.com/rq/rq                tag v2.12
#                                (NOTE: M4D.2's HEAD-based vendor was one
#                                commit past this tag -- a codeql-action CI
#                                bump, unrelated to rq's own source; see
#                                PATCH_APPLICATION_REPORT.md's M4D.2b
#                                section)
#   starlette (unpinned,      -> github.com/encode/starlette     tag 0.50.0
#     transitive via fastapi     (latest tag satisfying fastapi 0.128.2's
#     0.128.2's own              own pyproject.toml constraint
#     `starlette>=0.40.0,        `starlette>=0.40.0,<0.51.0`; the
#     <0.51.0`)                  pre-installed starlette 1.0.0 is OUTSIDE
#                                that range -- a real, disclosed
#                                non-parity finding this pass corrected)
#   pydantic==2.13.4          -> NOT vendored -- see "KNOWN GAP" below.
#
# KNOWN GAP (disclosed, not silently ignored): pydantic==2.13.4 requires
# pydantic-core==2.46.4 exactly (pydantic/pydantic's own pyproject.toml at
# tag v2.13.4). pydantic-core is a compiled Rust/PyO3 extension; building
# it needs `cargo` to fetch crate dependencies from crates.io /
# index.crates.io, which this sandbox's egress policy also blocks (403,
# confirmed via `curl -v https://index.crates.io/config.json`) -- the same
# class of block as PyPI/apt/Docker Hub, just a different host. rustc/cargo
# themselves ARE present in this sandbox, but with no reachable crate
# registry a real build is not possible here. The pre-installed pydantic
# 2.13.3 (paired with its own correctly-matching pydantic-core 2.46.3 --
# a real, internally consistent, already-installed release, not a
# mismatched hack) is used instead. This is a genuine, disclosed
# one-patch-version gap, not claimed as parity.
#
# uvicorn==0.48.0 and boto3==1.43.94 are pinned in requirements-production.txt
# but not exercised by any M4D.2/M4D.2b test: `fastapi.testclient.TestClient`
# drives the app directly over the ASGI transport, no live uvicorn server is
# needed for these tests, and boto3/S3 is out of scope (a disk-backed stand-in
# is used throughout -- see tests/test_m4d2_live_postgres.py's
# DiskArtifactStore docstring).
#
# Usage:
#   ./tools/m4d2b_setup_parity_infra.sh
#   PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test \
#     M4D2_REDIS_URL=redis://127.0.0.1:6379/0 python3 -m unittest tests.test_m4d2_live_postgres -v
#   (same PYTHONPATH/env for tests.test_m4d2_live_fastapi_redis and
#    tests.test_m4d2b_parity_and_worker -- each must run standalone, see
#    their own module docstrings)
set -euo pipefail

VENDOR_DIR="${M4D2B_VENDOR_DIR:-/tmp/m4d2b_vendor}"

clone_at_tag() {
    local url="$1" dest="$2" tag="$3"
    if [ ! -d "$dest/.git" ]; then
        git clone "$url" "$dest"
    fi
    ( cd "$dest" && git fetch --depth 1 origin "tag" "$tag" && git checkout "$tag" )
}

echo "== 1. Ensure the base M4D.2 sources are cloned (reused, not re-fetched) =="
clone_at_tag https://github.com/psycopg/psycopg.git  /tmp/psycopg_src        pool-3.3.3
clone_at_tag https://github.com/fastapi/fastapi.git  /tmp/fastapi_src       0.128.2
clone_at_tag https://github.com/redis/redis-py.git   /tmp/redis_py_src      v8.1.0
clone_at_tag https://github.com/rq/rq.git            /tmp/rq_src            v2.12
clone_at_tag https://github.com/encode/starlette.git /tmp/starlette_src     0.50.0

echo "== 2. psycopg core needs a SEPARATE worktree at 3.3.6 (psycopg and psycopg_pool =="
echo "==    are independently versioned packages in the same repo)                   =="
if [ ! -d /tmp/psycopg_src_3_3_6 ]; then
    ( cd /tmp/psycopg_src && git fetch --depth 1 origin tag 3.3.6 && git worktree add /tmp/psycopg_src_3_3_6 3.3.6 )
fi

echo "== 3. Build the parity vendor directory =="
mkdir -p "$VENDOR_DIR"
ln -sfn /tmp/fastapi_src/fastapi                     "$VENDOR_DIR/fastapi"
ln -sfn /tmp/starlette_src/starlette                  "$VENDOR_DIR/starlette"
ln -sfn /tmp/redis_py_src/redis                       "$VENDOR_DIR/redis"
ln -sfn /tmp/rq_src/rq                                "$VENDOR_DIR/rq"
ln -sfn /tmp/psycopg_src_3_3_6/psycopg/psycopg        "$VENDOR_DIR/psycopg"
ln -sfn /tmp/psycopg_src/psycopg_pool/psycopg_pool    "$VENDOR_DIR/psycopg_pool"
cat > "$VENDOR_DIR/annotated_doc.py" <<'PYEOF'
"""Local shim for the `annotated-doc` PyPI package -- identical to the one
in /tmp/m4d2_vendor; see tests/test_m4d2_live_postgres.py's module
docstring."""
from typing_extensions import Doc

__all__ = ["Doc"]
PYEOF

echo "== 4. Verify exact-parity versions import cleanly together =="
PYTHONPATH="$VENDOR_DIR" python3 -c "
import fastapi, starlette, psycopg, psycopg_pool, redis, rq, pydantic, pydantic_core
print('fastapi     ', fastapi.__version__, '(pin 0.128.2)')
print('starlette   ', starlette.__version__, '(latest compatible with fastapi\\'s <0.51.0)')
print('psycopg_pool', bool(psycopg_pool), '(pool-3.3.3, unpinned by psycopg[pool])')
print('redis-py    ', redis.__version__, '(pin 8.1.0)')
print('rq          ', rq.__version__, '(pin 2.12.0, exact tag v2.12)')
print('pydantic    ', pydantic.__version__, '(pin 2.13.4 -- KNOWN GAP, see script header)')
print('pydantic_core', pydantic_core.__version__, '(paired with installed pydantic)')
"
echo
echo "Done. Export PYTHONPATH=$VENDOR_DIR before running the M4D.2/M4D.2b test files."
