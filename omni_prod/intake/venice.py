"""agent.venice -- ONE person for the customer, in two modes (owner decision 2026-10-26).

  understanding  listens: the gap detector (intake.gaps.Spec) fills the spec from the customer's words, one material
                 question at a time. A cost RANGE is said here already, every turn -- never hidden behind "easy".
  planning       turns the FROZEN, APPROVED spec into a plan. This is what agent.product_architect used to be.

The hard buffer: there is no planning while listening. plan() refuses unless the spec was frozen (its fingerprint
pinned) and the customer approved exactly that fingerprint; any later change of the spec drops back to understanding.
The switch between the modes is a visible stage for the customer (`stages`), not an internal hand-off.

The plan is checked by a SEPARATE verifier (intake.plan_verifier.PlanVerifier, agent.plan_verifier): Venice does not
grade her own plan (NORTH_STAR 1: a source for every requirement; 7: an independent checker).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..pricing import M5_CLASS_BUILD_CREDITS, CostClass
from .gaps import Spec, language_of

UNDERSTANDING, PLANNING = 'understanding', 'planning'


class PlanningBeforeApproval(RuntimeError):
    """A plan was requested while Venice is still listening (spec not frozen, or not approved as frozen)."""


# The range is honest about what is not decided yet: the floor is the lightest class that can build this kind,
# the ceiling the class the open or stated features may need. Credits are the existing per-class build prices.
_FEATURES_UP = ('login', 'personal_data', 'access_scope')


def cost_range(spec: Spec) -> tuple[int, int]:
    g = spec.detect()
    low = M5_CLASS_BUILD_CREDITS[CostClass.LIGHT]
    high_class = CostClass.STANDARD
    heavy = [f for f in _FEATURES_UP if g['known'].get(f) not in (None, 'none', 'no', 'internal_link')
             or f in g['missing_material']]
    if spec.kind == 'web_app' and heavy:
        high_class = CostClass.ADVANCED
    return low, M5_CLASS_BUILD_CREDITS[high_class]


_TEXT = {
    'he': {'stage_u': 'שלב 1 מתוך 2 — אני מקשיב ומבין מה לבנות', 'stage_p': 'שלב 2 מתוך 2 — המפרט אושר, אני מתכנן',
           'cost': 'הערכת עלות: {lo}–{hi} קרדיטים. הטווח יצטמצם כשהמפרט ייסגר; לא מתחילים שום דבר בתשלום בלי אישור שלך.'},
    'ar': {'stage_u': 'المرحلة 1 من 2 — أستمع وأفهم ما يجب بناؤه', 'stage_p': 'المرحلة 2 من 2 — تمت الموافقة على المواصفات، أخطط الآن',
           'cost': 'تقدير التكلفة: {lo}–{hi} رصيدًا. سيضيق النطاق عند إغلاق المواصفات؛ لا يبدأ أي عمل مدفوع دون موافقتك.'},
    'en': {'stage_u': 'Step 1 of 2 — I am listening to understand what to build', 'stage_p': 'Step 2 of 2 — the spec is approved, I am planning',
           'cost': 'Cost estimate: {lo}–{hi} credits. The range narrows when the spec is closed; nothing paid starts without your approval.'},
}


@dataclass
class Venice:
    spec: Spec
    mode: str = UNDERSTANDING
    frozen: str | None = None            # fingerprint of the spec the customer is asked to approve
    approved: str | None = None          # fingerprint the customer approved
    stages: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.stages:
            self._stage(UNDERSTANDING)

    def _lang(self) -> str:
        lang = language_of(' '.join(self.spec.ledger.messages[-2:]))
        return lang if lang in _TEXT else 'en'

    def _stage(self, mode: str) -> None:
        self.stages.append({'mode': mode})

    def _stage_text(self, mode: str) -> str:
        return _TEXT[self._lang()]['stage_u' if mode == UNDERSTANDING else 'stage_p']   # in the customer's language now

    # ---- understanding
    def hear(self, message: str, proposals=()) -> dict:
        before = self.spec.fingerprint()
        self.spec.hear(message, proposals)
        if self.frozen and self.spec.fingerprint() != before:
            # the customer changed something after freezing: back to listening; the old approval no longer applies
            self.frozen = self.approved = None
            if self.mode != UNDERSTANDING:
                self.mode = UNDERSTANDING
                self._stage(UNDERSTANDING)
        return self.view()

    def view(self) -> dict:
        lo, hi = cost_range(self.spec)
        t = _TEXT[self._lang()]
        stage = {'mode': self.stages[-1]['mode'], 'text': self._stage_text(self.stages[-1]['mode'])}
        return {'agent': 'agent.venice', 'mode': self.mode, 'stage': stage,
                'stages': [{'mode': st['mode'], 'text': self._stage_text(st['mode'])} for st in self.stages],
                'cost_range_credits': [lo, hi], 'cost_text': t['cost'].format(lo=lo, hi=hi),
                'missing_material': self.spec.detect()['missing_material']}

    def freeze(self) -> str:
        """The customer is shown THIS spec to approve. Only possible when nothing material is missing."""
        if self.spec.detect()['missing_material']:
            raise PlanningBeforeApproval('the spec still has open material fields: ' +
                                         ', '.join(self.spec.detect()['missing_material']))
        self.frozen = self.spec.fingerprint()
        return self.frozen

    def approve(self, fingerprint: str) -> None:
        """The customer's explicit approval of the frozen spec, by its fingerprint. Switches to planning (a stage)."""
        if not self.frozen or fingerprint != self.frozen or self.spec.fingerprint() != self.frozen:
            raise PlanningBeforeApproval('approval does not match the frozen spec')
        self.approved = fingerprint
        self.mode = PLANNING
        self._stage(PLANNING)

    # ---- planning
    def plan(self) -> dict:
        """Planning mode only. Every plan item names the spec requirement it answers and where that came from."""
        if self.mode != PLANNING or not self.approved or self.spec.fingerprint() != self.approved:
            raise PlanningBeforeApproval('no planning while listening: the spec must be frozen and approved first')
        g = self.spec.detect()
        items = []
        for name, value in sorted(g['known'].items()):
            cur = self.spec.ledger.current(name)
            source = ('customer' if cur is not None and cur.status == 'stated'
                      else 'delegated' if cur is not None and cur.why == 'delegated' else 'default')
            items.append({'requirement': name, 'value': value, 'source': source})
        for name, imp in sorted(g['implied'].items()):
            items.append({'requirement': name, 'value': imp['value'], 'source': 'implied'})
        for name, value in sorted(g['assumed'].items()):
            items.append({'requirement': name, 'value': value, 'source': 'default'})
        return {'agent': 'agent.venice', 'mode': PLANNING, 'spec_fingerprint': self.approved, 'kind': self.spec.kind,
                'items': items, 'cost_range_credits': list(cost_range(self.spec))}
