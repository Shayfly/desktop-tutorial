#!/usr/bin/env bash
set -euo pipefail
python -m uvicorn omni_prod.investor_app:app --host 127.0.0.1 --port "${OMNI_DEMO_PORT:-8080}"
