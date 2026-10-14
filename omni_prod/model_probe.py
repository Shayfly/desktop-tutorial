"""One tiny real call to every configured catalog model.

Answers "is this provider connected, does this exact request shape work, what
did it cost" before a customer build depends on it (2026-10-08: OpenAI and
Anthropic were added to the catalog; Gemini's free quota had run out). Each
call asks for a one-word answer with a small output cap, so the worst case is
a fraction of a cent per model. Prints names, outcomes, token counts and the
metered cost only -- never keys.

    python -m omni_prod.model_probe
"""
from __future__ import annotations

import json
import sys
import time
from decimal import Decimal

from .model_catalog import load_model_catalog
from .model_gateway import OpenAICompatibleGateway

PROBE_MAX_TOKENS = 512  # reasoning models spend part of the cap on thinking


def probe(catalog=None, gateway_factory=OpenAICompatibleGateway) -> list[dict]:
    rows = []
    for model in catalog if catalog is not None else load_model_catalog():
        o = model.option
        row = {'name': model.endpoint.name if model.endpoint else o.model, 'model': o.model,
               'provider': o.provider, 'status': model.status}
        if model.endpoint is None:
            row['result'] = f'not configured ({model.api_key_env} is empty)'
            rows.append(row)
            continue
        gw = gateway_factory(model.endpoint)
        started = time.monotonic()
        try:
            answer = gw.complete(system='You are a connectivity check.', user='Reply with the single word OK.',
                                 max_tokens=min(PROBE_MAX_TOKENS, model.max_output_tokens))
            row['result'] = 'ok'
            row['answer'] = answer.strip()[:40]
        except Exception as exc:
            row['result'] = f'error: {exc}'[:300]
        row['seconds'] = round(time.monotonic() - started, 1)
        usage = getattr(gw, 'last_usage', None)
        if usage is not None and usage.input_tokens is not None and usage.output_tokens is not None:
            cost = (Decimal(usage.input_tokens) * o.input_per_million +
                    Decimal(usage.output_tokens) * o.output_per_million) / Decimal(1_000_000)
            row.update(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                       metered_cost_usd=str(cost.quantize(Decimal('0.000001'))))
        row['served_model'] = getattr(gw, 'last_response_model', None)
        rows.append(row)
    return rows


def main() -> int:
    rows = probe()
    print('MODEL-PROBE ' + json.dumps(rows, ensure_ascii=False))
    for r in rows:
        body = ' '.join(f'{k}={v}' for k, v in r.items() if k != 'name')
        print(f"::notice title={r['name']}::{body}".replace('\n', ' '))
    configured = [r for r in rows if r['status'] == 'CONFIGURED']
    return 0 if configured and all(r['result'] == 'ok' for r in configured) else 1


if __name__ == '__main__':
    sys.exit(main())
