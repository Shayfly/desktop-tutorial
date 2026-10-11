"""Model lanes for intake turns (Issue #12).

  deterministic   LOW turns (greetings): no model, $0
  standard        MEDIUM / HIGH / RISKY: task class 'conversation', mandatory
                  quality floor 70 (unchanged global floor)
  low_risk        a cheaper sub-70 lane -- DISABLED. It may serve LOW turns only,
                  and only with a qualification record proving: a Hebrew
                  benchmark (>= 150 cases, >= 95 % accuracy, zero sensitive false
                  negatives), verified provider pricing, and no tool permissions.
                  No such record exists in this repository, so it never runs.

RISKY results require explicit customer confirmation for every material field
(the Supervisor keeps model proposals as pre-selected hints). Approvals and
builds never execute from chat text in any lane: they need the server-bound
approval (build_approvals, migration 030).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .complexity import HIGH, LOW, RISKY

DETERMINISTIC, STANDARD, LOW_RISK = 'deterministic', 'standard', 'low_risk'
QUALIFICATION_FILE = Path(__file__).resolve().parents[2] / 'docs' / 'evidence' / 'intake' / 'low_risk_lane_qualification.json'


def _load_qualification():
    path = Path(os.getenv('OMNI_INTAKE_LOW_RISK_QUALIFICATION', '') or QUALIFICATION_FILE)
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def low_risk_lane_qualified(qualification: dict | None = None) -> tuple[bool, str]:
    q = qualification if qualification is not None else _load_qualification()
    if not isinstance(q, dict):
        return False, 'no Hebrew benchmark qualification record'
    bench = q.get('hebrew_benchmark') or {}
    if not (isinstance(bench, dict) and int(bench.get('cases') or 0) >= 150 and
            float(bench.get('accuracy') or 0) >= 0.95 and bench.get('sensitive_false_negatives') == 0):
        return False, 'Hebrew benchmark below the qualification bar'
    if q.get('pricing_verified') is not True:
        return False, 'provider pricing not verified'
    if q.get('tool_permissions') != 'none':
        return False, 'lane must have no tool permissions'
    return True, 'qualified'


def choose(level: str, *, qualification: dict | None = None) -> dict:
    if level == LOW:
        ok, why = low_risk_lane_qualified(qualification)
        if ok:
            return {'lane': LOW_RISK, 'task': 'conversation_low_risk', 'reason': why}
        return {'lane': DETERMINISTIC, 'task': None, 'reason': 'greeting: no model needed (' + why + ')'}
    return {'lane': STANDARD, 'task': 'conversation', 'quality_floor': 70,
            'requires_explicit_confirmation': level == RISKY, 'flag_for_review': level in (HIGH, RISKY),
            'reason': f'{level}: standard lane, mandatory floor 70'}
