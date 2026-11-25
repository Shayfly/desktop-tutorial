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
from ..behavior_acceptance import MAX_CHAIN      # one bound for every chain walk (it was 20 here; see find_in_chain)
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
    'G11',       # links: tel, anchors, address
    'BRAND',     # brand name
    'SHARE',     # share preview
    'A4',        # the asset plan's placement check (omni_prod/a4)
    'G8',        # runtime and load (omni_prod/runtime_load)
    'GAME',      # a game plays (omni_prod/game_runtime)
    'APPLE',     # the design gate: contract, refusal list, render, two reviewers (omni_prod/g_apple)
    'PRO',       # professional minimum of a business site (skill_units/design_minimum; owner 2026-11-19)
    'SITE_CLAIMS',   # content route: a superlative no fact supports, in the model's copy (omni_prod/site_content)
    'SITE_PARITY',   # content route: the served page is the rendered page, and the only page (omni_prod/site_content)
    'APP_STATES',    # an app's data screens: loading, empty, error; no stack trace to the customer (omni_prod/app_states)
)
# Calibrated 2026-11-19 on the five builds that carry gate evidence (bld_a875456f, bld_77899122, bld_a9643012,
# bld_d36b3b4e, bld_b0de74d5): G1, G10 and G5 passed all five, and each unit's broken fixture proves the fall on a
# broken page -- they left CALIBRATING and block (STATUS.md, 2026-11-19).
CALIBRATED = ('G1', 'G10', 'G5')
DEFAULT_MODE = {'G3': 'block', 'G4': 'warn', 'G6': 'block', **{g: 'block' for g in CALIBRATED},
                **{g: 'warn' for g in CALIBRATING}}
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
    from ..repair_contracts import _TEST_FILE
    # Production 2026-11-19 (bld_59236dc6, the owner's law-firm site): G5, blocking since #468, failed the build on
    # tests/test_cohen_law.py -- a test the builder wrote, never served -- and no repair could clear it (three rounds,
    # no_progress_repository_unchanged, $0.90). A test file is not loaded by a browser or served.
    return [(path, text) for path, text in sorted(repository.items())
            if isinstance(text, str) and path.lower().endswith(SERVED_EXT) and not _TEST_FILE.search(path)]


SERVED_PAGE_LIMIT = 44_000        # the preview smoke returns at most 45,000 characters of GET /; a longer page is cut
_TEMPLATE_FIELD = re.compile(r'\{[A-Za-z_][^{}\n]{0,80}\}')


def served_copy(found: list[tuple[str, str]], rendered) -> list[tuple[str, str]]:
    """Calibration, 2026-11-17 (rehearsals 44025252867 and 44025259144): a generated site keeps its page as a Python
    template -- `<title>{SITE_TITLE}</title>`, `{packages_html}` -- and fills it when it serves. Read from the source,
    the copy gate called the template fields "placeholders left in the page" and the brand gate said the business
    name is missing: both wrong, on two builds of two. "The gates judge the page the product SERVES, not its source"
    (Michael 2026-11-10). When the repository has ONE page, that page is a template, and the preview smoke of THIS
    round returned the whole page GET / serves, the page units read that served copy. Otherwise they read the source,
    as before -- never a guess about which page is which, and never a page that was cut."""
    page = (rendered or {}).get('/') if isinstance(rendered, dict) else None
    if (len(found) != 1 or not isinstance(page, str) or not _TEMPLATE_FIELD.search(found[0][1])
            or len(page) >= SERVED_PAGE_LIMIT or '</html' not in page.lower()):
        return found
    return [(found[0][0] + ' (as served)', page)]


def check(gate: str, repository: dict[str, str], rendered=None) -> dict:
    """{'status': 'pass'|'fail'|'NOT_RUN', 'failures': [{unit, page, code, findings}], 'checked': [...]}.
    `rendered`: the preview smoke's {'/': html} of this round, when it passed (see served_copy)."""
    found = served_copy(pages(repository), rendered)
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
        # the served page of THIS round only: the smoke keeps its last page when a later round fails before it runs
        rendered = getattr(self._inner, 'last_pages', None) if report.passed else None
        result = check(self.gate, self.view(repository), rendered if isinstance(rendered, dict) else None)
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
WORKER_GATES = ('G3', 'G4', 'G6', 'HE', 'G10', 'G11', 'G1', 'BRAND', 'SHARE', 'G5', 'PRO')
MAX_CALIBRATION_FINDINGS = 3      # per failure, in the evidence of a gate that is still calibrating
MAX_FINDING_CHARS = 200


def install_all(engine) -> dict:
    """Install every gate of WORKER_GATES; returns {gate: units}."""
    missing = [g for g in WORKER_GATES if g not in DEFAULT_MODE]
    if missing:
        raise ValueError(f'gates with no stated default mode: {missing}')
    installed = {g: install(engine, g) for g in WORKER_GATES}
    carry_rules(engine, WORKER_GATES)
    return installed


RULES_REQUIREMENT = 'PLATFORM-CHECKS'


def rules_text(gates) -> str:
    """What the installed gates check, as one text for the generator: each unit's own manifest description, in gate
    order. A gate that is off is left out (it checks nothing). '' when nothing is installed.

    Rehearsal 44043708644 (the butcher, 2026-11-17): the share gate failed a page for a missing og:title, and nothing
    had ever told the generator a shared link needs one. A check the generator learns about only by failing it costs
    a repair round once the gate blocks; the manifest already says what the check wants."""
    lines = []
    for g in gates:
        if mode(g) == 'off':
            continue
        lines += [f"- {manifest(u)['description']}" for u in gate_units(g)]
    if not lines:
        return ''
    return '\n'.join(['Checks 148AI runs on the finished product. Each line is one check; build so every one passes:']
                     + lines)


def with_rules(spec, text: str):
    """The spec with the checks in it as written: one quality requirement, added once. Deterministic, no model."""
    from ..product_spec import ProductSpec
    data = spec.to_dict()
    if not text or any(r['id'] == RULES_REQUIREMENT for r in data['requirements']):
        return spec
    data['requirements'].append({'id': RULES_REQUIREMENT, 'text': text, 'kind': 'quality', 'mandatory': False})
    return ProductSpec.from_dict(data)


class GateRulesArchitect:
    """Wraps the engine's architect: every spec it returns says what the installed gates check."""

    def __init__(self, inner, gates):
        self._inner, self.gates = inner, tuple(gates)

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def create_spec(self, prompt, *args, **kwargs):
        return with_rules(self._inner.create_spec(prompt, *args, **kwargs), rules_text(self.gates))


def carry_rules(engine, gates) -> bool:
    """Give the generator the installed gates' checks through the spec. False (and said) with no architect."""
    core = getattr(engine, 'core', engine)
    carried = False
    for holder in (core, engine):
        architect = getattr(holder, 'architect', None)
        if architect is not None and not isinstance(architect, GateRulesArchitect):
            holder.architect = GateRulesArchitect(architect, gates)
        carried = carried or isinstance(getattr(holder, 'architect', None), GateRulesArchitect)
    core.gate_rules_carried = carried
    _LOG.info('GATE_RULES carried=%s gates=%s', carried, ','.join(gates))
    return carried


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
