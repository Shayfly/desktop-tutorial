#!/usr/bin/env bash
# M4D.2 live-infrastructure runbook.
#
# Reproduces the environment tests/test_m4d2_live_postgres.py and
# tests/test_m4d2_live_fastapi_redis.py assume: a real, running PostgreSQL
# server with migrations 001-016 applied, a real running Redis server, and
# fastapi/psycopg/psycopg_pool/redis-py/rq importable.
#
# IN A NORMAL ENVIRONMENT (network access to PyPI): replace the whole
# "vendor via git clone" section below with:
#   pip install -r requirements-production.txt -r requirements-test.txt
# and skip PYTHONPATH entirely -- the git-clone vendoring here exists only
# because the sandbox this was written in has PyPI, the Debian package
# mirror, AND the Docker Hub registry all blocked by network policy
# (verified: pypi.org/files.pythonhosted.org -> 403 host_not_allowed;
# archive.ubuntu.com/security.ubuntu.com -> 403 at the package-download
# level even though apt-cache's local index resolves; registry-1.docker.io
# -> 403 Forbidden), while `git clone https://github.com/...` IS reachable.
# This script documents the real, working alternative path, not a fake one.
#
# Usage:
#   ./tools/m4d2_setup_live_infra.sh
#   PYTHONPATH=/tmp/m4d2_vendor M4D2_DATABASE_URL=postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test \
#     python3 -m unittest tests.test_m4d2_live_postgres -v
#   PYTHONPATH=/tmp/m4d2_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=redis://127.0.0.1:6379/0 \
#     python3 -m unittest tests.test_m4d2_live_fastapi_redis -v   # standalone process, see its own docstring
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="${M4D2_VENDOR_DIR:-/tmp/m4d2_vendor}"
DB_NAME="${M4D2_DB_NAME:-m4d2_test}"
DB_PASSWORD="${M4D2_DB_PASSWORD:-m4d2pass}"
PG_PORT="${M4D2_PG_PORT:-5432}"
REDIS_PORT="${M4D2_REDIS_PORT:-6379}"

echo "== 1. Start PostgreSQL (native cluster, no Docker needed) =="
if command -v pg_ctlcluster >/dev/null 2>&1; then
    pg_ctlcluster 16 main start || true
else
    echo "pg_ctlcluster not found -- start your own PostgreSQL 16+ server on port ${PG_PORT}" >&2
fi

echo "== 2. Start Redis =="
redis-server --daemonize yes --port "${REDIS_PORT}" --logfile /var/log/redis-server.log || true

echo "== 3. Create the M4D.2 test database and apply migrations =="
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '${DB_PASSWORD}';" 2>/dev/null || true
sudo -u postgres createdb "${DB_NAME}" 2>/dev/null || echo "  (database ${DB_NAME} already exists)"
export PGPASSWORD="${DB_PASSWORD}"
for f in "${REPO_ROOT}"/infra/postgres/*.sql; do
    psql -h 127.0.0.1 -p "${PG_PORT}" -U postgres -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "$f" >/dev/null
done
echo "  migrations 001-016 applied to ${DB_NAME}"

echo "== 4. Vendor fastapi/psycopg/psycopg_pool/redis-py/rq from their real upstream GitHub repos =="
mkdir -p "${VENDOR_DIR}"
clone_if_missing() {
    local url="$1" dest="$2"
    if [ ! -d "$dest/.git" ]; then
        git clone --depth 1 "$url" "$dest"
    fi
}
clone_if_missing https://github.com/psycopg/psycopg.git  /tmp/psycopg_src
clone_if_missing https://github.com/fastapi/fastapi.git  /tmp/fastapi_src
clone_if_missing https://github.com/redis/redis-py.git   /tmp/redis_py_src
clone_if_missing https://github.com/rq/rq.git            /tmp/rq_src

ln -sfn /tmp/fastapi_src/fastapi                "${VENDOR_DIR}/fastapi"
ln -sfn /tmp/redis_py_src/redis                 "${VENDOR_DIR}/redis"
ln -sfn /tmp/rq_src/rq                          "${VENDOR_DIR}/rq"
ln -sfn /tmp/psycopg_src/psycopg/psycopg        "${VENDOR_DIR}/psycopg"
ln -sfn /tmp/psycopg_src/psycopg_pool/psycopg_pool "${VENDOR_DIR}/psycopg_pool"

cat > "${VENDOR_DIR}/annotated_doc.py" <<'PYEOF'
"""Local shim for the `annotated-doc` PyPI package (PEP 727 `Doc()`
marker) -- see tests/test_m4d2_live_postgres.py's module docstring and
PATCH_APPLICATION_REPORT.md's M4D.2 section for why. Pure documentation
marker, zero effect on runtime behavior; typing_extensions (a real,
already-installed package) ships an identical class body."""
from typing_extensions import Doc

__all__ = ["Doc"]
PYEOF

echo "  vendor directory ready at ${VENDOR_DIR}"
echo
echo "== Verifying =="
PYTHONPATH="${VENDOR_DIR}" python3 -c "
import fastapi, psycopg, psycopg_pool, redis, rq
print('fastapi', fastapi.__version__)
print('psycopg_pool importable:', bool(psycopg_pool))
print('redis-py', redis.__version__)
print('rq', rq.__version__)
"
echo
echo "Done. Export PYTHONPATH=${VENDOR_DIR} and M4D2_DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@127.0.0.1:${PG_PORT}/${DB_NAME}"
echo "before running tests/test_m4d2_live_postgres.py and tests/test_m4d2_live_fastapi_redis.py."
