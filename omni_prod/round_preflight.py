"""Pre-flight before a verification round (founder decision 2026-10-19).

Three rehearsals in a row spent repair round 1 on a syntax error in a generated test file, and two spent a round on a
behaviour plan that did not cover every acceptance id. Both are visible by reading the files, without running anything.
Pre-flight finds them BEFORE the chain runs and asks the repairer for a narrow fix that may touch only the affected
files. That fix is not a repair round: the round counter does not move. If the cheap fix does not resolve it, the
repository goes to the chain unchanged-for-that-issue and the chain reports the failure as before (a real round): pre-flight
never hides a failure, it only tries to remove it first.

Every pre-flight action is a taxonomy record (layer 'preflight', failure_type 'preflight_syntax' |
'preflight_plan_coverage', was_repaired), so the budget it gives back is measurable.
"""
from __future__ import annotations

import json

PLAN_PATH = '.omni/project.json'
MAX_FIXES_PER_ISSUE = 1          # one narrow repairer call per issue per round; then the real round decides


def syntax_errors(repository: dict[str, str]) -> list[dict]:
    """Python files that do not compile and JSON files that do not parse (file, line, message)."""
    out = []
    for path in sorted(repository):
        text = repository[path]
        if not isinstance(text, str):
            continue
        if path.endswith('.py'):
            try:
                compile(text, path, 'exec', dont_inherit=True)
            except SyntaxError as exc:
                out.append({'file': path, 'line': exc.lineno or 0, 'message': f'Python syntax error: {exc.msg}'})
            except ValueError as exc:                       # e.g. a NUL byte
                out.append({'file': path, 'line': 0, 'message': f'Python source error: {exc}'})
        elif path.endswith('.json'):
            try:
                json.loads(text)
            except ValueError as exc:
                out.append({'file': path, 'line': getattr(exc, 'lineno', 0), 'message': f'JSON error: {exc}'[:200]})
    return out


def plan_coverage_gaps(repository: dict[str, str], spec) -> dict | None:
    """What the behaviour plan in .omni/project.json fails to cover, read statically (None = nothing to fix here).

    Only gaps that are a property of the PLAN: an acceptance id no step exercises, a required kind no step has, or a
    plan block that does not parse. Whether the app then passes those steps is the chain's job."""
    from .preview_runtime import NotPreviewable, parse_web_saas_acceptance_plan
    wanted = [a.id for a in getattr(spec, 'acceptance', ()) or ()]
    if PLAN_PATH not in repository or not wanted:
        return None
    try:
        plan = parse_web_saas_acceptance_plan(repository)
    except NotPreviewable as exc:
        return {'invalid': str(exc)[:300], 'missing_acceptance_ids': wanted, 'missing_kinds': []}
    except ValueError:
        return None                                         # the manifest itself is broken: syntax pre-flight's job
    if plan is None:
        return None                                         # no plan at all: the behaviour check explains what to add
    steps = [s for p in plan.personas for s in (p.get('steps') or []) if isinstance(s, dict)]
    covered = {a for s in steps for a in (s.get('acceptance_ids') or [])}
    kinds = {s.get('kind') for s in steps}
    missing_ids = [a for a in wanted if a not in covered]
    missing_kinds = [k for k in plan.required_kinds if k not in kinds]
    # The runner's OWN per-step validation (web_saas_acceptance._validate_plan), with the same acceptance ids the
    # behaviour check passes it (spec.acceptance). Paid run 39377332673: round 0 was rejected with "step S5 must
    # reference contract acceptance_ids" -- every id was covered by OTHER steps, so the coverage check above passed
    # and a defect visible by reading the file cost a full repair round, with no behaviour step run at all.
    from .web_saas_acceptance import _validate_plan
    invalid = _validate_plan(plan.personas, set(wanted))
    if not invalid and not missing_ids and not missing_kinds:
        return None
    return {'invalid': invalid, 'missing_acceptance_ids': missing_ids, 'missing_kinds': missing_kinds}


def syntax_failure(errors: list[dict]) -> dict:
    where = '; '.join(f"{e['file']}:{e['line']} {e['message']}" for e in errors[:6])
    return {'acceptance_id': 'CONSISTENCY', 'message': f'consistency (syntax): {where}',
            'evidence': 'Pre-flight (before any check runs): fix ONLY the syntax of the files named here so they '
                        'compile / parse. Do not change anything else.'}


def plan_failure(gaps: dict) -> dict:
    parts = []
    if gaps.get('invalid'):
        parts.append(f"the plan is invalid: {gaps['invalid']}")
    if gaps.get('missing_acceptance_ids'):
        parts.append('no step covers acceptance ids ' + ', '.join(gaps['missing_acceptance_ids']))
    if gaps.get('missing_kinds'):
        parts.append('no step of required kinds ' + ', '.join(gaps['missing_kinds']))
    return {'acceptance_id': 'BEHAVIOR', 'message': 'behavioural acceptance plan incomplete: ' + '; '.join(parts),
            'evidence': f'Pre-flight: fix ONLY the plan in {PLAN_PATH} (web_saas_acceptance.personas[].steps) so every '
                        'acceptance id and every required kind has at least one step that exercises it over HTTP. '
                        'Do not change the application.'}
