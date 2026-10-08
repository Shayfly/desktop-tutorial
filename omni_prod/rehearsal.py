"""Golden build rehearsal: the real generation pipeline, without customer state.

Runs exactly the engine a live build uses (`investor_app._live_components()`:
the configured model routes, the remote sandbox, dependency gate, preview
readiness incl. a real start of the app, quality-as-repair) on one prompt, then
the same quality gate the release uses. Writes nothing to the database, opens
no project, reserves no credits; the model gateway's own external budget
(OMNI_EXTERNAL_BUDGET_USD) bounds spend. Prints a compact JSON report.

Golden E2E #1 (2026-10-08): every failure so far was found by the founder
pressing "build" and sending a screenshot. This lets the platform's own
pipeline be exercised and iterated on directly.

    python -m omni_prod.rehearsal "<prompt>"
"""
from __future__ import annotations

import json
import sys
import time


def run(prompt: str) -> dict:
    from .investor_app import _live_components
    from .quality_gate import assess_repository
    from .worker_tasks import spend_snapshot
    started = time.monotonic()
    engine, gateway = _live_components()
    report: dict = {'prompt': prompt}
    try:
        result = engine.build(prompt)
    except Exception as exc:
        report.update(outcome='exception', error=f'{type(exc).__name__}: {exc}'[:1500])
        result = None
    if result is not None:
        quality = assess_repository(spec=result.spec, repository=result.repository)
        report.update(
            outcome=result.status, repair_rounds=result.repair_rounds,
            stop_reason=getattr(result, 'stop_reason', None),
            acceptance=[f'{a.id}: {a.text}' for a in result.spec.acceptance],
            files=sorted(result.repository)[:40],
            manifest=result.repository.get('.omni/project.json', '')[:800],
            failures=[{'id': f.acceptance_id, 'message': f.message[:300], 'evidence': (f.evidence or '')[-900:]}
                      for f in result.report.failures][:6],
            quality={'score': quality.score, 'passed': quality.passed, 'blockers': list(quality.blockers)},
            trace=getattr(engine, 'trace', [])[:8],
            review=[{'round': r.get('round'), 'enforced': r.get('enforced'), 'reviewer': r.get('reviewer'),
                     'model': r.get('model'), 'blocking': r.get('blocking'),
                     'findings': [f"{f['severity']}/{f['source']} {f['skill']}: {f['problem'][:160]}" for f in r.get('findings', [])][:8]}
                    for r in getattr(getattr(engine, 'executor', None), 'reviews', [])][:4],
        )
    spent, calls = spend_snapshot(gateway)
    report.update(model_calls=calls, authorized_spend_usd=str(spent), seconds=round(time.monotonic() - started))
    report.update(cost_projection(gateway))
    return report


def cost_projection(gateway) -> dict:
    """Measured tokens of this build and what the same tokens cost on every
    catalog model (list price; a different model would write a different
    number of tokens, so this is a price comparison, not a prediction)."""
    from decimal import Decimal
    tin = tout = 0
    by_model: dict[str, list[int]] = {}
    for rec in getattr(getattr(gateway, 'recorder', None), 'records', []) or []:
        i, o = getattr(rec, 'input_tokens', None), getattr(rec, 'output_tokens', None)
        if i is None or o is None:
            continue
        tin, tout = tin + i, tout + o
        agg = by_model.setdefault(rec.model or '?', [0, 0, 0])
        agg[0] += i; agg[1] += o; agg[2] += 1
    prices = {}
    for m in getattr(gateway, 'ranked', ()):
        opt = m.option
        prices[m.endpoint.name] = str(((Decimal(tin) * opt.input_per_million + Decimal(tout) * opt.output_per_million)
                                       / Decimal(1_000_000)).quantize(Decimal('0.0001')))
    return {'tokens': {'input': tin, 'output': tout, 'by_model': by_model}, 'same_tokens_cost_usd': prices}


def annotations(report: dict) -> list[str]:
    """GitHub notice lines (at most 10 per step are kept by GitHub)."""
    def note(title, body):
        body = str(body)[:3400].replace('%', '%25').replace('\r', '').replace('\n', '%0A')
        return f'::notice title={title}::{body}'
    q = report.get('quality') or {}
    lines = [note('outcome', f"{report.get('outcome')} rounds={report.get('repair_rounds')} stop={report.get('stop_reason')} "
                             f"quality={q.get('score')}/{'pass' if q.get('passed') else 'fail'} {q.get('blockers') or ''} "
                             f"calls={report.get('model_calls')} spend={report.get('authorized_spend_usd')} "
                             f"seconds={report.get('seconds')} {report.get('error', '')}"),
             note('acceptance', '\n'.join(report.get('acceptance') or [])),
             note('files', ', '.join(report.get('files') or []) + '\n' + (report.get('manifest') or ''))]
    if report.get('tokens'):
        lines.append(note('cost', f"tokens {json.dumps(report['tokens'])}\nsame tokens on each model (USD): "
                                  f"{json.dumps(report.get('same_tokens_cost_usd'))}"))
    if report.get('review'):
        lines.append(note('qa review', '\n'.join(
            f"round {r['round']} enforced={r['enforced']} reviewer={r['reviewer']} model={r['model']} blocking={r['blocking']}\n  "
            + '\n  '.join(r['findings']) for r in report['review'])))
    if report.get('trace'):
        lines.append(note('repair rounds', '\n'.join(
            f"round {t['round']}: failing {t['failing']} changed {t['changed']} :: {t['first_failure'][-500:]}"
            for t in report['trace'])))
    for i, f in enumerate((report.get('failures') or [])[:5]):
        lines.append(note(f"failure {i + 1} {f['id']}", f['message'] + '\n' + f['evidence']))
    return lines


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or not argv[0].strip():
        print('usage: python -m omni_prod.rehearsal "<prompt>"', file=sys.stderr)
        return 2
    report = run(argv[0])
    print('REHEARSAL ' + json.dumps(report, ensure_ascii=False))
    for line in annotations(report):
        print(line)
    return 0 if report.get('outcome') == 'ready' and report.get('quality', {}).get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
