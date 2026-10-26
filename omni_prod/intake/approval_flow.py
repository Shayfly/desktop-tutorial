"""Two-gate approval for the live conversation (owner decision 2026-10-26): Venice is wired into the chat.

  free conversation  -> the spec + a cost RANGE                       (Venice, understanding: "Step 1 of 2")
  gate 1             the customer approves the spec, by its fingerprint. No plan exists before this.
  plan               made from the APPROVED spec, then checked by the separate verifier (agent.plan_verifier)
                     BEFORE the customer sees it. A verifier correction is a visible line; a refused plan is not shown.
  gate 2             the customer approves the budget: the exact cost next to the range said earlier; a cost outside
                     the range is said in full, with the reason -- never smoothed over.
  build              only then.

Approval state lives in the durable conversation log (intake_messages.interpretation), so no migration is needed:
  {'gate': 'spec'}                     a turn that asked for gate 1 (marks the project as on the two-gate flow)
  {'spec_approved': <fingerprint>}     the customer's gate-1 approval
A saved plan made on this flow carries plan['spec_gate'] with the verifier's verdict. Plans saved before this flow
(no 'spec_gate') and projects that never saw gate 1 keep the old path: nothing approved earlier is broken.
"""
from __future__ import annotations

from ..pricing import M5_CLASS_BUILD_CREDITS, CostClass
from . import contract as C
from .plan_verifier import PlanVerifier, Verdict

GATE_KEY = 'spec_gate'
_SOURCE = {'message': 'customer', 'answer': 'customer', 'delegated': 'delegated', 'implied': 'implied',
           'probe': 'implied', 'default': 'default'}
_HEAVY = ('login', 'personal_data', 'access_scope')


# ------------------------------------------------------------------ durable gate state

def on_two_gate_flow(messages) -> bool:
    return any((m.get('interpretation') or {}).get('gate') == 'spec' or (m.get('interpretation') or {}).get('spec_approved')
               for m in messages)


def spec_approved(messages, fingerprint: str) -> bool:
    return bool(fingerprint) and any((m.get('interpretation') or {}).get('spec_approved') == fingerprint for m in messages)


# ------------------------------------------------------------------ cost

def cost_range(brief) -> tuple[int, int]:
    """The range said while listening: same rule as agent.venice (intake.venice.cost_range), read from the brief."""
    from .families import classify_family
    v = brief.values()
    low, high = M5_CLASS_BUILD_CREDITS[CostClass.LIGHT], CostClass.STANDARD
    heavy = [f for f in _HEAVY if v.get(f) not in (None, 'none', 'no', 'internal_link')]
    if classify_family(brief.prompt) == 'web_app' and heavy:
        high = CostClass.ADVANCED
    return low, M5_CLASS_BUILD_CREDITS[high]


def compare(rng: tuple[int, int], exact: int | None) -> dict:
    lo, hi = rng
    if exact is None:
        return {'range': [lo, hi], 'exact': None, 'outside_range': None}
    return {'range': [lo, hi], 'exact': exact, 'outside_range': 'above' if exact > hi else 'below' if exact < lo else None}


# ------------------------------------------------------------------ the verifier's view

def _auth(plan) -> str | None:
    for line in plan.get('security_boundaries') or []:
        if str(line).startswith('sign-in: '):
            return str(line)[len('sign-in: '):]
    return None


def spec_view(brief) -> dict:
    """The approved spec as requirements: every brief field, plus what the plan must carry from it."""
    contract = C.build(brief)
    out = {f'field:{k}': v['value'] for k, v in brief.fields.items() if 'value' in v}
    out.update({'product_family': contract.product_family, 'auth_mode': contract.authentication_requirements['mode'],
                'languages': list(contract.languages), 'personal_data': bool(contract.data_requirements.get('personal_data')),
                'acceptance_criteria': [a['id'] for a in contract.acceptance_criteria],
                'requirements_fingerprint': contract.fingerprint()})
    return out


