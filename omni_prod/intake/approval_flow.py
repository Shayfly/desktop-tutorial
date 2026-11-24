"""Two-gate approval for the live conversation (owner decision 2026-10-26): Venice is wired into the chat.

  free conversation  -> the spec + a cost RANGE                       (Venice, understanding: "Step 1 of 2")
  gate 1             the customer approves the spec, by its fingerprint. No plan exists before this.
  plan               made from the APPROVED spec, then checked by the separate verifier (agent.plan_verifier)
                     BEFORE the customer sees it. A verifier correction is a visible line; a refused plan is not shown.
  gate 2             the customer approves the budget: the exact cost next to the range said earlier; a cost outside
                     the range is said in full, with the reason -- never smoothed over.
  build              only then.

Approval state lives in the durable conversation log (intake_messages.interpretation), so no migration is needed:
  {'flow': 'two_gate'}                 the FIRST message of a conversation started after 2026-10-28 (explicit mark)
  {'gate': 'spec'}                     a turn that asked for gate 1 (marks the project as on the two-gate flow)
  {'spec_approved': <fingerprint>}     the customer's gate-1 approval
A saved plan made on this flow carries plan['spec_gate'] with the verifier's verdict. Plans saved before this flow
(no 'spec_gate') and projects that never saw gate 1 keep the old path: nothing approved earlier is broken.
"""
from __future__ import annotations

import json

from ..pricing import M5_CLASS_BUILD_CREDITS, CostClass
from .. import customer_lang as CL
from . import contract as C
from .plan_verifier import PlanVerifier, Verdict

GATE_KEY = 'spec_gate'
_SOURCE = {'message': 'customer', 'answer': 'customer', 'delegated': 'delegated', 'implied': 'implied',
           'probe': 'implied', 'default': 'default'}
_HEAVY = ('login', 'personal_data', 'access_scope')


# ------------------------------------------------------------------ durable gate state

FLOW = 'two_gate'


def on_two_gate_flow(messages) -> bool:
    """True when the conversation was STARTED on the two-gate flow (its first message carries flow='two_gate',
    founder 2026-10-28), or when it already asked for gate 1 / recorded a spec approval. A project with none of these
    is an earlier project and keeps the earlier path."""
    return any((m.get('interpretation') or {}).get('flow') == FLOW
               or (m.get('interpretation') or {}).get('gate') == 'spec' or (m.get('interpretation') or {}).get('spec_approved')
               for m in messages)


def spec_approved(messages, fingerprint: str) -> bool:
    return bool(fingerprint) and any((m.get('interpretation') or {}).get('spec_approved') == fingerprint for m in messages)


def spec_invalid_reason(brief, messages, fingerprint: str) -> str | None:
    """Why an approval of this spec does not stand (None = it stands). Michael 2026-11-13 (the cafe): an approval is
    valid only for a spec that (1) was approved at this fingerprint, (2) already holds every fact the customer's
    stored messages state, and (3) has no needed fact that is neither given nor waived. Used by the conversation
    AND by build admission, so no path builds on an older approval."""
    from .. import discovery as d
    from . import media_reading as MR
    if not spec_approved(messages, fingerprint):
        return 'spec_not_approved'
    # warehouse 128: a draft read from the customer's file that awaits their decision holds every approval
    if MR.pending_drafts(messages):
        return 'reading_draft_pending'
    probe = d.Brief.from_dict(json.loads(json.dumps(brief.to_dict())))
    if d.note_customer_texts(probe, d.customer_messages(messages)) or MR.collect_skeleton(probe, messages):
        return 'facts_not_collected'
    if d.missing_facts(brief)[0]:
        return 'missing_facts_not_waived'
    return None


# ------------------------------------------------------------------ cost

def cost_range(brief, plan_credits: int | None = None) -> tuple[int, int]:
    """The cost said while listening. The price of a build is set by the customer's plan alone (pricing.m5_build_terms),
    so when the plan is known the "range" is that one number, said from the first message (the owner, 2026-11-16: the
    chat said 45-200 and the panel said 500; one of them was false). Only with no known plan is it an estimate: the
    same rule as agent.venice (intake.venice.cost_range), read from the brief."""
    if plan_credits is not None:
        if isinstance(plan_credits, bool) or not isinstance(plan_credits, int) or plan_credits < 0:
            raise ValueError(f'plan_credits must be a non-negative int, got {plan_credits!r}')
        return plan_credits, plan_credits
    from .families import classify_family
    v = brief.values()
    low, high = M5_CLASS_BUILD_CREDITS[CostClass.LIGHT], CostClass.STANDARD
    heavy = [f for f in _HEAVY if v.get(f) not in (None, 'none', 'no', 'internal_link')]
    if classify_family(brief.prompt) == 'web_app' and heavy:
        high = CostClass.ADVANCED
    return low, M5_CLASS_BUILD_CREDITS[high]


