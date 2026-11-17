"""G-APPLE: the design gate (the owner, 2026-11-17).

"A page that could be any business" is what the other gates cannot see: each checks one thing that is wrong. This one
holds the page to a design contract locked before any code is written, and to a list of things a careful designer
never ships.

  contract.py    the locked design contract, from the approved brief: type scale, 8-grid, semantic palette with
                 computed contrast, two weights, one radius, motion tokens
  static.py      the page against the contract and the refusal list (deterministic)
  render.py      the page as laid out at 390 / 768 / 1440 / 320: sideways scroll, cut text, controls under 44 px,
                 off-grid spacing, line length, the 30/60-character string test (deterministic, in the sandbox browser)
  reviewers.py   two separate vision reviewers -- typography/layout and brand/category -- findings with a selector and
                 a severity; P0 blocks; a reviewer never touches code

It is installed LAST, right before the build, and it is a new gate: it enters at warn (gate.CALIBRATING). In warn every
finding goes to the log and the build evidence (`g_apple`) and nothing blocks. In block a static or render finding, or
a reviewer's P0, fails the build with what is wrong and where.

Without an approved brief there is no contract to lock (a raw request): the gate says NOT_RUN with that reason.
"""
from __future__ import annotations

import logging

from . import contract as C
from . import render as R
from . import reviewers as V
from . import static as S

GATE = 'APPLE'
ACCEPTANCE_ID = 'gate-APPLE'
_LOG = logging.getLogger(__name__)


class AppleGateExecutor:
    def __init__(self, inner, contract: dict | None, mode: str, *, gateway=None, business: str = '', not_run: str = ''):
        self._inner, self.contract, self.mode = inner, contract, mode
        self.gateway, self.business, self.not_run = gateway, business, not_run
        self.last_apple = None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        from ..autonomous_core import AcceptanceFailure, ExecutionReport
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report                       # a page that fails earlier checks is not yet a page to judge
        if self.contract is None:
            self.last_apple = {'status': 'NOT_RUN', 'mode': self.mode, 'reason': self.not_run}
            _LOG.warning('APPLE_NOT_RUN mode=%s reason=%s', self.mode, self.not_run)
            return report
        result = self.check(repository)
        self.last_apple = result
        blocking = result['static'] + result['render'] + [
            {'code': f"REVIEW_{r['reviewer']}", 'where': f['selector'], 'why': f['problem']}
            for r in result['reviewers'] if r['status'] == 'REVIEWED' for f in r['findings'] if f['severity'] == 'P0']
        _LOG.info('APPLE mode=%s status=%s static=%d render=%d p0=%s not_run=%s', self.mode, result['status'],
                  len(result['static']), len(result['render']),
                  {r['reviewer']: r.get('p0') for r in result['reviewers']}, result['not_run'])
        if self.mode != 'block' or not blocking:
            return report
        failures = tuple(AcceptanceFailure(ACCEPTANCE_ID, (
            f"{f['code']} at {f.get('where') or f.get('selector') or 'the page'}"
            + (f" ({f['width']} px wide)" if f.get('width') else '') + f": {f['why']}")) for f in blocking[:12])
        return ExecutionReport(False, tuple(report.failures) + failures, report.build_log)

    def check(self, repository: dict) -> dict:
        from ..skill_units.gate import pages, served_copy
        not_run: list[str] = []
        rendered = getattr(self._inner, 'last_pages', None)
        found = served_copy(pages(repository), rendered if isinstance(rendered, dict) else None)
        static = [{**f, 'page': path} for path, html in found for f in S.check(html, self.contract)]
        if not found:
            not_run.append('static: no HTML page in the repository')
        render: list[dict] = []
        run = getattr(self._inner, '_run', None)
        if not callable(run):
            not_run.append('render: no sandbox to open the page in')
        else:
            from ..sandbox_script import staged_script
            for width in R.WIDTHS:                           # bounded: four widths
                try:
                    staged, argv = staged_script(repository, 'apple_render', R.PROBE, str(width))
                    measured = R.parse(run(staged, argv, f'apple-{width}', profile='browser').get('stdout', ''))
                except Exception as exc:
                    from ..verification_verdict import reraise_control
                    reraise_control(exc)
                    measured, why = None, f'{type(exc).__name__}: {exc}'[:160]
                else:
                    why = 'no measurement printed'
                if measured is None:
                    not_run.append(f'render {width}: {why}')
                    continue
                render.extend(R.findings(measured))
        shots = getattr(self._inner, 'last_shots', None)
        shots = shots if isinstance(shots, dict) else {}
        reviews = [V.review(self.gateway, name, shots, business=self.business) for name in V.REVIEWERS]
        not_run += [f"{r['reviewer']}: {r['reason']}" for r in reviews if r['status'] == 'NOT_RUN']
        p0 = sum(r.get('p0', 0) for r in reviews if r['status'] == 'REVIEWED')
        status = 'fail' if (static or render or p0) else ('NOT_RUN' if not_run else 'pass')
        return {'status': status, 'mode': self.mode, 'contract': self.contract['fingerprint'], 'static': static,
                'render': render, 'reviewers': reviews, 'not_run': not_run}


def install(engine, *, prompt: str, gateway=None) -> str:
    """Lock the contract, give it to the generator, and install the gate in its mode. Returns the prompt the engine
    builds from. Installed last, right before the build."""
    from ..skill_units import gate as G
    core = getattr(engine, 'core', engine)
    mode = G.mode(GATE)
    modes = dict(getattr(core, 'gate_modes', None) or {})
    modes[GATE] = mode
    core.gate_modes = modes
    if mode == 'off':
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s): this build is NOT checked by %s', GATE, GATE, GATE)
        return prompt
    try:
        contract, why = C.build(prompt), ''
    except C.ContractError as exc:
        contract, why = None, f'no design contract: {exc}'
    core.design_contract = contract
    business = (prompt or '').split('--- Approved project brief')[0].strip()
    core.executor = core.apple_gate = AppleGateExecutor(core.executor, contract, mode, gateway=gateway,
                                                         business=business, not_run=why)
    _LOG.info('GATE_ON gate=%s mode=%s contract=%s', GATE, mode, contract['fingerprint'] if contract else 'NONE')
    return prompt + '\n\n' + C.rules(contract) if contract else prompt


def report(engine) -> dict:
    core = getattr(engine, 'core', engine)
    modes = getattr(core, 'gate_modes', None)
    gate = getattr(core, 'apple_gate', None)
    contract = getattr(core, 'design_contract', None)
    return {'gate': GATE, 'mode': modes.get(GATE) if isinstance(modes, dict) else None,
            'contract': {k: contract[k] for k in ('fingerprint', 'tokens', 'contrast', 'dropped')} if isinstance(contract, dict) else None,
            'last': gate.last_apple if isinstance(gate, AppleGateExecutor) else None}