def plan_items(plan: dict, brief) -> list[dict]:
    """What the plan actually says, as verifier items. Field items are only as good as the plan's derivation: if the
    plan was made from other requirements, every field is reported as not carried."""
    derived = plan.get('requirements_fingerprint') == C.build(brief).fingerprint()
    items = [{'requirement': f'field:{k}', 'value': v['value'] if derived else '<plan made from other requirements>',
              'source': _SOURCE.get(v.get('source'), 'default')}
             for k, v in brief.fields.items() if 'value' in v]
    ui = plan.get('ui_architecture') or {}
    items += [{'requirement': 'product_family', 'value': plan.get('product_family'), 'source': 'implied'},
              {'requirement': 'auth_mode', 'value': _auth(plan), 'source': 'implied'},
              {'requirement': 'languages', 'value': list(ui.get('languages') or []), 'source': 'implied'},
              {'requirement': 'personal_data', 'source': 'implied',
               'value': any('personal data' in str(x) for x in plan.get('security_boundaries') or [])},
              {'requirement': 'acceptance_criteria', 'source': 'implied',
               'value': [a.get('id') for a in plan.get('acceptance_criteria') or []]},
              {'requirement': 'requirements_fingerprint', 'value': plan.get('requirements_fingerprint'), 'source': 'implied'}]
    return items


def verify(plan: dict, brief, approved_fingerprint: str) -> Verdict:
    return PlanVerifier().verify(spec_fingerprint=approved_fingerprint, spec_values=spec_view(brief),
                                 plan={'spec_fingerprint': plan.get('brief_fingerprint'), 'items': plan_items(plan, brief)})


def verified_plan(make_plan, brief, approved_fingerprint: str) -> tuple[dict | None, dict]:
    """Plan -> verifier -> (one correction: re-plan from the approved spec) -> verifier. Returns (plan or None, record).
    The customer sees the plan only if the last verdict accepted it."""
    plan = make_plan()
    first = verify(plan, brief, approved_fingerprint)
    record = {'agent': 'agent.plan_verifier', 'accepted': first.accepted, 'problems': list(first.problems),
              'corrected': False}
    if first.accepted:
        return plan, record
    plan = make_plan(corrective=True)
    second = verify(plan, brief, approved_fingerprint)
    record.update(accepted=second.accepted, corrected=second.accepted, remaining=list(second.problems))
    return (plan if second.accepted else None), record


# ------------------------------------------------------------------ customer text