def range_line(lang: str, lo: int, hi: int) -> str:
    """One number when the plan set the price, a range only when it is an estimate."""
    t = text(lang)
    return t['price'].format(c=lo) if lo == hi else t['range'].format(lo=lo, hi=hi)


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

# Plain words (owner 2026-11-21): the customer reads no name of the machinery here -- what was understood, what it takes
# from their balance, and the one button to press, called by the name the button really has. The two buttons' names
# live here once; assets/app.js carries the same words (tests/test_plain_words_failure_and_approval.py compares them).
# The verifier's own findings ({what}) and the plan's raw complexity ({cx}) stay in the stored record
# (interpretation.verification, the plan's spec_gate) and are not said to the customer.
# The Arabic names are app.js's T.ar labels of the same buttons (tests/test_server_texts_arabic.py compares them).
CONFIRM_BUTTON = {'he': 'כן, זה נכון', 'en': 'Yes, that is right', 'ar': 'نعم، هذا صحيح'}
APPROVE_BUTTON = {'he': 'לאשר ולהתחיל לבנות', 'en': 'Approve and start building', 'ar': 'الموافقة وبدء البناء'}
EDIT_BUTTON = {'he': 'עריכת הבקשה', 'en': 'Edit requirements', 'ar': 'تعديل الطلب'}

