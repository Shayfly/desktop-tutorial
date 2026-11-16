"""The gates as skill units (plan part A section 7; owner 2026-11-16: wire the five accessibility units into G3).

A gate is every unit whose manifest names it (`"gate": "G3"`). The gate wraps the engine's executor: after the sandbox
run, each unit's probe runs on every page of the generated repository, and a failing probe fails the build -- its
code and findings go to the repair round as an acceptance failure (`gate-G3-<unit>`), like any other failed check.

Pages: a .html/.htm file, or a whole HTML document inside a .py/.jinja/.j2 file (the generated sites serve their page
from app.py, e.g. HTML_CONTENT). A unit whose manifest says reads_source (the secrets units, G6) reads every text file. A build with no page at all is NOT_RUN, said in the log and in `last_gate`; never a
silent pass.

The switch is OMNI_GATE_<gate>: "1" (default, the owner's order) blocks, "0" turns the gate off (said in the log);
any other value raises.
"""
from __future__ import annotations

import logging
from dataclasses import replace
import os
import re

from . import manifest, run, units

_DOC = re.compile(r'(?:<!doctype html[^>]*>\s*)?<html\b.*?</html\s*>', re.S | re.I)
_LOG = logging.getLogger(__name__)


def gate_units(gate: str) -> list[str]:
    found = [u for u in units() if manifest(u)['gate'] == gate]
    if not found:
        raise ValueError(f'no skill unit belongs to gate {gate!r}')
    return found


def pages(repository: dict[str, str]) -> list[tuple[str, str]]:
    """(path, html) of every page in a generated repository, in path order."""
    out = []
    for path, text in sorted(repository.items()):
        if not isinstance(text, str):
            continue
        if path.endswith(('.html', '.htm')):
            out.append((path, text))
        elif path.endswith(('.py', '.jinja', '.j2')):
            out.extend((f'{path}#{i + 1}', m.group()) for i, m in enumerate(_DOC.finditer(text)))
    return out


def sources_of(repository: dict[str, str]) -> list[tuple[str, str]]:
    """(path, text) of every text file of a generated repository: what a unit with reads_source reads."""
    return [(path, text) for path, text in sorted(repository.items()) if isinstance(text, str)]


def enabled(gate: str) -> bool:
    raw = os.environ.get(f'OMNI_GATE_{gate}', '1').strip()
    if raw not in ('0', '1'):
        raise ValueError(f"OMNI_GATE_{gate} must be '0' or '1', not {raw!r}")
    return raw == '1'


def check(gate: str, repository: dict[str, str]) -> dict:
    """{'status': 'pass'|'fail'|'NOT_RUN', 'failures': [{unit, page, code, findings}], 'checked': [...]}."""
    found = pages(repository)
    sources = sources_of(repository)
    members = gate_units(gate)
    reads_source = {u: bool(manifest(u)['reads_source']) for u in members}
    if not found and not any(reads_source.values()):
        return {'status': 'NOT_RUN', 'reason': 'no HTML page in the generated repository', 'failures': [], 'checked': []}
    failures, checked = [], []
    for unit in members:
        for path, html in (sources if reads_source[unit] else found):   # a source unit reads every text file
            result = run(unit, html)
            checked.append(f'{unit} on {path}')
            if result['status'] == 'fail':
                failures.append({'unit': unit, 'page': path, 'code': result['code'],
                                 'findings': list(result.get('findings') or [])[:5]})
    return {'status': 'fail' if failures else 'pass', 'failures': failures, 'checked': checked}


class SkillGateExecutor:
    """The build is not accepted until every unit of the gate passes on every page."""

    def __init__(self, inner, gate: str):
        self._inner, self.gate, self.last_gate = inner, gate, None
        gate_units(gate)                                 # a gate with no unit raises at install, not mid-build

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from ..autonomous_core import AcceptanceFailure
        report = self._inner.execute(repository=repository, spec=spec)
        result = check(self.gate, repository)
        self.last_gate = result
        if result['status'] == 'NOT_RUN':
            _LOG.warning('GATE_NOT_RUN gate=%s %s', self.gate, result['reason'])
            return report
        if result['status'] == 'pass':
            return report
        problems = tuple(AcceptanceFailure(
            f"gate-{self.gate}-{f['unit']}",
            f"{f['code']} ({manifest(f['unit'])['name']}) on {f['page']}: " + '; '.join(map(str, f['findings'])))
            for f in result['failures'])
        return replace(report, passed=False, failures=tuple(report.failures) + problems)


def install(engine, gate: str) -> list[str]:
    """Wrap the engine's executor with the gate; returns the units it runs ([] when switched off, said in the log)."""
    if not enabled(gate):
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s=0)', gate, gate)
        return []
    core = getattr(engine, 'core', engine)
    core.executor = SkillGateExecutor(core.executor, gate)
    return gate_units(gate)
