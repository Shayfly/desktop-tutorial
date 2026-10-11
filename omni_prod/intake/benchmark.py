"""Intake benchmark (Wave A §5.3): requirement-extraction quality per interpreter.

    python -m omni_prod.intake.benchmark                 # deterministic interpreter, free
    python -m omni_prod.intake.benchmark --model         # routed model, PAID: refused unless
                                                          # OMNI_INTAKE_BENCH_BUDGET_USD is set (founder approval)

Scores per case: field recall (expected fields extracted with the expected
value), precision (proposed values that are not wrong), hallucinations
(forbidden values proposed), family accuracy, delegate detection. Results for a
model are never presented as live verification of the product conversation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .interpreter import DeterministicInterpreter, ModelInterpreter

FIXTURES = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'intake' / 'cases.json'


def score(interpreter, cases) -> dict:
    rows, tp, fn, wrong, halluc, fam_ok, deleg_ok = [], 0, 0, 0, 0, 0, 0
    for c in cases:
        it = interpreter.interpret(c['message'])
        got = {p.field: p.value for p in it.proposals if p.field != 'goal'}
        hit = sum(1 for k, v in c['expected'].items() if got.get(k) == v)
        miss = len(c['expected']) - hit
        bad = sum(1 for k, v in got.items() if k in c['expected'] and c['expected'][k] != v)
        hal = sum(1 for k, v in c.get('forbidden', {}).items() if got.get(k) == v)
        tp, fn, wrong, halluc = tp + hit, fn + miss, wrong + bad, halluc + hal
        fam_ok += it.product_family == c['family']
        deleg_ok += it.delegate_rest == bool(c.get('delegate_rest'))
        rows.append({'id': c['id'], 'lang': c['lang'], 'recall': f'{hit}/{len(c["expected"])}', 'wrong': bad,
                     'hallucinated': hal, 'family': it.product_family, 'family_ok': it.product_family == c['family']})
    n = len(cases)
    return {'interpreter': getattr(interpreter, 'name', type(interpreter).__name__), 'cases': n,
            'field_recall': round(tp / max(tp + fn, 1), 3), 'wrong_values': wrong, 'hallucinations': halluc,
            'family_accuracy': round(fam_ok / max(n, 1), 3), 'delegate_accuracy': round(deleg_ok / max(n, 1), 3),
            'by_language': {lang: sum(1 for r in rows if r['lang'] == lang) for lang in ('he', 'en')}, 'rows': rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='omni_prod.intake.benchmark')
    ap.add_argument('--model', action='store_true')
    args = ap.parse_args(argv)
    cases = json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
    if args.model:
        if not os.getenv('OMNI_INTAKE_BENCH_BUDGET_USD'):
            print('refused: a model benchmark makes paid calls; set OMNI_INTAKE_BENCH_BUDGET_USD after founder approval')
            return 2
        from ..investor_app import _model_gateway_and_executor
        interp = ModelInterpreter(_model_gateway_and_executor()[0])
    else:
        interp = DeterministicInterpreter()
    print(json.dumps(score(interp, cases), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