TEXT = {
    'he': {'stage1': 'שלב 1 מתוך 2', 'stage2': 'שלב 2 מתוך 2',
           'spec': 'זה מה שהבנתי שאתם רוצים: {summary}.',
           'price': 'הבנייה הזו תוריד {c} מהיתרה שלכם.',
           'exact_same': 'המחיר: {exact} מהיתרה שלכם, כמו שאמרתי.',
           'range': 'הערכה: הבנייה תוריד בין {lo} ל-{hi} מהיתרה שלכם.',
           'gate1': 'אם זה נכון, לחצו על "' + CONFIRM_BUTTON['he'] + '" ואכין תוכנית. שום דבר לא נבנה ולא חויבתם על שום דבר לפני כן.',
           'gate1_needed': 'קודם צריך לאשר שהבנתי נכון; אני לא מכין תוכנית לפני כן.',
           'stale': 'הבקשה השתנתה מאז שהצגתי אותה. זו הבקשה כמו שהיא עכשיו; אשרו אותה ואכין תוכנית.',
           'planned': 'מעולה. הכנתי תוכנית.',
           'fixed': 'תיקנתי אותה לפני שהצגתי אותה.',
           'refused': 'לא הצלחתי להכין תוכנית שמתאימה למה שביקשתם. לא חויבתם. כתבו שוב במשפט אחד מה הכי חשוב לכם, או לחצו על "' + EDIT_BUTTON['he'] + '".',
           'exact': 'המחיר המדויק: {exact} מהיתרה שלכם (קודם אמרתי {lo}–{hi}).',
           'above': 'שימו לב: זה {d} יותר ממה שאמרתי ({lo}–{hi}). המחיר המדויק נקבע רק אחרי שהתוכנית מוכנה, והוא יצא גבוה מההערכה שלי.',
           'below': 'זה {d} פחות ממה שאמרתי ({lo}–{hi}): המחיר המדויק יצא נמוך מההערכה שלי.',
           'exact_unknown': 'את המחיר המדויק אחשב כשתאשרו את הבנייה; עד אז ההערכה היא בין {lo} ל-{hi} מהיתרה שלכם.',
           'gate2': 'כדי להתחיל לבנות, לחצו על "' + APPROVE_BUTTON['he'] + '".'},
    # Arabic (2026-11-22): translated from the Hebrew and independently reviewed; it replaces the first Arabic, which
    # named the machinery (spec, verifier, budget, plan) and did not name the buttons.
    'ar': {'stage1': 'الخطوة 1 من 2', 'stage2': 'الخطوة 2 من 2',
           'spec': 'هذا ما فهمت أنكم تريدونه: {summary}.',
           'price': 'هذا البناء سيخصم {c} من رصيدكم.',
           'exact_same': 'السعر: {exact} من رصيدكم، كما قلت.',
           'range': 'تقدير: سيخصم البناء ما بين {lo} و{hi} من رصيدكم.',
           'gate1': 'إذا كان هذا صحيحًا، اضغطوا على "' + CONFIRM_BUTTON['ar'] + '" وسأُعدّ خطة. لا يُبنى شيء ولا يُخصم منكم أي مبلغ قبل ذلك.',
           'gate1_needed': 'يجب أولًا أن تؤكدوا أنني فهمتكم بشكل صحيح؛ لا أُعدّ خطة قبل ذلك.',
           'stale': 'تغيّر الطلب منذ أن عرضته. هذا هو الطلب كما هو الآن؛ أكّدوه وسأُعدّ خطة.',
           'planned': 'رائع. أعددت خطة.',
           'fixed': 'صحّحتها قبل أن أعرضها.',
           'refused': 'لم أتمكن من إعداد خطة تناسب ما طلبتم. لم يُخصم منكم أي مبلغ. اكتبوا مرة أخرى، في جملة واحدة، ما هو الأهم بالنسبة لكم، أو اضغطوا على "' + EDIT_BUTTON['ar'] + '".',
           'exact': 'السعر الدقيق: {exact} من رصيدكم (قلت سابقًا {lo}–{hi}).',
           'above': 'لاحظوا: هذا أكثر بـ{d} مما قلت ({lo}–{hi}). السعر الدقيق لا يُحدَّد إلا بعد أن تجهز الخطة، وقد جاء أعلى من تقديري.',
           'below': 'هذا أقل بـ{d} مما قلت ({lo}–{hi}): جاء السعر الدقيق أقل من تقديري.',
           'exact_unknown': 'سأحسب السعر الدقيق عندما توافقون على البناء؛ وحتى ذلك الحين التقدير ما بين {lo} و{hi} من رصيدكم.',
           'gate2': 'لبدء البناء، اضغطوا على "' + APPROVE_BUTTON['ar'] + '".'},
    'en': {'stage1': 'Step 1 of 2', 'stage2': 'Step 2 of 2',
           'spec': 'This is what I understood you want: {summary}.',
           'price': 'This build takes {c} from your balance.',
           'exact_same': 'The price: {exact} from your balance, as I said.',
           'range': 'Estimate: this build takes between {lo} and {hi} from your balance.',
           'gate1': 'If it is right, press "' + CONFIRM_BUTTON['en'] + '" and I will prepare a plan. Nothing is built and you are charged for nothing before that.',
           'gate1_needed': 'First confirm that I understood you; I do not prepare a plan before that.',
           'stale': 'The request changed since I showed it. This is the request as it is now; confirm it and I will prepare a plan.',
           'planned': 'Great. I prepared a plan.',
           'fixed': 'I corrected it before showing it.',
           'refused': 'I could not prepare a plan that fits what you asked for. You were not charged. Write again, in one sentence, what matters most to you, or press "' + EDIT_BUTTON['en'] + '".',
           'exact': 'The exact price: {exact} from your balance (earlier I said {lo}–{hi}).',
           'above': 'Note: this is {d} more than I said ({lo}–{hi}). The exact price is set only once the plan is ready, and it came out higher than my estimate.',
           'below': 'This is {d} less than I said ({lo}–{hi}): the exact price came out lower than my estimate.',
           'exact_unknown': 'I will calculate the exact price when you approve the build; until then the estimate is between {lo} and {hi} from your balance.',
           'gate2': 'To start building, press "' + APPROVE_BUTTON['en'] + '".'},
}


def text(lang: str) -> dict:
    return CL.of(TEXT, lang)


def budget_lines(cmp: dict, lang: str, complexity: str | None) -> list[str]:
    t, (lo, hi) = text(lang), cmp['range']
    if cmp['exact'] is None:
        return [t['exact_unknown'].format(lo=lo, hi=hi)]
    if lo == hi == cmp['exact']:              # the plan's price was said at gate 1; nothing to compare
        return [t['exact_same'].format(exact=cmp['exact'])]
    lines = [t['exact'].format(exact=cmp['exact'], lo=lo, hi=hi)]
    if cmp['outside_range'] == 'above':
        lines.append(t['above'].format(lo=lo, hi=hi, d=cmp['exact'] - hi, cx=complexity or '—'))
    elif cmp['outside_range'] == 'below':
        lines.append(t['below'].format(lo=lo, hi=hi, d=lo - cmp['exact']))
    return lines
