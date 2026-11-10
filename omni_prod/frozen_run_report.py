"""Frozen-run report row from one build's evidence (docs/frozen-run-20261110.md, Michael 2026-11-10).

Pure: evidence in, one row out. `humanDecisions` and `humanCodeFixes` come from outside the build (the conversation
store and the git log) and are passed in.
"""
from __future__ import annotations

from datetime import datetime


def _ts(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


def report_row(*, arm: str, job: dict, evidence: dict, baseline_sha: str, pinned_models: set[str] | None = None,
               human_decisions: int = 0, human_code_fixes: int = 0) -> dict:
    gate = evidence.get('gate_waste') or {}
    quarantined = gate.get('quarantined_gates') or []
    reviews = (evidence.get('design_review') or {}).get('reviews') or []
    score = next((r.get('score') for r in reversed(reviews) if isinstance(r, dict) and r.get('score') is not None), None)
    answered = {e.get('model') or e.get('endpoint') for e in evidence.get('model_route_events') or []
                if isinstance(e, dict) and e.get('outcome') in ('ok', 'success', 'answered')}
    off_pin = sorted(m for m in answered if m and pinned_models is not None and m not in pinned_models)
    critical = any(q.get('critical') for q in quarantined)
    rounds = int(job.get('repair_rounds') or evidence.get('repair_rounds') or 0)
    started, finished = _ts(job.get('started_at')), _ts(job.get('finished_at'))
    cost = float(job.get('actual_provider_cost_usd') or evidence.get('provider_spend_usd') or 0)
    waste = float(gate.get('measured_usd') or 0)
    return {
        'arm': arm, 'build_id': job.get('id'), 'baselineSha': baseline_sha,
        'passed': job.get('status') == 'ready' and rounds == 0 and human_code_fixes == 0,
        'status': job.get('status'), 'rounds': rounds, 'codeChangingRounds': rounds,
        'gateWasteRounds': int(gate.get('rounds') or 0), 'gateWasteUsd': waste, 'costUsd': cost,
        'gateWasteShare': round(waste / cost, 4) if cost else 0.0,
        'humanCodeFixes': human_code_fixes, 'humanDecisions': human_decisions,
        'degraded': bool(critical or off_pin), 'offPinModels': off_pin,
        'quarantinedProbes': [q.get('probe') or q.get('skill') for q in quarantined],
        'timeToPreviewSec': int((finished - started).total_seconds()) if started and finished else None,
        'designScore': score,
        'canonHash': next((r.get('canon_hash') for r in reversed(evidence.get('product_review') or [])
                           if isinstance(r, dict) and r.get('canon_hash')), None),
    }
