"""Live vision probe (Michael 2026-11-15: vision first, then the live probe; Shai approved its cost).

Sends every model of the worker's real catalog (OMNI_MODEL_CATALOG_JSON, the routes builds use) two known pictures
drawn here -- a red circle and a blue triangle on white -- one call each, and asks for the shape and the colour as
JSON. A model passes only if it names both pictures correctly; one fixed guess cannot pass both. The answer, the
model and the verdict are printed per call as a GitHub annotation, and the run ends non-zero if a model listed in
omni_prod.vision_models (where image calls are routed) does not pass: that is a calibration finding to report, not
something to route around.

Bounded: 2 calls per model, at most MAX_MODELS models, max_tokens per call capped; each provider call has the
catalog's own timeout. It does not go through the router, on purpose: the router would send images only to the
models already listed, and the probe exists to test the others too.

    python -m omni_prod.vision_probe            # on the worker host (it holds the catalog and the keys)
"""
from __future__ import annotations

import json
import os
import struct
import sys
import zlib

MAX_MODELS = 12
MAX_TOKENS = 1200          # reasoning models count thinking tokens against the cap
SIZE = 128
PICTURES = {'red circle': ('circle', 'red'), 'blue triangle': ('triangle', 'blue')}
_RGB = {'red': (220, 30, 30), 'blue': (30, 60, 220)}
SYSTEM = ('You are shown one picture. Answer with a JSON object only: {"shape": "circle" | "square" | "triangle", '
          '"color": "red" | "green" | "blue"}. Describe the single coloured shape on the white background.')


def _inside(shape: str, x: int, y: int) -> bool:
    c = SIZE / 2
    if shape == 'circle':
        return (x - c) ** 2 + (y - c) ** 2 <= (SIZE * 0.35) ** 2
    if shape == 'triangle':                       # apex up, base at 80% height
        top, bottom = SIZE * 0.15, SIZE * 0.80
        if not top <= y <= bottom:
            return False
        half = (y - top) / (bottom - top) * SIZE * 0.40
        return abs(x - c) <= half
    raise ValueError(f'unknown shape {shape!r}')


def picture(name: str) -> bytes:
    """A PNG of the named picture (pure Python: the worker image needs no imaging library)."""
    shape, colour = PICTURES[name]
    fg, bg = _RGB[colour], (255, 255, 255)
    rows = b''.join(b'\x00' + b''.join(bytes(fg if _inside(shape, x, y) else bg) for x in range(SIZE))
                    for y in range(SIZE))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def _parse(text: str) -> dict:
    text = (text or '').strip()
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise ValueError('no JSON object in the answer')
    data = json.loads(text[start:end + 1])
    return {'shape': str(data.get('shape', '')).strip().lower(), 'color': str(data.get('color', '')).strip().lower()}


def probe_model(gateway, model: str) -> dict:
    """Two calls; returns {'model', 'passed', 'answers': [...]} -- never raises for a provider error (it is a result)."""
    answers, passed = [], True
    for name, (shape, colour) in PICTURES.items():
        row = {'picture': name}
        try:
            # temperature is left at the gateway's default: it already omits it where a provider refuses one
            seen = _parse(gateway.complete(system=SYSTEM, user='What is in this picture?', max_tokens=MAX_TOKENS,
                                           images=(picture(name),)))
            row.update(seen=seen, ok=(seen['shape'], seen['color']) == (shape, colour))
        except Exception as exc:                  # a refusal, a timeout or an unreadable answer is a failed probe
            row.update(error=f'{type(exc).__name__}: {exc}'[:300], ok=False)
        passed = passed and row['ok']
        answers.append(row)
    return {'model': model, 'passed': passed, 'answers': answers}


def run(catalog, gateway_factory) -> list[dict]:
    models = list(catalog)
    if not models:
        raise SystemExit('vision probe: the model catalog is empty (OMNI_MODEL_CATALOG_JSON) -- nothing was probed')
    if len(models) > MAX_MODELS:
        raise SystemExit(f'vision probe: {len(models)} models exceeds the bound {MAX_MODELS}')
    return [probe_model(gateway_factory(m.endpoint), m.endpoint.model) for m in models]


def report(results: list[dict], listed) -> int:
    for r in results:
        for a in r['answers']:
            said = a.get('seen') or a.get('error')
            print(f"::notice title=vision probe {r['model']}::{a['picture']} -> {json.dumps(said, ensure_ascii=False)} "
                  f"{'OK' if a['ok'] else 'WRONG'}")
        print(f"::notice title=vision probe {r['model']}::{'PASS' if r['passed'] else 'FAIL'} "
              f"({'routed for images' if r['model'] in listed else 'not routed for images'})")
    print('VISION_PROBE_JSON ' + json.dumps(results, ensure_ascii=False))
    broken = [r['model'] for r in results if r['model'] in listed and not r['passed']]
    for m in broken:
        print(f'::error title=vision probe calibration::{m} is routed for images but did not pass the probe')
    return 1 if broken else 0


def main() -> int:
    from .model_catalog import load_model_catalog
    from .model_gateway import OpenAICompatibleGateway
    from .vision_models import VISION_MODELS
    return report(run(load_model_catalog(os.environ), OpenAICompatibleGateway), set(VISION_MODELS))


if __name__ == '__main__':
    sys.exit(main())
