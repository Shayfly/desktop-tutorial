#!/usr/bin/env sh
set -eu

export OMNI_RUN_LIVE_INTEGRATION=1
python -m unittest discover -s tests/integration -v
