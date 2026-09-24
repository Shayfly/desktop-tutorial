# Omni Creator V23 — Local Prelaunch Demo

## Fast path

```bash
python -m pip install -r requirements-demo.txt
./scripts/run_prelaunch_demo.sh
```

Open: `http://127.0.0.1:8080`

The browser demo uses the **offline deterministic route** by default and does not claim arbitrary AI generation.

## Enable live autonomous AI build

Requirements:
1. Docker installed and the Omni sandbox image built.
2. An OpenAI-compatible local model endpoint such as vLLM/SGLang/Ollama gateway.
3. `OMNI_ENABLE_LIVE_BUILD=1`.
4. `OMNI_LOCAL_MODEL_URL` and `OMNI_LOCAL_MODEL_ID` configured.

Paid fallback stays blocked unless explicitly enabled by the existing V22 policy variables.

## Quality gate

```bash
python scripts/run_quality_gate.py
```
