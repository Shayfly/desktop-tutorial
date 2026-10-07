#!/usr/bin/env bash
# Writes infra/worker-host/.env for docker compose on the worker host.
#
# Input: the GitHub secret WORKER_ENV in the environment variable of the same
# name. Adds the host-generated sandbox secret (bootstrap.sh) and the model
# catalog when the secret does not set them. Shared by every workflow that runs
# docker compose on the host, so they all see the same configuration (compose
# refuses to start without OMNI_SANDBOX_SHARED_SECRET). Writes mode 600 and
# prints variable names only, never values.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
if [ -z "${WORKER_ENV:-}" ]; then echo "::error::GitHub secret WORKER_ENV is not set"; exit 1; fi
printf '%s\n' "$WORKER_ENV" | tr -d '\r' > .env
grep -q '^OMNI_SANDBOX_SHARED_SECRET=.' .env || echo "OMNI_SANDBOX_SHARED_SECRET=$(cat /etc/omni/sandbox_secret)" >> .env
if ! grep -q '^OMNI_MODEL_CATALOG_JSON=.' .env; then
  sed -i '/^OMNI_MODEL_CATALOG_JSON=/d' .env
  echo "OMNI_MODEL_CATALOG_JSON=$(python3 -c 'import json;print(json.dumps(json.load(open("model-catalog.json")),separators=(",",":")))')" >> .env
fi
echo "Configured variable names:"; cut -d= -f1 .env | grep -v '^#' | grep . | sort | tr '\n' ' '; echo
