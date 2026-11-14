"""C31 — registry_lint: the registry (CONTROLS.json) enforces itself in CI (founder 2026-10-21).

    python tools/registry_lint.py CONTROLS.json [--base BASE_CONTROLS.json] [--today YYYY-MM-DD]

Exit 0 = clean, 1 = violations (each printed as ::error), 2 = the registry cannot be read.

Rules
  R1  every control declares its canary: `canary` (a non-empty list of test ids) OR `canary_pending` (a non-empty reason).
      Neither, or both, is a violation: a canary row cannot disappear silently.
  R2  every canary test id resolves: `path::Class::test` or `path::test`; the file exists and defines it (read with ast,
      never imported or run).
  R3  no overdue drill: a control of type `drill` (or a live control with its own `drill: "monthly: ..."`, C16) must have
      run within its frequency (weekly 7, monthly 31,
      quarterly 92 days), counted from its last `drills_run` entry, or from `adopted` if it never ran.
  R4  with --base (the registry on main): a control that has a canary on main must still have one here; replacing it with
      `canary_pending` is a removal, not a change.
  R5  control ids are unique.

BOUNDARY (written next to it in CONTROLS.json `c31_boundary`): this lint proves that a canary row exists and names an
existing test. It does NOT prove that the canary fails when the control breaks. That is the drill.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import sys
from pathlib import Path

PERIOD_DAYS = {'weekly': 7, 'monthly': 31, 'quarterly': 92}


def _test_exists(root: Path, test_id: str) -> str | None:
    """None when the test exists, else the reason."""
    parts = test_id.split('::')
    if len(parts) not in (2, 3):
        return f'malformed test id {test_id!r} (path::Class::test or path::test)'
    path = root / parts[0]
    if not path.is_file():
        return f'{parts[0]} does not exist'
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError as exc:
        return f'{parts[0]} does not parse: {exc.msg}'
    if len(parts) == 2:
        found = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[1] for n in tree.body)
        return None if found else f'{parts[0]} has no top-level test {parts[1]}'
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == parts[1]), None)
    if cls is None:
        return f'{parts[0]} has no class {parts[1]}'
    found = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[2] for n in cls.body)
    return None if found else f'{parts[0]}::{parts[1]} has no test {parts[2]}'


def lint(registry: dict, *, root: Path, base: dict | None = None, today: dt.date | None = None) -> list[str]:
    today = today or dt.date.today()
    errors: list[str] = []
    controls = registry.get('controls') or []
    ids = [c.get('id') for c in controls]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f'R5 {dup}: control id is not unique')
    for c in controls:
        cid = c.get('id')
        has_canary = 'canary' in c and c['canary'] is not None
        has_pending = 'canary_pending' in c and c['canary_pending'] is not None
        if has_canary == has_pending:
            errors.append(f'R1 {cid}: must declare exactly one of canary / canary_pending '
                          f'({"both" if has_canary else "neither"} present)')
        if has_canary:
            tests = c['canary']
            if not isinstance(tests, list) or not tests or not all(isinstance(t, str) and t for t in tests):
                errors.append(f'R1 {cid}: canary must be a non-empty list of test ids')
            else:
                for t in tests:
                    why = _test_exists(root, t)
                    if why:
                        errors.append(f'R2 {cid}: canary {t}: {why}')
        if has_pending and not (isinstance(c['canary_pending'], str) and c['canary_pending'].strip()):
            errors.append(f'R1 {cid}: canary_pending must give a reason')
    adopted = registry.get('adopted')
    runs = {}
    for r in registry.get('drills_run') or []:
        try:
            d = dt.date.fromisoformat(str(r.get('date')))
        except ValueError:
            errors.append(f'R3 {r.get("control")}: drills_run date {r.get("date")!r} is not YYYY-MM-DD')
            continue
        runs[r.get('control')] = max(d, runs.get(r.get('control'), d))
    for c in controls:
        if c.get('type') == 'drill':
            freq = str(c.get('frequency'))
        elif isinstance(c.get('drill'), str):          # a live control with its own scheduled drill (C16: "monthly: ...")
            freq = c['drill'].split(':', 1)[0].strip()
        else:
            continue
        period = PERIOD_DAYS.get(freq)
        if period is None:
            errors.append(f'R3 {c.get("id")}: drill frequency {freq!r} is not one of {sorted(PERIOD_DAYS)}')
            continue
        last = runs.get(c.get('id'))
        if last is None:
            try:
                last = dt.date.fromisoformat(str(adopted))
            except ValueError:
                errors.append(f'R3 {c.get("id")}: never run and the registry has no valid `adopted` date')
                continue
        due = last + dt.timedelta(days=period)
        if today > due:
            errors.append(f'R3 {c.get("id")}: drill overdue since {due.isoformat()} '
                          f'({freq}; last {"run" if c.get("id") in runs else "adopted"} {last.isoformat()})')
    if base:
        now = {c.get('id'): c for c in controls}
        for b in base.get('controls') or []:
            if b.get('canary') and not (now.get(b.get('id')) or {}).get('canary'):
                errors.append(f'R4 {b.get("id")}: has a canary on main and none here (canary row removed)')
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('registry')
    ap.add_argument('--base', help='the registry on main (R4)')
    ap.add_argument('--today', help='YYYY-MM-DD (tests); default: today')
    a = ap.parse_args(argv)
    path = Path(a.registry)
    try:
        registry = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(f'::error title=registry_lint::cannot read {path}: {exc}')
        return 2
    base = None
    if a.base:
        try:
            base = json.loads(Path(a.base).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            print(f'::notice title=registry_lint::no base registry at {a.base}: R4 skipped')
    today = dt.date.fromisoformat(a.today) if a.today else None
    errors = lint(registry, root=path.resolve().parent, base=base, today=today)
    for e in errors:
        print(f'::error title=registry_lint::{e}')
    n = len(registry.get('controls') or [])
    with_canary = sum(1 for c in registry.get('controls') or [] if c.get('canary'))
    print(f'registry_lint: {n} controls, {with_canary} with a canary, {len(errors)} violation(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
