"""agent.plan_verifier -- the separate checker of Venice's plan (owner decision 2026-10-26).

It reads only the approved spec and the plan (data), never Venice's internals, and refuses a plan that
  * is not for the approved spec (fingerprint mismatch),
  * misses a requirement of the spec,
  * contains a requirement the spec does not have, or one without a source (NORTH_STAR 1),
  * changes a value the spec settled.
A plan the verifier refuses is not a plan the customer sees.
"""
from __future__ import annotations

from dataclasses import dataclass

_SOURCES = ('customer', 'delegated', 'implied', 'default')


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    problems: tuple[str, ...]


class PlanVerifier:
    agent = 'agent.plan_verifier'

    def verify(self, *, spec_fingerprint: str, spec_values: dict, plan: dict) -> Verdict:
        problems = []
        if plan.get('spec_fingerprint') != spec_fingerprint:
            problems.append('the plan is not for the approved spec (fingerprint mismatch)')
        items = plan.get('items') or []
        planned = {}
        for it in items:
            name = it.get('requirement')
            if not name:
                problems.append('a plan item names no requirement')
                continue
            if it.get('source') not in _SOURCES:
                problems.append(f'{name}: no source (stated, delegated, implied or default)')
            if name not in spec_values:
                problems.append(f'{name}: not in the approved spec')
            elif it.get('value') != spec_values[name]:
                problems.append(f'{name}: plan says {it.get("value")!r}, the spec says {spec_values[name]!r}')
            planned[name] = it
        for name in spec_values:
            if name not in planned:
                problems.append(f'{name}: required by the spec, missing from the plan')
        return Verdict(not problems, tuple(problems))
