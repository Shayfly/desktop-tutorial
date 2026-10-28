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
# Provider keys kept as their own GitHub secrets (OPENAI_API_KEY,
# ANTHROPIC_API_KEY, VENICE_API_KEY1): added when set and not already given by WORKER_ENV(_OVERRIDES).
for key_name in OPENAI_API_KEY ANTHROPIC_API_KEY VENICE_API_KEY1; do
  key_value="${!key_name:-}"
  if [ -n "$key_value" ] && ! grep -q "^${key_name}=." .env; then
    sed -i "/^${key_name}=/d" .env
    printf '%s=%s\n' "$key_name" "$key_value" >> .env
    echo "::notice title=provider keys::${key_name} added from its GitHub secret"
  elif [ -z "$key_value" ] && ! grep -q "^${key_name}=." .env; then
    echo "::notice title=provider keys::${key_name} not set; its catalog models stay NOT_CONFIGURED"
  fi
done
unset key_value
# The deployed commit (not a secret): stored with every stage result as its source commit.
sed -i '/^OMNI_SOURCE_COMMIT=/d' .env
echo "OMNI_SOURCE_COMMIT=${GITHUB_SHA:-unknown}" >> .env
grep -q '^OMNI_SANDBOX_SHARED_SECRET=.' .env || echo "OMNI_SANDBOX_SHARED_SECRET=$(cat /etc/omni/sandbox_secret)" >> .env
if ! grep -q '^OMNI_MODEL_CATALOG_JSON=.' .env; then
  sed -i '/^OMNI_MODEL_CATALOG_JSON=/d' .env
  echo "OMNI_MODEL_CATALOG_JSON=$(python3 -c 'import json;print(json.dumps(json.load(open("model-catalog.json")),separators=(",",":")))')" >> .env
fi
# Founder-only real-model intake. Turn on only for staging, and never override
# an explicit WORKER_ENV(_OVERRIDES) operator choice (e.g. OMNI_INTAKE_MODEL=0).
# This does not make any model call: durable Vercel intake reservations still
# enforce $0.005/message, $0.05/project, $0.15/day on the preview branch.
if grep -qx 'OMNI_ENV=staging' .env && ! grep -q '^OMNI_INTAKE_MODEL=' .env; then
  echo 'OMNI_INTAKE_MODEL=1' >> .env
  echo "::notice title=staging-intake::founder-only intake model enabled for the dedicated worker"
fi
# Which catalog models can route (names and key presence only, never values).
python3 - <<'PY' || true
import json
env = {}
for line in open(".env", encoding="utf-8"):
    if "=" in line and not line.startswith("#"):
        k, v = line.rstrip("\n").split("=", 1)
        env[k] = v
try:
    items = json.loads(env.get("OMNI_MODEL_CATALOG_JSON", "[]"))
    rows = [f"{i.get('name')}={'CONFIGURED' if env.get(i.get('api_key_env', ''), '').strip() else 'NOT_CONFIGURED'}" for i in items]
    print("::notice title=model catalog::" + " ".join(rows))
except Exception as exc:
    print(f"::warning title=model catalog::could not read the catalog: {type(exc).__name__}")
