"""The behavioural acceptance plan verified in round 0 is a floor for every repair round (founder 2026-11-02 01:18,
direction b).

bld_96ab03c880f24b3a98065bf29eed11c3 and bld_99ea49dfc6c843aabc90bb8cccbcc1d7: in round 1 the repairer returned a
.omni/project.json without the "web_saas_acceptance" block (1063 B -> 341 B), and it stayed that way to the end. The
plan is what the behaviour check runs; a repair that removes a step (for example "POST a score of 2.9 -> 400") makes
the product easier to pass instead of fixing it.

A repair round may ADD steps, kinds or ids. When it removes or changes any step that was in the round-0 plan, drops a
required kind, or deletes the block, the round-0 block is put back -- the rest of the round's changes (code, tests,
the rest of the manifest) are kept -- and the repairer is told so on the next round (REPAIR_PLAN_WEAKENED).
"""
from __future__ import annotations

import json

PLAN_PATH = '.omni/project.json'
PLAN_KEY = 'web_saas_acceptance'
PLAN_WEAKENED_ID = 'REPAIR_PLAN_WEAKENED'


def _manifest(repository: dict[str, str]) -> dict | None:
    try:
        data = json.loads(repository.get(PLAN_PATH) or '')
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def plan_block(repository: dict[str, str]):
    """The plan block of a repository, or None (no manifest, unparseable, or no plan)."""
    data = _manifest(repository)
    block = data.get(PLAN_KEY) if data else None
    return block if isinstance(block, dict) else None


def _steps(block) -> list:
    out = []
    for persona in (block or {}).get('personas') or []:
        if isinstance(persona, dict):
            out.extend(s for s in persona.get('steps') or [] if isinstance(s, dict))
    return out


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def weakened(floor, candidate_block) -> list[str]:
    """What the candidate lost against the floor, as short labels ([] = nothing lost)."""
    if not floor:
        return []
    if not isinstance(candidate_block, dict):
        return ['the whole web_saas_acceptance block']
    lost = []
    have = {_canon(s) for s in _steps(candidate_block)}
    for step in _steps(floor):
        if _canon(step) not in have:
            lost.append(f"step {step.get('id', '?')} ({step.get('method', '')} {step.get('path', '')} -> "
                        f"{step.get('expect_status', '')})".replace('  ', ' '))
    kinds = set(candidate_block.get('required_kinds') or [])
    lost += [f'required kind {k}' for k in floor.get('required_kinds') or [] if k not in kinds]
    if floor.get('product_family') != candidate_block.get('product_family'):
        lost.append('product_family')
    return lost


def enforce(candidate: dict[str, str], floor, reference: dict[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    """Put the floor back if the candidate weakened it; returns (repository to verify, what was lost).
    `reference` is the repository the repair started from: when the restored manifest is the same document as its
    manifest, its exact text is used, so a repair that only cut the plan leaves the repository byte-identical (and
    the loop's fingerprint check stops it instead of paying for the same state again)."""
    lost = weakened(floor, plan_block(candidate))
    if not lost:
        return candidate, []
    data = _manifest(candidate)
    if data is None:
        return candidate, []      # no parseable manifest: the manifest checks fail the round on their own
    data[PLAN_KEY] = floor
    restored = dict(candidate)
    restored[PLAN_PATH] = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if reference is not None and _manifest(reference) == data:
        restored[PLAN_PATH] = reference[PLAN_PATH]
    return restored, lost


def note(lost: list[str]) -> dict:
    return {'acceptance_id': PLAN_WEAKENED_ID,
            'message': 'your previous change removed or weakened the behavioural acceptance plan '
                       f'({PLAN_PATH}, {PLAN_KEY}); the original plan was put back and the product is checked '
                       'against it. Do not remove or change its steps -- fix the application so it passes them',
            'evidence': 'removed or changed: ' + '; '.join(lost)[:600]}
