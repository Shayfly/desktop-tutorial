# Local model setup contract

Omni V23 does not hard-code a vendor. It expects an OpenAI-compatible `/v1/chat/completions` endpoint.

Configure:

```bash
export OMNI_LOCAL_MODEL_URL=http://127.0.0.1:8001/v1
export OMNI_LOCAL_MODEL_ID=<your-model-id>
export OMNI_ZERO_COST_MODE=1
export OMNI_ENABLE_LIVE_BUILD=1
```

Then run the Control Center and use `/api/live/build`.

Recommended evaluation order:
1. Start with an open-weight coding model that fits available GPU memory.
2. Keep Zero-Cost Mode enabled until local success rate is measured.
3. Only then configure paid fallback with a strict per-build budget.
4. Run `scripts/run_live_benchmark.py` and retain the generated benchmark JSON as diligence evidence.

The package intentionally does not claim a specific model is already running because no GPU/model server is available in the current build environment.
