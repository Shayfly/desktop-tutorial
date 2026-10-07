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
# Optional second secret WORKER_ENV_OVERRIDES: KEY=VALUE lines that replace the
# same keys from WORKER_ENV, so one value can be corrected without re-pasting
# the whole secret (GitHub secrets cannot be read back).
if [ -n "${WORKER_ENV_OVERRIDES:-}" ]; then
  overridden=""
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue;; esac
    name=${line%%=*}
    if ! [[ "$name" =~ ^[A-Z][A-Z0-9_]*$ ]] || [ "$name" = "$line" ]; then
      echo "::error title=WORKER_ENV_OVERRIDES::every line must be NAME=value with an upper-case NAME"; exit 1
    fi
    sed -i "/^${name}=/d" .env
    printf '%s\n' "$line" >> .env
    overridden="$overridden $name"
  done < <(printf '%s\n' "$WORKER_ENV_OVERRIDES" | tr -d '\r')
  echo "::notice title=WORKER_ENV_OVERRIDES::applied names:${overridden:- none}"
else
  echo "::notice title=WORKER_ENV_OVERRIDES::not set (empty), using WORKER_ENV only"
fi
grep -q '^OMNI_SANDBOX_SHARED_SECRET=.' .env || echo "OMNI_SANDBOX_SHARED_SECRET=$(cat /etc/omni/sandbox_secret)" >> .env
if ! grep -q '^OMNI_MODEL_CATALOG_JSON=.' .env; then
  sed -i '/^OMNI_MODEL_CATALOG_JSON=/d' .env
  echo "OMNI_MODEL_CATALOG_JSON=$(python3 -c 'import json;print(json.dumps(json.load(open("model-catalog.json")),separators=(",",":")))')" >> .env
fi
echo "Configured variable names:"; cut -d= -f1 .env | grep -v '^#' | grep . | sort | tr '\n' ' '; echo

# Shape checks, reported by variable NAME and length only (never values).
# Golden E2E #1 (2026-10-07): a build passed generation and sandbox
# verification and then failed at the very end on R2 with "Credential access
# key has length 34, should be 32" -- a pasted value had extra characters.
problems=0
while IFS= read -r line; do
  case "$line" in ''|'#'*) continue;; esac
  name=${line%%=*}; value=${line#*=}
  if [[ "$value" =~ ^[[:space:]] || "$value" =~ [[:space:]]$ ]]; then
    echo "::error title=WORKER_ENV::${name} has spaces before or after the value"; problems=1
  fi
  if [[ "$value" =~ ^[\"\'] || "$value" =~ [\"\']$ ]]; then
    echo "::error title=WORKER_ENV::${name} is wrapped in quotes; paste the value without quotes"; problems=1
  fi
  if printf '%s' "$value" | LC_ALL=C grep -q '[^ -~]'; then
    echo "::error title=WORKER_ENV::${name} contains invisible or non-ASCII characters (often copied from a web page); type or re-copy the value"; problems=1
  fi
done < .env
if grep -q '^OMNI_S3_ENDPOINT=.*r2\.cloudflarestorage\.com' .env; then
  ak=$(sed -n 's/^OMNI_S3_ACCESS_KEY=//p' .env | head -n 1); sk=$(sed -n 's/^OMNI_S3_SECRET_KEY=//p' .env | head -n 1)
  if [ "${#ak}" -ne 32 ]; then
    echo "::error title=WORKER_ENV::OMNI_S3_ACCESS_KEY has ${#ak} characters; a Cloudflare R2 Access Key ID has 32"; problems=1
  fi
  if [ "${#sk}" -ne 64 ]; then
    echo "::error title=WORKER_ENV::OMNI_S3_SECRET_KEY has ${#sk} characters; a Cloudflare R2 Secret Access Key has 64"; problems=1
  fi
fi
if [ "$problems" -ne 0 ]; then
  echo "::error title=WORKER_ENV::fix the lines above in the GitHub secret WORKER_ENV, then run Deploy build worker again"
  exit 1
fi