PY
# Preview edge defaults (non-secret). The public IP is the host's own egress
# address; sslip.io resolves <anything>.<ip-with-dashes>.sslip.io to it.
if ! grep -q '^OMNI_PREVIEW_HOST_SUFFIX=.' .env; then
  ip=$(curl -fsS --max-time 10 https://checkip.amazonaws.com | tr -d '[:space:]' || true)
  if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "OMNI_PREVIEW_HOST_SUFFIX=${ip//./-}.sslip.io" >> .env
  else
    echo "::warning title=preview::could not determine the public IP; previews stay unconfigured"
  fi
fi
suffix=$(sed -n 's/^OMNI_PREVIEW_HOST_SUFFIX=//p' .env | head -n 1)
grep -q '^OMNI_PREVIEW_RUNTIME_HOST=.' .env || echo "OMNI_PREVIEW_RUNTIME_HOST=$(hostname | tr -c 'A-Za-z0-9-\n' '-')" >> .env
if [ -n "$suffix" ] && ! grep -q '^PREVIEW_DOMAIN_TEMPLATE=.' .env; then
  echo "PREVIEW_DOMAIN_TEMPLATE=https://{preview_id}.${suffix}" >> .env
fi
# Non-secret build knobs, published with their values so a limit lower than a
# real build needs is visible in the deploy (rehearsal 2026-10-08 used 17 calls).
grep -q '^OMNI_EXTERNAL_CALLS_PER_BUILD=.' .env || echo "OMNI_EXTERNAL_CALLS_PER_BUILD=40" >> .env
knobs=$(grep -E '^(OMNI_EXTERNAL_CALLS_PER_BUILD|OMNI_EXTERNAL_BUDGET_USD|OMNI_MAX_REPAIR_ROUNDS|OMNI_MODEL_ROUTING|OMNI_MODEL_MIN_QUALITY|OMNI_MODEL_TASK_MIN_QUALITY|OMNI_ZERO_COST_MODE|OMNI_ALLOW_EXTERNAL_FALLBACK)=' .env | tr '\n' ' ')
echo "::notice title=build-knobs::${knobs:-none set}"
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
# C23 (founder 2026-10-20): secret LENGTHS block the deploy (they were warnings). Only lengths the code itself
# requires, and only for values known to pass today (storage-probe and sandbox-probe PASS in deploy 39472683855):
#   OMNI_S3_ACCESS_KEY / OMNI_S3_SECRET_KEY on an R2 endpoint: 32 / 64 characters (R2 credential format)
#   OMNI_SANDBOX_SHARED_SECRET: at least 32 (omni_prod/sandbox_service.py:52 refuses every run below that)
# Reported by name and length only; the value itself is never printed.
length_error() { echo "::error title=WORKER_ENV::$1"; problems=1; }
if grep -q '^OMNI_S3_ENDPOINT=.*r2\.cloudflarestorage\.com' .env; then
  ak=$(sed -n 's/^OMNI_S3_ACCESS_KEY=//p' .env | head -n 1); sk=$(sed -n 's/^OMNI_S3_SECRET_KEY=//p' .env | head -n 1)
  if [ "${#ak}" -ne 32 ]; then
    # Positions of characters that cannot be in a hex Access Key ID; the
    # character itself is shown only when it is punctuation (not secret).
    odd=$(python3 - "$ak" <<'PY'
import sys, string
v = sys.argv[1]
out = [f"{i+1}:{c if c in string.punctuation else 'letter' if c.isalpha() else 'other'}"
       for i, c in enumerate(v) if c not in "0123456789abcdef"]
print(", ".join(out) or "none (all hex)")
PY
)
    length_error "OMNI_S3_ACCESS_KEY has ${#ak} characters; an R2 Access Key ID has 32. Non-hex characters at positions: ${odd}."
  fi
  if [ "${#sk}" -ne 64 ]; then
    length_error "OMNI_S3_SECRET_KEY has ${#sk} characters; an R2 Secret Access Key has 64."
  fi
fi
sandbox_secret=$(sed -n 's/^OMNI_SANDBOX_SHARED_SECRET=//p' .env | head -n 1)
if [ "${#sandbox_secret}" -lt 32 ]; then
  length_error "OMNI_SANDBOX_SHARED_SECRET has ${#sandbox_secret} characters; the sandbox runner refuses every run below 32 (omni_prod/sandbox_service.py:52)."
fi
# OMNI_SECRET_KEY (founder 2026-10-20): preflight.py:38 requires >= 48, but its length on this worker is unknown, so it
# is DISCOVERED here first (name + length, a notice, never blocking). Once a deploy has shown it, it can join the
# blocking checks above without risking a deploy.
secret_key=$(sed -n 's/^OMNI_SECRET_KEY=//p' .env | head -n 1)
echo "::notice title=secret-lengths::OMNI_SECRET_KEY=${#secret_key} characters (preflight.py:38 requires >= 48; not blocking yet)"
unset ak sk sandbox_secret secret_key
if [ "$problems" -ne 0 ]; then
  echo "::error title=WORKER_ENV::fix the lines above in the GitHub secret WORKER_ENV, then run Deploy build worker again"
  exit 1
fi
