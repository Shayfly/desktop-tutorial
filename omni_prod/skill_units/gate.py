"""The gates as skill units (plan part A section 7; owner 2026-11-16: wire the five accessibility units into G3).

A gate is every unit whose manifest names it (`"gate": "G3"`). The gate wraps the engine's executor: after the sandbox
run, each unit's probe runs on every page of the generated repository, and a failing probe fails the build -- its
code and findings go to the repair round as an acceptance failure (`gate-G3-<unit>`), like any other failed check.

Pages: a .html/.htm file, or a whole HTML document inside a .py/.jinja/.j2 file (the generated sites serve their page
from app.py, e.g. HTML_CONTENT). A unit whose manifest says reads_source (the secrets units, G6) reads every text file. A build with no page at all is NOT_RUN, said in the log and in `last_gate`; never a
silent pass.

The switch is OMNI_GATE_<gate>: block | warn | off ("1" = block, "0" = off); any other value raises. Defaults: G3 and
G6 block, G4 warns until warehouse 114 is fixed. The mode of every gate, OFF included, is said in the log and written
to the build evidence on every build.
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


MODES = ('block', 'warn', 'off')
MAX_CHAIN = 20           # the longest executor wrapper chain report() walks
# owner 2026-11-16: G4 warns (a unit that warns makes it a gate; without the unit it is a heading) until warehouse 114
# (the hero image inlined as base64) is fixed; G3 and G6 block.
DEFAULT_MODE = {'G3': 'block', 'G4': 'warn', 'G6': 'block', 'HE': 'block', 'G10': 'block', 'G11': 'block',
                'G1': 'block', 'BRAND': 'block', 'SHARE': 'block'}   # HE Hebrew, G10 copy, G11 links, G1 empty blocks
_ALIASES = {'1': 'block', '0': 'off'}


def mode(gate: str) -> str:
    """OMNI_GATE_<gate>: block | warn | off ('1' = block, '0' = off). Any other value raises; no silent default."""
    raw = os.environ.get(f'OMNI_GATE_{gate}', DEFAULT_MODE.get(gate, 'block')).strip().lower()
    value = _ALIASES.get(raw, raw)
    if value not in MODES:
        raise ValueError(f"OMNI_GATE_{gate} must be one of {MODES} (or '1'/'0'), not {raw!r}")
    return value


def enabled(gate: str) -> bool:
    return mode(gate) != 'off'


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
    """block: the build is not accepted until every unit of the gate passes on every page. warn: the failures are
    recorded (last_gate, the log, the build evidence) and the build goes on."""

    def __init__(self, inner, gate: str, mode_: str = 'block'):
        self._inner, self.gate, self.mode, self.last_gate = inner, gate, mode_, None
        gate_units(gate)                                 # a gate with no unit raises at install, not mid-build

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from ..autonomous_core import AcceptanceFailure
        report = self._inner.execute(repository=repository, spec=spec)
        result = check(self.gate, repository)
        self.last_gate = {**result, 'mode': self.mode}
        if result['status'] == 'NOT_RUN':
            _LOG.warning('GATE_NOT_RUN gate=%s %s', self.gate, result['reason'])
            return report
        if result['status'] == 'pass':
            return report
        if self.mode == 'warn':
            _LOG.warning('GATE_WARN gate=%s %s', self.gate,
                         '; '.join(f"{f['unit']}:{f['code']}@{f['page']}" for f in result['failures']))
            return report
        problems = tuple(AcceptanceFailure(
            f"gate-{self.gate}-{f['unit']}",
            f"{f['code']} ({manifest(f['unit'])['name']}) on {f['page']}: " + '; '.join(map(str, f['findings'])))
            for f in result['failures'])
        return replace(report, passed=False, failures=tuple(report.failures) + problems)


def install(engine, gate: str) -> list[str]:
    """Wrap the engine's executor with the gate; returns the units it runs ([] when off). The gate's mode is written to
    the engine (`gate_modes`) and said in the log on EVERY build -- a gate switched off in silence is a forgotten gate
    (owner 2026-11-16)."""
    core = getattr(engine, 'core', engine)
    m = mode(gate)
    modes = dict(getattr(core, 'gate_modes', None) or {})
    modes[gate] = m
    core.gate_modes = modes
    if m == 'off':
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s): this build is NOT checked by %s', gate, gate, gate)
        return []
    _LOG.info('GATE_ON gate=%s mode=%s', gate, m)
    core.executor = SkillGateExecutor(core.executor, gate, m)
    return gate_units(gate)


def report(engine) -> dict:
    """What the build evidence carries: per gate its mode and its last result (codes only), OFF included."""
    core = getattr(engine, 'core', engine)
    modes = getattr(core, 'gate_modes', None)
    out = {g: {'mode': m} for g, m in modes.items()} if isinstance(modes, dict) else {}
    ex = getattr(core, 'executor', None)
    for _ in range(MAX_CHAIN):     # bounded: a wrapper chain is short; never follow an object that invents attributes
        if not isinstance(ex, SkillGateExecutor):
            break
        if ex.gate in out and ex.last_gate is not None:
            out[ex.gate].update(status=ex.last_gate['status'],
                                failures=[{k: f[k] for k in ('unit', 'page', 'code')} for f in ex.last_gate['failures']])
        ex = vars(ex).get('_inner')
    return out
