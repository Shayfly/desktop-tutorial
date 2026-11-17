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
# The owner, 2026-11-16 (rule 4): a new gate enters at warn -- three builds, calibration, a proven fall on a broken page
# -- and only then blocks. CALIBRATING names the gates that have not finished that; each one warns by default, and its
# findings are in the log and in the build evidence of every build. Moving a gate to block = removing it from here,
# with the three builds as evidence. (HE Hebrew, G10 copy, G11 links, G1 empty blocks, BRAND brand name, SHARE preview,
# G5 rights: the source of every font, image and media file; A4: the asset plan's placement check, omni_prod/a4.)
# One gate per line, so adding a gate never rewrites another gate's line (a negative control that removes one gate
# must keep matching; tests/test_negative_controls_apply.py).
CALIBRATING = (
    'HE',        # Hebrew: grammar, gender, translationese
    'G10',       # copy: filler and placeholders
    'G11',       # links: tel, anchors, address
    'G1',        # empty blocks
    'BRAND',     # brand name
    'SHARE',     # share preview
    'G5',        # rights: the source of every font, image and media file
    'A4',        # the asset plan's placement check (omni_prod/a4)
    'G8',        # runtime and load (omni_prod/runtime_load)
    'GAME',      # a game plays (omni_prod/game_runtime)
)
DEFAULT_MODE = {'G3': 'block', 'G4': 'warn', 'G6': 'block', **{g: 'warn' for g in CALIBRATING}}
# Gates that read the page AS WRITTEN: the platform's own assets as their 148ai-asset:// placeholders, not as the
# bytes the engine's transform put in before the sandbox. G5 judges where an asset comes from, and the placeholder is
# the record of that; a raster data: URI left after the transform is put back is bytes the platform did not supply.
AS_WRITTEN = ('G5',)
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


def served_of(repository: dict[str, str]) -> list[tuple[str, str]]:
    """(path, text) of every file a browser loads or a server serves: what a unit with reads_served reads. A page
    is not only its <html> document -- a stylesheet, a script file and a fragment in a Python constant load assets
    too (an independent review, 2026-11-16: the rights units read whole documents only and passed the rest)."""
    from ..rights_sources import SERVED_EXT
    return [(path, text) for path, text in sorted(repository.items())
            if isinstance(text, str) and path.lower().endswith(SERVED_EXT)]


def check(gate: str, repository: dict[str, str]) -> dict:
    """{'status': 'pass'|'fail'|'NOT_RUN', 'failures': [{unit, page, code, findings}], 'checked': [...]}."""
    found = pages(repository)
    sources = sources_of(repository)
    served = served_of(repository)
    members = gate_units(gate)
    reads = {u: ('source' if manifest(u)['reads_source'] else 'served' if manifest(u).get('reads_served') else 'page')
             for u in members}
    targets = {'page': found, 'source': sources, 'served': served}
    if not any(targets[r] for r in reads.values()):
        return {'status': 'NOT_RUN', 'reason': 'no HTML page in the generated repository', 'failures': [], 'checked': []}
    failures, checked = [], []
    for unit in members:
        for path, html in targets[reads[unit]]:           # a source unit reads every text file, a served unit the served ones
            result = run(unit, html, path)
            checked.append(f'{unit} on {path}')
            if result['status'] == 'fail':
                failures.append({'unit': unit, 'page': path, 'code': result['code'],
                                 'findings': list(result.get('findings') or [])[:5]})
    return {'status': 'fail' if failures else 'pass', 'failures': failures, 'checked': checked}


class SkillGateExecutor:
    """block: the build is not accepted until every unit of the gate passes on every page. warn: the failures are
    recorded (last_gate, the log, the build evidence) and the build goes on."""

    def __init__(self, inner, gate: str, mode_: str = 'block', core=None):
        self._inner, self.gate, self.mode, self.last_gate = inner, gate, mode_, None
        self._core = core                                # the engine core: its transform gives the as-written view
        gate_units(gate)                                 # a gate with no unit raises at install, not mid-build

    def view(self, repository):
        """The repository this gate reads: as the sandbox got it, or as written for the AS_WRITTEN gates."""
        if self.gate not in AS_WRITTEN:
            return repository
        redact = getattr(getattr(self._core, 'repository_transform', None), 'redact', None)
        written = redact(repository) if callable(redact) else repository
        return written if isinstance(written, dict) else repository     # never a transform that invents its result

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from ..autonomous_core import AcceptanceFailure
        report = self._inner.execute(repository=repository, spec=spec)
        result = check(self.gate, self.view(repository))
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
    core.executor = SkillGateExecutor(core.executor, gate, m, core=core)
    return gate_units(gate)


# Every gate a build runs, in the order the worker installs them. One list: the rehearsal installs the same gates, so a
# calibration build cannot check less than a customer's build.
WORKER_GATES = ('G3', 'G4', 'G6', 'HE', 'G10', 'G11', 'G1', 'BRAND', 'SHARE', 'G5')
MAX_CALIBRATION_FINDINGS = 3      # per failure, in the evidence of a gate that is still calibrating
MAX_FINDING_CHARS = 200


def install_all(engine) -> dict:
    """Install every gate of WORKER_GATES; returns {gate: units}."""
    missing = [g for g in WORKER_GATES if g not in DEFAULT_MODE]
    if missing:
        raise ValueError(f'gates with no stated default mode: {missing}')
    return {g: install(engine, g) for g in WORKER_GATES}


def _calibration_findings(failure: dict) -> list[dict]:
    return [{'where': str(f.get('where', ''))[:MAX_FINDING_CHARS], 'why': str(f.get('why', ''))[:MAX_FINDING_CHARS]}
            for f in (failure.get('findings') or [])[:MAX_CALIBRATION_FINDINGS]]


def report(engine) -> dict:
    """What the build evidence carries: per gate its mode and its last result, OFF included. Codes only -- except a
    gate that is still CALIBRATING: its findings (bounded) are kept too, because calibrating a gate means reading
    what it flagged on real pages. G6 reads source files and is never in that list: a secret is never copied here."""
    core = getattr(engine, 'core', engine)
    modes = getattr(core, 'gate_modes', None)
    out = {g: {'mode': m} for g, m in modes.items()} if isinstance(modes, dict) else {}
    ex = getattr(core, 'executor', None)
    # Bounded: a wrapper chain is short. `_inner` is read from the instance's own __dict__ only, so an object that
    # invents attributes (a MagicMock) ends the walk. It walks THROUGH other wrappers too: the worker installs the
    # uploaded-image check and the asset-marker gate outside the skill gates (2026-11-16, a bug of mine: the walk
    # stopped at the first non-gate wrapper, and the evidence lost every gate's result when a photo was placed).
    for _ in range(MAX_CHAIN):
        if ex is None:
            break
        if isinstance(ex, SkillGateExecutor) and ex.gate in out and ex.last_gate is not None:
            keep = ex.gate in CALIBRATING and not any(manifest(u)['reads_source'] for u in gate_units(ex.gate))
            out[ex.gate].update(status=ex.last_gate['status'],
                                failures=[{**{k: f[k] for k in ('unit', 'page', 'code')},
                                           **({'findings': _calibration_findings(f)} if keep else {})}
                                          for f in ex.last_gate['failures']])
        ex = getattr(ex, '__dict__', {}).get('_inner')
    return out
