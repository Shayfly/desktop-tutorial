"""Test fixture: the production verification chain with every check recorded as
having RUN and PASSED (release policy: a check that did not run is not a pass).

Worker tests that drive `_run_live_build_job` with a fake engine use this as
`engine.executor` so the policy sees real executor objects with real results,
instead of a MagicMock from which nothing can be read.
"""
from types import SimpleNamespace

from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
from omni_prod.browser_probe import BrowserFlowExecutor
from omni_prod.consistency_gate import ConsistencyGateExecutor
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.product_review import ProductReviewExecutor

ACCEPTED_SPEC = SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='works'),), requirements=())


def verified_chain(*, reviewer: str = 'reviewer-model', overrides: dict | None = None):
    o = overrides or {}
    c = ConsistencyGateExecutor(SimpleNamespace())
    c.last_consistency = o.get('consistency', {'passed': True, 'blocking': [], 'advisories': []})
    c.consistency_rounds = [{'passed': True, 'blocking': 0, 'advisories': 0}]
    p = PreviewReadyExecutor(c)
    p.last_smoke = o.get('smoke', {'status': 'PASS'})
    b = BehaviorAcceptanceExecutor(p)
    b.last_report = o.get('behavior', {'status': 'PASS', 'summary': 'behavioral acceptance passed'})
    br = BrowserFlowExecutor(b)
    br.last_probe = o.get('browser', {'status': 'passed', 'forms': 1, 'findings': []})
    rv = ProductReviewExecutor(br)
    rv.reviews = o.get('reviews', [{'round': 1, 'reviewer': 'model', 'model': reviewer, 'blocking': 0, 'enforced': False}])
    return rv
