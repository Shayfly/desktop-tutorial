"""Skills as units (plan part A section 6, part B section 4; owner 2026-11-16: the first five, accessibility).

Each unit is a directory: manifest.json (input, output, kind, cost, gate, owner), probe.py (deterministic, no model:
`probe(html) -> {'status': 'pass'} | {'status': 'fail', 'code': ..., 'findings': [...]}`), fixtures/ok/,
fixtures/broken/ (with expected.json naming the code it must produce and what is broken), failure_codes.json (code ->
meaning, required fix). The acceptance check of a unit: its probe passes every ok fixture and fails every broken one
with the expected code. A probe that passes both is empty. A code the probe emits that failure_codes.json does not
declare is an error, not a silent pass.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_KEYS = ('name', 'input', 'output', 'kind', 'cost_usd', 'gate', 'owner', 'reads_source')


def units() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p / 'manifest.json').exists())


def manifest(unit: str) -> dict:
    data = json.loads((ROOT / unit / 'manifest.json').read_text(encoding='utf-8'))
    missing = [k for k in MANIFEST_KEYS if k not in data]
    if missing:
        raise ValueError(f'{unit}: manifest lacks {missing}')
    return data


def failure_codes(unit: str) -> dict:
    return json.loads((ROOT / unit / 'failure_codes.json').read_text(encoding='utf-8'))


def run(unit: str, html: str) -> dict:
    """Run one unit's probe; a code the unit does not declare raises."""
    result = importlib.import_module(f'{__name__}.{unit}.probe').probe(html)
    if result.get('status') not in ('pass', 'fail'):
        raise ValueError(f'{unit}: probe returned status {result.get("status")!r}')
    if result['status'] == 'fail' and result.get('code') not in failure_codes(unit):
        raise ValueError(f'{unit}: undeclared failure code {result.get("code")!r}')
    return result


def fixtures(unit: str, kind: str) -> list[tuple[str, str, dict]]:
    """(name, html, expected) for fixtures/<kind>/*.html; expected comes from fixtures/<kind>/expected.json."""
    d = ROOT / unit / 'fixtures' / kind
    expected = json.loads((d / 'expected.json').read_text(encoding='utf-8')) if (d / 'expected.json').exists() else {}
    return [(p.name, p.read_text(encoding='utf-8'), expected.get(p.name, {})) for p in sorted(d.glob('*.html'))]


# ---- shared static HTML helpers (no browser) ----------------------------------------------------------------------
import re

TAG = re.compile(r'<([a-zA-Z][\w-]*)\b([^>]*)>', re.S)
_ATTR = re.compile(r'([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'>]+)))?')


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in _ATTR.finditer(raw or ''):
        out[m.group(1).lower()] = next((g for g in m.groups()[1:] if g is not None), '')
    return out


def tags(html: str):
    for m in TAG.finditer(html or ''):
        yield m.start(), m.group(1).lower(), attrs(m.group(2))


_DROP = re.compile(r'<(script|style|template)\b[^>]*>.*?</\1\s*>', re.S | re.I)


def text_nodes(html: str) -> list[str]:
    """The visible text of a page, one string per text node (never joined across elements: a table's "שבת" cell and
    its "שבת סגור" cell are two nodes, not a repeated word)."""
    import html as _html
    body = _DROP.sub(' ', html or '')
    out = []
    for chunk in re.split(r'<[^>]+>', body):
        t = re.sub(r'\s+', ' ', _html.unescape(chunk)).strip()
        if t:
            out.append(t)
    return out
