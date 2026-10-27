"""Provider probe (2026-10-28): does each provider ANSWER with the worker's own keys, right now?

"Configured" (a key is present) is not "working": a key on an account with no money is configured and dead. So each
model route makes ONE minimal real call (1-16 output tokens) -- the only way a no-credit account shows -- and prints
one ::notice PASS|FAIL with the HTTP status and the provider's short error code. Keys and error messages are never
printed. Worst-case spend for the whole probe: well under 0.01 USD.

Keys are read from the worker's deployed .env (WORKER_ENV + WORKER_ENV_OVERRIDES + provider-key GitHub secrets,
written by write-env.sh): GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, VENICE_API_KEY1, REPLICATE_API_TOKEN.
Models: every route in infra/worker-host/model-catalog.json, plus Venice's cheapest private model and Replicate's
account check (token validity only -- Replicate billing is NOT proven without a paid prediction, and says so).
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
TIMEOUT = 30


def load_env(path: pathlib.Path) -> dict:
    env = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v
    return env


def call(method, url, headers, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'Content-Type': 'application/json', 'User-Agent': '148AI-probe/1', **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read(1_000_000) or b'{}')
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read(65536) or b'{}')
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as exc:
        return None, {'error': {'type': type(exc).__name__}}


def code_of(payload) -> str:
    err = payload.get('error') if isinstance(payload, dict) else None
    if isinstance(err, dict):
        return str(err.get('code') or err.get('type') or err.get('status') or '')[:60]
    if isinstance(err, str):
        return err[:60] if len(err) < 60 else 'error'
    return str((payload or {}).get('type') or '')[:60] if isinstance(payload, dict) else ''


def report(name, ok, status, payload, extra=''):
    print(f"::notice title=provider-probe {name}::{'PASS' if ok else 'FAIL'} http={status} "
          f"code={code_of(payload) or '-'}{(' ' + extra) if extra else ''}", flush=True)
    return ok


def main() -> int:
    env = load_env(HERE / '.env')
    results = []
    catalog = json.loads((HERE / 'model-catalog.json').read_text(encoding='utf-8'))
    for m in catalog:
        provider, model, base = m.get('provider'), m.get('model'), str(m.get('base_url', '')).rstrip('/')
        key = (env.get(m.get('api_key_env') or '') or '').strip()
        name = f'{provider}/{model}'
        if not key:
            results.append(report(name, False, None, {}, f"{m.get('api_key_env')} not set on the worker"))
            continue
        if provider == 'anthropic':
            s, p = call('POST', base + '/messages', {'x-api-key': key, 'anthropic-version': '2023-06-01'},
                        {'model': model, 'max_tokens': 1, 'messages': [{'role': 'user', 'content': 'ok'}]})
        else:
            body = {'model': model, 'messages': [{'role': 'user', 'content': 'ok'}]}
            body['max_completion_tokens' if model.startswith('gpt-6') else 'max_tokens'] = 16
            s, p = call('POST', base + '/chat/completions', {'Authorization': 'Bearer ' + key}, body)
        results.append(report(name, s == 200, s, p))
    vk = (env.get('VENICE_API_KEY1') or '').strip()
    if not vk:
        results.append(report('venice', False, None, {}, 'VENICE_API_KEY1 not set on the worker'))
    else:
        s, p = call('GET', 'https://api.venice.ai/api/v1/models?type=text', {'Authorization': 'Bearer ' + vk})
        private = []
        for it in (p.get('data') or []) if s == 200 else []:
            spec = it.get('model_spec') or {}
            price = spec.get('pricing') or {}
            try:
                cost = float(price['input']['usd']) + float(price['output']['usd'])
            except Exception:
                continue
            if spec.get('privacy') == 'private':
                private.append((cost, it.get('id')))
        if not private:
            results.append(report('venice', False, s, p, 'no private priced model listed'))
        else:
            model = min(private)[1]
            s, p = call('POST', 'https://api.venice.ai/api/v1/chat/completions', {'Authorization': 'Bearer ' + vk},
                        {'model': model, 'max_tokens': 1, 'messages': [{'role': 'user', 'content': 'ok'}],
                         'venice_parameters': {'include_venice_system_prompt': False}})
            results.append(report(f'venice/{model}', s == 200, s, p))
    rt = (env.get('REPLICATE_API_TOKEN') or '').strip()
    if not rt:
        results.append(report('replicate', False, None, {}, 'REPLICATE_API_TOKEN not set on the worker'))
    else:
        s, p = call('GET', 'https://api.replicate.com/v1/account', {'Authorization': 'Bearer ' + rt})
        results.append(report('replicate/account', s == 200, s, p, 'token check only; billing NOT verified'))
    print(f"::notice title=provider-probe summary::{sum(results)} of {len(results)} answered", flush=True)
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
