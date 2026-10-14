#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for this gate." >&2
  exit 2
fi

docker compose -f docker-compose.production.yml up -d --build
trap 'docker compose -f docker-compose.production.yml down -v' EXIT INT TERM

# The env passed to the API/worker must point at compose services.
export OMNI_RUN_LIVE_INTEGRATION=1
python -m unittest discover -s tests/integration -v
