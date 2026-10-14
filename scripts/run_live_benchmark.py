#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni_prod.benchmark_suite import BenchmarkRunner, CASES
from omni_prod.investor_app import _live_engine

if os.getenv('OMNI_ENABLE_LIVE_BUILD') != '1':
    raise SystemExit('Set OMNI_ENABLE_LIVE_BUILD=1 after configuring Docker + local model.')

out = Path(os.getenv('OMNI_BENCHMARK_OUTPUT', 'BENCHMARK-LIVE.json'))
results = BenchmarkRunner(_live_engine).run(CASES)
BenchmarkRunner.write(out, results)
ready = sum(1 for r in results if r.status == 'ready')
print(json.dumps({'cases': len(results), 'ready': ready, 'output': str(out)}, indent=2))
raise SystemExit(0 if ready == len(results) else 2)