TEXT = {
    'he': {'stage1': 'שלב 1 מתוך 2', 'stage2': 'שלב 2 מתוך 2',
           'spec': 'זה המפרט שהבנתי: {summary}.',
           'range': 'הערכת עלות: {lo}–{hi} קרדיטים.',
           'gate1': 'אם זה נכון, אשרו את המפרט ואז אכין תוכנית. לא נבנית תוכנית ולא מחויב דבר לפני האישור.',
           'gate1_needed': 'קודם צריך לאשר את המפרט; לא מכינים תוכנית לפני כן.',
           'stale': 'המפרט השתנה מאז שהוצג. זה המפרט העדכני; אשרו אותו כדי שאתכנן.',
           'planned': 'המפרט אושר. הכנתי תוכנית והמאמת בדק אותה מול המפרט.',
           'fixed': 'המאמת מצא ותיקן: {what}.',
           'refused': 'התוכנית לא עברה את בדיקת המאמת ולכן לא מוצגת: {what}. לא מחויב דבר; אפשר לערוך את המפרט.',
           'exact': 'העלות המדויקת: {exact} קרדיטים (הטווח שנאמר: {lo}–{hi}).',
           'above': 'שימו לב: זה מעל הטווח שאמרתי ({lo}–{hi}) ב-{d} קרדיטים. הסיבה: המחיר המדויק נקבע לפי המסלול שלך ומורכבות התוכנית ({cx}), והוא גבוה ממה שהערכתי.',
           'below': 'זה מתחת לטווח שאמרתי ({lo}–{hi}) ב-{d} קרדיטים: המחיר המדויק לפי המסלול שלך נמוך ממה שהערכתי.',
           'exact_unknown': 'את העלות המדויקת אחשב באישור התקציב; עד אז הטווח הוא {lo}–{hi} קרדיטים.',
           'gate2': 'כדי להתחיל לבנות, אשרו את התקציב.'},
    'ar': {'stage1': 'المرحلة 1 من 2', 'stage2': 'المرحلة 2 من 2',
           'spec': 'هذه المواصفات كما فهمتها: {summary}.',
           'range': 'تقدير التكلفة: {lo}–{hi} رصيدًا.',
           'gate1': 'إذا كانت صحيحة، وافق على المواصفات ثم أُعدّ خطة. لا خطة ولا خصم قبل الموافقة.',
           'gate1_needed': 'يجب الموافقة على المواصفات أولًا؛ لا خطة قبل ذلك.',
           'stale': 'تغيّرت المواصفات منذ عرضها. هذه هي الحالية؛ وافق عليها لأخطط.',
           'planned': 'تمت الموافقة على المواصفات. أعددت خطة وفحصها المدقق مقابل المواصفات.',
           'fixed': 'وجد المدقق وصحّح: {what}.',
           'refused': 'لم تجتز الخطة فحص المدقق ولذلك لا تُعرض: {what}. لم يُخصم شيء؛ يمكن تعديل المواصفات.',
           'exact': 'التكلفة الدقيقة: {exact} رصيدًا (النطاق المذكور: {lo}–{hi}).',
           'above': 'انتبه: هذا أعلى من النطاق الذي ذكرته ({lo}–{hi}) بـ {d} رصيدًا. السبب: السعر الدقيق يحدده اشتراكك وتعقيد الخطة ({cx})، وهو أعلى من تقديري.',
           'below': 'هذا أقل من النطاق الذي ذكرته ({lo}–{hi}) بـ {d} رصيدًا: السعر الدقيق في اشتراكك أقل من تقديري.',
           'exact_unknown': 'سأحسب التكلفة الدقيقة عند الموافقة على الميزانية؛ حتى ذلك الحين النطاق {lo}–{hi} رصيدًا.',
           'gate2': 'لبدء البناء، وافق على الميزانية.'},
    'en': {'stage1': 'Step 1 of 2', 'stage2': 'Step 2 of 2',
           'spec': 'This is the spec as I understood it: {summary}.',
           'range': 'Cost estimate: {lo}–{hi} credits.',
           'gate1': 'If it is right, approve the spec and I will prepare a plan. No plan is made and nothing is charged before you approve.',
           'gate1_needed': 'The spec has to be approved first; no plan is made before that.',
           'stale': 'The spec changed since it was shown. This is the current one; approve it and I will plan.',
           'planned': 'The spec is approved. I prepared a plan and the verifier checked it against the spec.',
           'fixed': 'The verifier found and fixed: {what}.',
           'refused': 'The plan did not pass the verifier, so it is not shown: {what}. Nothing was charged; you can edit the spec.',
           'exact': 'Exact cost: {exact} credits (the range I gave: {lo}–{hi}).',
           'above': 'Note: this is above the range I gave ({lo}–{hi}) by {d} credits. Why: the exact price follows your plan and the plan\'s complexity ({cx}), and it is higher than my estimate.',
           'below': 'This is below the range I gave ({lo}–{hi}) by {d} credits: the exact price on your plan is lower than my estimate.',
           'exact_unknown': 'I will calculate the exact cost when you approve the budget; until then the range is {lo}–{hi} credits.',
           'gate2': 'To start building, approve the budget.'},
}


def text(lang: str) -> dict:
    return TEXT[lang if lang in TEXT else 'en']


def budget_lines(cmp: dict, lang: str, complexity: str | None) -> list[str]:
    t, (lo, hi) = text(lang), cmp['range']
    if cmp['exact'] is None:
        return [t['exact_unknown'].format(lo=lo, hi=hi)]
    lines = [t['exact'].format(exact=cmp['exact'], lo=lo, hi=hi)]
    if cmp['outside_range'] == 'above':
        lines.append(t['above'].format(lo=lo, hi=hi, d=cmp['exact'] - hi, cx=complexity or '—'))
    elif cmp['outside_range'] == 'below':
        lines.append(t['below'].format(lo=lo, hi=hi, d=lo - cmp['exact']))
    return lines
