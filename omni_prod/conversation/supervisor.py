"""Conversation Supervisor (Unified Conversation OS §1-2, §4).

One persistent conversation per project. Each customer message is routed by
a DETERMINISTIC intent classifier (no model cost for routing) to existing
services:

  requirements    -> intake interpreter + confidence policy -> new brief revision
  answer          -> a quick-reply to an open question (same validated path as discovery)
  missing         -> open material questions / contradictions from the brief
  recommend       -> the recommended defaults and the provisional plan
  cost            -> credits + the plan's authorized model budget (no invented prices)
  feasibility     -> "can we add payments (later)?" -> feasibility gate on that capability
  approve         -> the approval ACTION (the customer still clicks; never auto-builds)
  status          -> durable build/agent task records
  modify          -> an existing version exists: offers the modification pipeline (customer confirms)

After any brief change the Chief Architect re-plans (deterministic, $0) and the
plan is stored as PROPOSED for that brief fingerprint. Nothing paid starts here.
A model is used only for interpretation, only when OMNI_INTAKE_MODEL=1, only
within the per-project conversation budget, and only through the routed
gateway's `conversation` task class (cheap models allowed; never for
architecture). Chat history is not the source of truth: the brief, plans,
builds and versions are.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .. import discovery as d
from ..intake import agent as intake_agent
from ..intake import contract as C
from ..intake.interpreter import DeterministicInterpreter, interpreter_from_env, language_of
from ..planning import feasibility as F
from ..planning.architect import ChiefArchitect

INTENTS = ('requirements', 'answer', 'missing', 'recommend', 'cost', 'feasibility', 'approve', 'status', 'modify')
_RX = {
    'status': r'(מה המצב|איפה (זה )?עומד|מה קורה עם הבנייה|סטטוס|how is it going|\bstatus\b|progress|is it done)',
    'cost': r'(כמה (זה )?(יעלה|עולה)|מה המחיר|עלות|קרדיטים|how much|what will it cost|price|cost)',
    'missing': r'(מה חסר|מה עוד צריך|מה אתה צריך ממני|what\'?s missing|what is missing|what do you need)',
    'recommend': r'(מה אתה ממליץ|מה מומלץ|תמליץ|what do you recommend|any recommendation|what would you suggest)',
    'feasibility': r'(אפשר להוסיף|האם אפשר|אפשר גם|תוכלו להוסיף|can (we|you) add|is it possible|could it also|later\?)',
    'approve': r'(תתחיל(ו)? לבנות|תבנה את זה|אפשר להתחיל|מאשר(ת)? (את )?(הבנייה|התוכנית)|go ahead|start (the )?build|build it now|let\'?s build)',
}
_MODIFY_RX = r'(תשנה|תשנו|שנה את|תוסיף|תוסיפו|להוסיף|תוריד|תמחק|הזז|change|add|remove|make the|move the|rename|fix)'
_FEAS_KEYS = (('payments', r'(תשלו[םמ]|סליקה|payment|stripe|checkout)'), ('sign-in', r'(התחברות|לוגין|login|sign ?in)'),
              ('email', r'(מייל|email)'), ('sms', r'(sms|וואטסאפ|whatsapp)'), ('mobile app', r'(אפליקציה|app store|android|ios)'),
              ('publishing', r'(לפרסם|דומיין|כתובת קבועה|publish|domain)'), ('images', r'(תמונות|image|לוגו)'))


_CAP_HE = {'payments': 'תשלומים', 'sign-in': 'התחברות משתמשים', 'email': 'שליחת מיילים', 'sms': 'הודעות SMS/וואטסאפ',
           'mobile app': 'אפליקציה לנייד', 'publishing': 'פרסום לכתובת קבועה', 'images': 'יצירת תמונות'}
_REASON_HE = {F.BLOCKED: 'עוד לא מחובר בפלטפורמה', F.UNSUPPORTED: 'עוד לא נתמך', F.WITH_CONSTRAINTS: 'אפשרי עם מגבלות'}
_ALT_HE = {'payments': 'לבנות עכשיו בלי תשלומים ולהוסיף אותם כשהחיבור יהיה זמין', 'sign-in': 'כלי פנימי בלי התחברות, בקישור פרטי',
           'email': 'לבנות עכשיו בלי שליחת מיילים', 'sms': 'לבנות עכשיו בלי הודעות', 'mobile app': 'גרסת ווב שעובדת גם בנייד',
           'publishing': 'תצוגה מקדימה פרטית והורדת קוד המקור', 'images': 'להעלות תמונות משלכם'}


# A bare "start" once a brief exists ("תתחיל", "בוא נתחיל", "go") asks for the approval screen. The first message
# of a project ("תבנה לי ...") stays a requirements message because it only matches with a brief and as a full match.
_START_BARE = (r'(?:יאללה\s+)?(?:בוא(?:ו)?\s+)?(?:נתחיל|תתחיל(?:ו)?|תתחילי|תבנה|תבנו|תבני|להתחיל|התחל)'
               r'(?:\s+לבנות)?(?:\s+(?:עכשיו|כבר|בבקשה))*|(?:ok\s+)?(?:go|start|let\'?s start)(?:\s+(?:now|please))*')


def classify_intent(message: str, *, has_version: bool, has_brief: bool) -> str:
    t = (message or '').strip().lower()
    if has_brief and re.fullmatch(_START_BARE, t.strip(' .!?,'), re.I):
        return 'approve'
    for intent in ('status', 'approve', 'cost', 'missing', 'recommend', 'feasibility'):
        if re.search(_RX[intent], t, re.I):
            return intent
    if has_version and re.search(_MODIFY_RX, t, re.I):
        return 'modify'
    return 'requirements'


# Content the customer adds after the brief is complete (prices, copy, links, logo text). It is recorded, verbatim,
# in the brief's "content" field as a new revision; the new fingerprint invalidates any earlier approval.
_CONTENT_RX = re.compile(r'(₪|\bnis\b|\bils\b|\$|\d{2,}\s*(ש"ח|שקל|₪)|מחיר|מחירון|מחירים|טקסט|תוכן|קישור|לינק|וואטסאפ|ווטסאפ|whatsapp|wa\.me|'
               r'לוגו|logo|price|prices|copy|link)', re.I)


def _record_content(brief, message: str):
    text = ' '.join((message or '').split())[:1500]
    cur = brief.fields.get('content')
    if cur and cur.get('source') in ('answer', 'message') and text not in str(cur.get('value')):
        text = (str(cur['value']) + ' | ' + text)[:2000]
    return d.answer(brief, {'content': text})


@dataclass
class Turn:
    intent: str
    language: str
    reply: str
    brief_row: object | None = None
    questions: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    plan: dict | None = None
    plan_id: str | None = None
    contract: dict | None = None
    interpretation: dict | None = None
    cost_usd: Decimal | None = Decimal('0')       # None = UNKNOWN / PENDING (see cost_state)
    cost_state: str = 'CONFIRMED_ZERO'
    reservation_id: str | None = None
    explained: bool = False                        # this answer explained why the open question matters
    gaps: dict | None = None                       # WP1: what the artifact still needs, and the one next question
    gate: str | None = None                        # 'spec': this turn asked for gate 1 (approve the spec)
    venice: dict | None = None                     # agent.venice: mode, the visible stage, the cost range
    blocked: list = field(default_factory=list)    # feasibility blockers said in this turn (no plan before gate 1)

    def to_dict(self, lang: str) -> dict:
        return {'intent': self.intent, 'language': self.language, 'reply': self.reply,
                'questions': [{**q.to_dict(lang), 'suggested': (self.brief_row.brief.hints.get(q.field) if self.brief_row else None)}
                              for q in self.questions],
                'actions': self.actions, 'plan_id': self.plan_id,
                'plan': _plan_view(self.plan) if self.plan else None, 'contract': self.contract,
                'interpretation': self.interpretation, 'gaps': self.gaps, 'venice': self.venice}


def _plan_view(plan: dict) -> dict:
    """What the workspace shows: no provider/model internals by default."""
    return {k: plan[k] for k in ('status', 'product_family', 'complexity', 'architecture', 'feasibility', 'layers',
                                 'critical_path', 'executable', 'budget', 'milestones', 'capability_gaps', 'graph_problems',
                                 'brief_fingerprint', 'spec_gate') if k in plan} | {
        'tasks': [{'task_id': t['task_id'], 'task_type': t['task_type'], 'department': t['department'],
                   'agent': t['responsible_agent'], 'dependencies': t['dependencies'], 'stage': t['stage'],
                   'conditional': t['conditional'], 'executable': t['executable']} for t in plan['execution_graph']['tasks']]}


_TXT = {
    'he': {'got': 'הבנתי', 'assumed': 'בחרתי עבורכם (אפשר לשנות בכל רגע)', 'ask': 'כדי להמשיך אני צריך תשובה אחת קטנה',
           'content_saved': 'שמרתי את התוכן שכתבתם בסיכום הפרויקט, בדיוק כפי שנכתב. האישור הקודם בוטל — צריך לאשר את הגרסה המעודכנת.',
           'ready_again': 'התוכנית מעודכנת ומוכנה. כדי להתחיל לבנות לחצו על "אישור והתחלת בנייה" — שום חיוב לא מתחיל לפני האישור.',
           'ready': 'יש לי תמונה מלאה. הכנתי תוכנית עבודה — אפשר לעבור עליה ולאשר. שום בנייה ושום חיוב לא מתחילים לפני אישור.',
           'blocked': 'יש דרישה שאי אפשר לבנות כרגע', 'nothing': 'לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".',
           'missing_none': 'לא חסר כלום — אפשר לעבור לסיכום ולאשר.', 'missing': 'חסר לי:', 'contra': 'יש סתירה שצריך להחליט עליה:',
           'conflict': 'קודם נקבע: {current}. עכשיו הבנתי: {proposed}. לא שיניתי — מה נכון?',
           'confirm_sensitive': 'זה נושא רגיש ({field}), אז אני צריך אישור מפורש שלכם בכפתור.',
           'corrected': 'עדכנתי',
           'cost': 'עלות הבנייה: {credits} קרדיטים. תקרת ההוצאה על מודלים לבנייה הזו: עד ${cap} (מוחזק לפני תחילת העבודה; מחויבת העלות בפועל).',
           'cost_unknown': 'את העלות המדויקת אחשב אחרי שהמפרט יאושר.', 'approve': 'כדי להתחיל, אשרו את הסיכום והעלות בכפתור "אישור והתחלת בנייה".',
           'approve_not_ready': 'עדיין אי אפשר לאשר:', 'status_none': 'עדיין לא התחילה בנייה בפרויקט הזה.',
           'status': 'הבנייה האחרונה: {status}{phase}. משימות: {done} הושלמו, {running} בתהליך, {pending} ממתינות, {failed} נכשלו.',
           'modify': 'הבנתי שתרצו לשנות את המוצר הקיים. אשרו ואשלח את השינוי לצנרת השינויים (תוצג עלות לפני ביצוע).',
           'feas_yes': '{cap}: אפשר כבר עכשיו.', 'feas_no': '{cap}: לא זמין כרגע — {reason}.{alt}',
           'recommend': 'ההמלצות שלי (כבר בתוך הסיכום, ואפשר לשנות כל אחת):', 'alt': ' חלופה: {x}.',
           'more': ' עוד {n} החלטות כאלה בלשונית "דרישות".',
           'ask_one': 'שאלה אחת לפני שממשיכים:', 'decide': 'יש החלטה אחת לפני שממשיכים:',
           'verify': 'רק לוודא — הבנתי מהבקשה: {label}. נכון?',
           'why': 'למה אני שואל: {why}', 'unsure': 'אם לא בטוחים, אפשר ללחוץ "בחרו עבורי" ואבחר {rec}. תמיד אפשר לשנות אחר כך.',
           'unsure_norec': 'אם לא בטוחים, אפשר ללחוץ "בחרו עבורי". תמיד אפשר לשנות אחר כך.',
           'options': '{q} אפשרויות: {opts}.',
           'attached_shown': '📎 {n}',
           'attached_only': 'קיבלתי {n} ושמרתי בפרויקט. עדיין אין ניתוח תמונה אוטומטי (צריך מודל עם יכולת ראייה ואישור תקציב), אז כתבו במשפט מה חשוב בה או מה לשנות.',
           'attached_note': '(שמרתי {n}; היא מועברת כהקשר לשינוי, בלי ניתוח תמונה אוטומטי.)',
           'images': lambda n: 'תמונה אחת' if n == 1 else f'{n} תמונות'},
    'en': {'got': 'Got it', 'assumed': 'I chose for you (change anything any time)', 'ask': 'To continue I need one short answer',
           'content_saved': 'I saved the content you wrote in the project summary, exactly as written. Any earlier approval is cancelled; please approve the updated version.',
           'ready_again': 'The plan is up to date. To start, press "Approve and start build"; nothing is charged before you approve.',
           'ready': 'I have the full picture and prepared a work plan you can review and approve. Nothing is built or charged before you approve.',
           'blocked': 'Something you asked for cannot be built right now', 'nothing': 'I did not spot new details. Tell me more, or ask "what is missing?".',
           'missing_none': 'Nothing is missing: you can review the summary and approve.', 'missing': 'Still missing:',
           'contra': 'There is a contradiction to decide:',
           'conflict': 'Earlier: {current}. Now I understood: {proposed}. I did not change it — which is right?',
           'confirm_sensitive': 'This is sensitive ({field}), so I need your explicit confirmation with the button.',
           'corrected': 'Updated',
           'cost': 'This build costs {credits} credits. Model spending for it is capped at ${cap} (reserved before work starts; you are charged actual usage).',
           'cost_unknown': 'I will calculate the exact cost once the spec is approved.',
           'approve': 'To start, approve the summary and cost with "Approve and start building".',
           'approve_not_ready': 'It cannot be approved yet:', 'status_none': 'No build has started in this project yet.',
           'status': 'Latest build: {status}{phase}. Tasks: {done} done, {running} running, {pending} waiting, {failed} failed.',
           'modify': 'You want to change the existing product. Confirm and I will send it to the change pipeline (cost shown before it runs).',
           'feas_yes': '{cap}: available now.', 'feas_no': '{cap}: not available right now — {reason}.{alt}',
           'recommend': 'My recommendations (already in the summary; change any of them):', 'alt': ' Alternative: {x}.',
           'more': ' {n} more such decisions are in "Requirements".',
           'ask_one': 'One question before we continue:', 'decide': 'One decision before we continue:',
           'verify': 'Just to confirm — from your request I understood: {label}. Right?',
           'why': 'Why I ask: {why}', 'unsure': 'If you are not sure, tap "Choose for me" and I will use {rec}. You can change it later.',
           'unsure_norec': 'If you are not sure, tap "Choose for me". You can change it later.',
           'options': '{q} Options: {opts}.',
           'attached_shown': '📎 {n}',
           'attached_only': 'I saved {n} in the project. Automatic image analysis is not enabled yet (it needs a vision-capable model and an approved budget), so tell me in a sentence what matters in it or what to change.',
           'attached_note': '(I saved {n}; it goes with the change as context, without automatic image analysis.)',
           'images': lambda n: 'one image' if n == 1 else f'{n} images'},
}


# Short names for decisions (directive 2026-10-11 "Conversation UX"): the
# reply names the decision in a word or two, not by repeating the question.
SHORT = {
    'he': {'audience': 'קהל', 'goal': 'מטרה', 'login': 'התחברות', 'personal_data': 'פרטים אישיים', 'access_scope': 'גישה',
           'screens': 'מסכים', 'languages': 'שפה', 'content': 'תוכן התחלתי', 'dates': 'תאריכים', 'duplicates': 'כפילויות',
           'style': 'סגנון', 'color': 'צבע', 'font': 'גופן', 'logo': 'לוגו', 'references': 'השראה'},
    'en': {'audience': 'audience', 'goal': 'goal', 'login': 'sign-in', 'personal_data': 'personal data', 'access_scope': 'access',
           'screens': 'screens', 'languages': 'language', 'content': 'starting content', 'dates': 'dates',
           'duplicates': 'duplicates', 'style': 'style', 'color': 'colour', 'font': 'font', 'logo': 'logo',
           'references': 'references'},
}
# "I don't know / what? / why?" -- explain why the open question matters and
# offer the recommendation, instead of repeating the same sentence.
def _why_prefixes():
    from ..intake.gaps import FALLBACK
    return tuple(t['_why'] for t in FALLBACK.values())


_WHY_PREFIXES = _why_prefixes()
_UNSURE_RX = (r'^\s*(מה\??|מה זה\??|למה\??|לא (יודע|יודעת|בטוח|בטוחה|הבנתי)|אין לי מושג|תסביר|תסבירי|הסבר|'
              r'\?+|what\??|why\??|i don\'?t know|not sure|no idea|what do you mean|explain|'
              r'لماذا\s*[?؟]?|ماذا\s*[?؟]?|لا أعرف|لست متأكد[ًا]*|اشرح)\s*[.!?؟]*\s*$')


def _short(field_: str, lang: str) -> str:
    q = d.BY_ID.get(field_)
    name = SHORT['he' if lang == 'he' else 'en'].get(field_)
    return name or ((q.he if lang == 'he' else q.en) if q else field_)


def _label(field_: str, value, lang: str) -> str:
    q = d.BY_ID.get(field_)
    return f'{_short(field_, lang)}: {d._label(q, value, lang) if q else value}'


class ConversationSupervisor:
    def __init__(self, *, briefs, store, gateway=None, architect: ChiefArchitect | None = None, credits: int | None = None,
                 budget_usd: Decimal = Decimal('0.50'), context=None, worker_interpreter=None,
                 reservations=None, enqueue=None):
        self.briefs = briefs            # brief repository (latest/save) -- the source of truth
        self.store = store              # conversation store (messages, plans)
        self.gateway = gateway
        self.architect = architect or ChiefArchitect()
        self.credits = credits
        self.budget_usd = budget_usd
        self.context = context or (lambda project_id: {})   # durable build/version state (read-only)
        self.worker_interpreter = worker_interpreter           # injected in tests
        self.reservations = reservations                       # intake.budget.ReservationService (migration 037)
        self.enqueue = enqueue                                 # RQ enqueue of a reservation id

    # ------------------------------------------------------------------ helpers
    def intake_mode(self, project_id, account_id=None):
        from ..intake import budget as B
        from ..intake import mode as intake_mode

        def spend():
            if self.reservations is not None and account_id:
                return (self.reservations.counted(f'project:{account_id}:{project_id}'),
                        self.reservations.counted(B.DAILY_SCOPE))
            return self.store.conversation_cost(project_id), self.store.daily_cost()
        worker_route_available = self.worker_interpreter is not None or (
            self.reservations is not None and self.enqueue is not None)
        return intake_mode.resolve_with_spend(spend, has_direct_gateway=self.gateway is not None,
                                              worker_route_available=worker_route_available)

    def _interpreter(self, project_id, account_id=None, request_key=None, task='conversation'):
        """Every paid call goes through a durable reservation (Issue #12); without
        the reservation service, authorization or budget the answer is deterministic."""
        from ..intake import budget as B
        from ..intake import mode as intake_mode
        m = self.intake_mode(project_id, account_id)
        if m.mode != intake_mode.MODEL_WORKER:
            return DeterministicInterpreter()
        if self.worker_interpreter is not None:
            if hasattr(self.worker_interpreter, 'task'):
                self.worker_interpreter.task = task
            return self.worker_interpreter
        if self.reservations is None or self.enqueue is None or not account_id:
            return DeterministicInterpreter()
        from ..intake.worker_route import ReservedWorkerInterpreter
        return ReservedWorkerInterpreter(self.reservations, self.enqueue, account_id=account_id,
                                         project_id=project_id, request_key=request_key, caps=B.caps_from_env(),
                                         task=task)

    def _feasibility(self, row) -> dict:
        """What can be built from the spec, WITHOUT a plan (gate 1 has not been passed yet)."""
        try:
            return F.assess(C.build(row.brief)).to_dict()
        except C.ContractInvalid:
            return {}

    def _messages(self, project_id):
        try:
            return self.store.messages_for(project_id, limit=500)
        except Exception:
            return []

    def _spec_ok(self, project_id, row) -> bool:
        from ..intake import approval_flow as AF
        return row is not None and AF.spec_approved(self._messages(project_id), row.fingerprint)

    def _approved_plan(self, project_id, row):
        """After gate 1 only: the verified plan saved for this exact spec (None before)."""
        if not self._spec_ok(project_id, row):
            return None, None, None
        saved = self.store.plan_for(project_id, row.fingerprint)
        if saved is None:
            return None, None, None
        try:
            contract = C.build(row.brief).to_dict()
        except C.ContractInvalid:
            contract = None
        return saved['plan'], saved['id'], contract

    def _gate1(self, turn, row, lang):
        """Step 1 of 2: the spec + the cost range, and the approve-spec control. No plan exists here."""
        from ..intake import approval_flow as AF
        t, (lo, hi) = AF.text(lang), AF.cost_range(row.brief)
        summary = '; '.join(_label(k, v['value'], lang) for k, v in list(row.brief.fields.items())[:8] if 'value' in v)
        turn.gate = 'spec'
        turn.venice = {'agent': 'agent.venice', 'mode': 'understanding', 'stage': t['stage1'],
                       'cost_range_credits': [lo, hi]}
        turn.actions.append({'type': 'approve_spec', 'brief_revision': row.revision, 'brief_fingerprint': row.fingerprint})
        return [t['stage1'] + ' —', t['spec'].format(summary=summary or '—'), t['range'].format(lo=lo, hi=hi), t['gate1']]

    def _plan(self, project_id, row):
        try:
            contract = C.build(row.brief)
        except C.ContractInvalid:
            return None, None, None
        plan = self.architect.plan(contract, budget_usd=self.budget_usd,
                                   status='PROPOSED' if row.complete else 'DRAFT')
        saved = self.store.save_plan(project_id=project_id, brief_revision=row.revision,
                                     brief_fingerprint=row.fingerprint, plan=plan) if row.complete else None
        return plan, (saved or {}).get('id'), contract.to_dict()

    # --------------------------------------------------------------------- turn
    def turn(self, *, project_id: str, account_id: str, message: str = '', answers: dict | None = None,
             request_key: str | None = None, lang: str | None = None, attachments: list | None = None) -> Turn:
        message = (message or '').strip()[:8000]
        lang = lang or language_of(message or 'שלום')
        T = _TXT['he' if lang == 'he' else 'en']
        ctx = self.context(project_id) or {}
        row = self.briefs.latest(project_id)
        shown = message or '; '.join(_label(d.BY_ID[q].field if q in d.BY_ID else q,
                                            v if v != d.DELEGATE else ('בחרו עבורי' if lang == 'he' else 'choose for me'), lang)
                                     for q, v in (answers or {}).items())
        attachments = list(attachments or [])
        if attachments and not shown:
            shown = T['attached_shown'].format(n=T['images'](len(attachments)))
        if shown:
            self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                                   brief_revision=row.revision if row else None, request_key=request_key,
                                   interpretation={'attachments': [{'id': a['id'], 'kind': a['kind']} for a in attachments]}
                                   if attachments else None)
        intent = 'answer' if answers else classify_intent(message, has_version=bool(ctx.get('latest_version_id')),
                                                          has_brief=row is not None)
        if intent == 'recommend' and self.intake_mode(project_id,account_id).paid:
            intent='requirements'
        # An explicit withdrawal refers only to a uniquely identified blocker
        # in the previous reply. Never guess which of several requirements to drop.
        if row and not answers and re.fullmatch(r'(?:אז\s+)?(?:תוותר|וותר|תוריד)\s+(?:על\s+)?זה(?:\s+כרגע)?[.!? ]*|'
                                               r'(?:skip|remove|drop)\s+(?:that|it)(?:\s+for now)?[.!? ]*', message, re.I):
            previous = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
            last_blocked = (previous[-1].get('interpretation') or {}).get('blocked') if previous else None
            blockers = [f for f in self._feasibility(row).get('findings', [])
                        if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            if last_blocked and len(blockers) == 1 and blockers[0]['item'].startswith('sign-in'):
                answers = {'login': 'none'}
                intent = 'answer'
        if attachments and not message and not answers:
            intent = 'attachment'
        turn = Turn(intent, lang, '')
        if intent == 'attachment':
            turn.brief_row = row
            turn.reply = T['attached_only'].format(n=T['images'](len(attachments)))
        elif intent in ('answer', 'requirements'):
            turn = self._requirements(project_id, account_id, row, message, answers or {}, request_key, lang, T, attachments)
        else:
            turn.brief_row = row
            if row is not None:
                turn.plan, turn.plan_id, turn.contract = self._approved_plan(project_id, row)
            turn.reply = self._answer(intent, row, turn.plan, ctx, message, T, lang)
            if intent == 'approve' and turn.plan and turn.plan.get('executable') and row and row.complete:
                turn.actions.append({'type': 'approve_build', 'brief_revision': row.revision,
                                     **({'cost': turn.plan['spec_gate']['cost']} if 'spec_gate' in turn.plan else {})})
            elif intent == 'approve' and row is not None and row.complete and not self._spec_ok(project_id, row) \
                    and self._feasibility(row).get('buildable'):
                from ..intake import approval_flow as AF
                turn.reply = ' '.join([AF.text(lang)['gate1_needed']] + self._gate1(turn, row, lang))
            if intent == 'modify':
                turn.actions.append({'type': 'confirm_modification', 'version_id': ctx.get('latest_version_id'),
                                     'request': message,
                                     **({'attachment_ids': [a['id'] for a in attachments]} if attachments else {})})
            if row is not None and intent != 'attachment':
                turn.questions = intake_agent.apply(row.brief, DeterministicInterpreter().interpret('', row.brief),
                                                    infer_defaults=False).asked if intent == 'missing' else []
        if attachments and intent != 'attachment':
            turn.reply = (turn.reply + ' ' + T['attached_note'].format(n=T['images'](len(attachments)))).strip()
        if turn.blocked and turn.plan is None:              # blocked before gate 1: edit the spec (there is no plan)
            if not any(a['type'] == 'edit_requirements' for a in turn.actions):
                turn.actions.append({'type': 'edit_requirements', 'brief_revision': turn.brief_row.revision})
        elif turn.brief_row and not (turn.plan or {}).get('executable', True):
            for action in ({'type': 'show_plan', 'brief_revision': turn.brief_row.revision},
                           {'type': 'edit_requirements', 'brief_revision': turn.brief_row.revision}):
                if not any(a['type'] == action['type'] for a in turn.actions):
                    turn.actions.append(action)
        paid = turn.reservation_id is not None
        self.store.add_message(project_id=project_id, account_id=account_id, role='assistant', content=turn.reply,
                               brief_revision=turn.brief_row.revision if turn.brief_row else None,
                               interpretation={'intent': turn.intent, **(turn.interpretation or {}),
                                               'asked': [q.id for q in turn.questions],
                                               'explained': bool(getattr(turn, 'explained', False)),
                                               'actions': turn.actions, 'plan_id': turn.plan_id,
                                               **({'gate': turn.gate} if getattr(turn, 'gate', None) else {}),
                                               **({'blocked': turn.blocked} if getattr(turn, 'blocked', None) else {}),
                                               **({'venice': turn.venice} if getattr(turn, 'venice', None) else {})},
                               interpreter=(turn.interpretation or {}).get('interpreter', 'deterministic'),
                               cost_usd=turn.cost_usd, request_key=request_key,
                               cost_state=turn.cost_state if paid else None, reservation_id=turn.reservation_id)
        return turn

    # ------------------------------------------------------------- gate 1 -> plan -> verifier -> gate 2
    def approve_spec(self, *, project_id: str, account_id: str, brief_fingerprint: str, request_key: str | None = None,
                     lang: str | None = None) -> Turn:
        """Gate 1: the customer approves THIS spec (by fingerprint). Only now is a plan made; the separate verifier
        checks it before the customer sees it; then gate 2 shows the exact cost next to the range said earlier."""
        from ..intake import approval_flow as AF
        row = self.briefs.latest(project_id)
        lang = lang or language_of(row.brief.prompt if row else 'שלום')
        t, T = AF.text(lang), _TXT['he' if lang == 'he' else 'en']
        turn = Turn('approve_spec', lang, '', row)
        shown = {'he': 'אישרתי את המפרט', 'ar': 'وافقت على المواصفات'}.get(lang, 'I approve the spec')
        current = row is not None and row.complete and brief_fingerprint == row.fingerprint
        feasible = current and self._feasibility(row).get('buildable')
        self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                               brief_revision=row.revision if row else None, request_key=request_key,
                               interpretation={'spec_approved': row.fingerprint} if feasible else
                               {'spec_approval_refused': brief_fingerprint})
        if not current or not feasible:        # never plan for a spec the customer did not see as it is now
            if row is None:
                turn.reply = T['nothing']
            elif not row.complete:
                pend = [(q.he if lang == 'he' else q.en) for q in d.pending(row.brief)]
                turn.reply = T['approve_not_ready'] + ' ' + '; '.join(pend[:4] or ['—'])
            elif not self._feasibility(row).get('buildable'):
                blocked = [f for f in self._feasibility(row).get('findings', [])
                           if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                turn.reply = T['blocked'] + ': ' + '; '.join(self._finding_message(f, lang, T) for f in blocked[:3])
            else:
                turn.reply = ' '.join([t['stale']] + self._gate1(turn, row, lang))
            return self._finish(project_id, account_id, turn, request_key)

        contract = C.build(row.brief)
        cached = self.store.plan_for(project_id, row.fingerprint)

        def make_plan(corrective=False):
            if cached is not None and not corrective:
                return cached['plan']
            return self.architect.plan(C.build(row.brief), budget_usd=self.budget_usd, status='PROPOSED')
        plan, record = AF.verified_plan(make_plan, row.brief, row.fingerprint)
        lo_hi = AF.cost_range(row.brief)
        parts = [t['stage2'] + ' —']
        turn.venice = {'agent': 'agent.venice', 'mode': 'planning', 'stage': t['stage2'], 'cost_range_credits': list(lo_hi)}
        turn.interpretation = {'verification': record}
        if plan is None:                       # the customer never sees a plan the verifier refused
            parts.append(t['refused'].format(what='; '.join(record.get('remaining') or record['problems'])[:400]))
            turn.actions.append({'type': 'edit_requirements', 'brief_revision': row.revision})
            turn.reply = ' '.join(parts)
            return self._finish(project_id, account_id, turn, request_key)
        cmp = AF.compare(lo_hi, self.credits)
        plan = {**plan, AF.GATE_KEY: {'approved_fingerprint': row.fingerprint, 'verification': record, 'cost': cmp}}
        saved = self.store.save_plan(project_id=project_id, brief_revision=row.revision,
                                     brief_fingerprint=row.fingerprint, plan=plan)
        turn.plan, turn.plan_id, turn.contract = plan, saved.get('id'), contract.to_dict()
        parts.append(t['planned'])
        if record['corrected']:
            parts.append(t['fixed'].format(what='; '.join(record['problems'])[:400]))
        if plan.get('executable'):
            parts.extend(AF.budget_lines(cmp, lang, plan.get('complexity')))
            parts.append(t['gate2'])
            turn.actions += [{'type': 'show_plan', 'brief_revision': row.revision},
                             {'type': 'approve_build', 'brief_revision': row.revision, 'cost': cmp}]
        else:
            blocked = [f for f in plan['feasibility'].get('findings', []) if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            parts.append(T['blocked'] + ': ' + '; '.join(self._finding_message(f, lang, T) for f in blocked[:3]))
            turn.actions += [{'type': 'show_plan', 'brief_revision': row.revision},
                             {'type': 'edit_requirements', 'brief_revision': row.revision}]
        turn.reply = ' '.join(parts)
        return self._finish(project_id, account_id, turn, request_key)

    def _finish(self, project_id, account_id, turn, request_key):
        self.store.add_message(project_id=project_id, account_id=account_id, role='assistant', content=turn.reply,
                               brief_revision=turn.brief_row.revision if turn.brief_row else None,
                               interpretation={'intent': turn.intent, **(turn.interpretation or {}), 'asked': [],
                                               'actions': turn.actions, 'plan_id': turn.plan_id,
                                               **({'gate': turn.gate} if getattr(turn, 'gate', None) else {}),
                                               **({'blocked': turn.blocked} if getattr(turn, 'blocked', None) else {}),
                                               **({'venice': turn.venice} if getattr(turn, 'venice', None) else {})},
                               interpreter='deterministic', cost_usd=Decimal('0'), request_key=request_key)
        return turn

    def _classify(self, project_id, row, message):
        from ..intake import complexity, lanes
        history = [m for m in self.store.messages_for(project_id, limit=9)]
        if history and history[-1].get('role') == 'customer':
            history = history[:-1]                        # the current message was stored at turn start
        confirmed = {k: f['value'] for k, f in (row.brief.fields.items() if row else ())
                     if f.get('source') in intake_agent.CONFIRMED_SOURCES}
        det = DeterministicInterpreter().interpret(message, row.brief if row else None)
        proposed = {p.field: p.value for p in det.proposals if p.confidence == 'high'}
        c = complexity.classify(message, history, confirmed=confirmed, proposed=proposed)
        return c, lanes.choose(c.level)

    def _requirements(self, project_id, account_id, row, message, answers, request_key, lang, T, attachments=()) -> Turn:
        from ..intake import lanes
        cls, lane = (self._classify(project_id, row, message) if message else (None, None))
        interp = None
        if message:
            source = (self._interpreter(project_id, account_id, request_key, task=lane['task'])
                      if lane['lane'] in lanes.MODEL_LANES else DeterministicInterpreter())
            source.history = self.store.messages_for(project_id, limit=5)[:-1]
            interp = source.interpret(message, row.brief if row else None)
        brief = row.brief if row else d.start(message or '', d.GUIDED)
        for qid, value in answers.items():
            brief = intake_agent.answer_question(brief, qid, value)
        sensitive = bool(lane and lane.get('requires_explicit_confirmation'))
        res = intake_agent.apply(brief, interp, require_confirmation=sensitive) if interp else intake_agent.apply(
            brief, DeterministicInterpreter().interpret('', brief))
        new_brief = res.brief
        # Persist only schema- and evidence-validated model decisions in the same
        # brief revision. They remain reviewable and bind to the normal approval
        # fingerprint; deterministic fallback cannot silently invent exclusions.
        if interp is not None and getattr(interp, 'semantic_decisions', None) and str(interp.interpreter).startswith('model'):
            from ..semantic_capabilities import updated_decisions
            new_brief.semantic_decisions = updated_decisions(
                new_brief.semantic_decisions, interp.semantic_decisions)
        recorded = False
        if (message and row is not None and row.complete and not res.applied and not res.conflicts and not res.corrected
                and not answers and _CONTENT_RX.search(message)):
            new_brief, recorded = _record_content(new_brief, message), True
        if len(attachments) == 1 and re.search(r'לוגו|\blogo\b', message, re.I):
            a = attachments[0]
            if re.fullmatch(r'att_[a-f0-9]{32}', a.get('id','')) and re.fullmatch(r'[a-f0-9]{64}',a.get('sha256','')):
                new_brief.assets['logo'] = {k:a[k] for k in ('id','sha256','mime','size_bytes')}
                new_brief = d.answer(new_brief, {'logo':'later'})
        # QUESTIONS-001: the gap detector decides what is asked. It reads the open discovery questions as candidates,
        # writes the values the request implies into the brief (shown as assumptions), and its ONE ordered question
        # replaces the questionnaire's list. Only a conflict with a confirmed value is still asked back first.
        unsure_now = bool(message and re.search(_UNSURE_RX, message.strip().lower(), re.I))
        gaps, gap_q = self._gaps(project_id, message, interp, answers, new_brief, lang, unsure=unsure_now)
        res.asked = (res.asked[:len(res.conflicts)] if res.conflicts else
                     [d.BY_ID[gap_q.field]] if gap_q is not None and gap_q.field in d.BY_ID else [])
        expected = row.revision if row else 0
        if row is None or new_brief.fingerprint() != row.fingerprint:
            row = self.briefs.save(project_id=project_id, account_id=account_id, brief=new_brief,
                                   expected_revision=expected, request_key=request_key)
        turn = Turn('answer' if answers and not message else 'requirements', lang, '', row, res.asked)
        turn.interpretation = interp.to_dict() if interp else None
        if turn.interpretation is not None:
            turn.interpretation.update(complexity=cls.to_dict() if cls else None, lane=lane,
                                       conflicts=res.conflicts, corrected=res.corrected)
        if interp is not None:
            turn.cost_usd = None if interp.cost_usd is None else Decimal(str(interp.cost_usd))
            turn.cost_state, turn.reservation_id = interp.cost_state, interp.reservation_id
        turn.gaps = gaps
        parts = []
        # The model's conversational advice is not an action: the authoritative
        # questions, changes, blockers and approval controls below still apply.
        if interp is not None and interp.reply and not res.conflicts:
            parts.append(interp.reply)
        stated = [x for x in res.applied if x['field'] not in {c['field'] for c in res.corrected}]
        if stated:
            parts.append(f'{T["got"]}: ' + '; '.join(_label(x['field'], x['value'], lang) for x in stated[:6]) + '.')
        if res.corrected:
            parts.append(f'{T["corrected"]}: ' + '; '.join(_label(c['field'], c['new'], lang) for c in res.corrected[:4]) + '.')
        for c in res.conflicts[:3]:
            name = (d.BY_ID[c['field']].he if lang == 'he' else d.BY_ID[c['field']].en) if c['field'] in d.BY_ID else c['field']
            if c['current'] is None:
                parts.append(T['confirm_sensitive'].format(field=name))
            else:
                parts.append(T['conflict'].format(current=_label(c['field'], c['current'], lang),
                                                  proposed=_label(c['field'], c['proposed'], lang)))
        short = [x for x in res.assumed if d.BY_ID.get(x['field']) and d.BY_ID[x['field']].kind == 'choice']
        if short:
            more = len(res.assumed) - len(short[:3])
            parts.append(f'{T["assumed"]}: ' + '; '.join(_label(x['field'], x['value'], lang) for x in short[:3])
                         + '.' + (T['more'].format(n=more) if more > 0 else ''))
        unsure = bool(message and re.search(_UNSURE_RX, message.strip().lower(), re.I))
        if row.complete and gap_q is None:
            feas = self._feasibility(row)
            if feas.get('buildable'):
                if recorded:
                    parts.append(T['content_saved'])
                if self._spec_ok(project_id, row):         # nothing changed since gate 1: the verified plan stands
                    turn.plan, turn.plan_id, turn.contract = self._approved_plan(project_id, row)
                    parts.append(T['ready_again'])
                    turn.actions.append({'type': 'show_plan', 'brief_revision': row.revision})
                else:                                      # gate 1: the spec and the range; no plan yet
                    parts.extend(self._gate1(turn, row, lang))
            else:
                blocked = [f for f in feas.get('findings', []) if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                turn.blocked = [f['item'] for f in blocked]
                parts.append(T['blocked'] + ': ' + '; '.join(
                    self._finding_message(f, lang, T) for f in blocked[:3]))
        elif res.asked:                                     # still listening: no plan while a material field is open
            if row.complete:
                turn.blocked = [f['item'] for f in self._feasibility(row).get('findings', [])
                                if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            if gap_q is not None and not res.conflicts:
                parts.append(gap_q.text)                    # the detector's question, exactly as it is in turn.gaps
                turn.explained = gap_q.text.startswith(_WHY_PREFIXES)
            else:                                           # only a conflict with a confirmed value is asked back here
                self._last_reply_was_why = False
                repeated = self._repeats(project_id, res.asked)
                explain = unsure or repeated
                parts.extend(self._ask_line(res, row, lang, T, unsure=explain))
                turn.explained = explain and not self._last_reply_was_why
        if not parts:
            parts.append(T['nothing'])
        turn.reply = ' '.join(parts)
        return turn

    def _gaps(self, project_id, message, interp, answers, brief, lang, unsure=False):
        """(gaps evidence, the one next Question or None). Per-project spec held in this process (WP1b: durable)."""
        from ..intake.families import classify_family, named_family
        from ..intake.gaps import Questioner, Spec
        from ..intake.interpreter import Proposal
        said, proposals = message, list(getattr(interp, 'proposals', ()) or ())
        if not message and answers:                   # a quick-reply button: its label is the customer's words
            labels = [(q, v, next((o.he if lang == 'he' else o.en for o in d.BY_ID[q].options if o.value == v), str(v)))
                      for q, v in answers.items() if q in d.BY_ID]
            said = '; '.join(label for _, _, label in labels)
            proposals = [Proposal(d.BY_ID[q].field, v, 'high', label) for q, v, label in labels if v != d.DELEGATE]
            if any(v == d.DELEGATE for _, v, _ in labels):
                said += ' ' + ('you decide' if lang == 'en' else 'תחליט אתה')
        if not said:
            return None, None
        specs = self.__dict__.setdefault('_gap_specs', {})
        kind, spec = named_family(said), specs.get(project_id)
        if spec is None or (kind is not None and kind != spec.kind):
            spec = specs[project_id] = Spec(kind or classify_family(said), [])
        spec.hear(said, proposals, settle=not unsure)      # "what?" keeps the question open (explained, not skipped)
        pending = [q.field for q in d.pending(brief)]
        g = spec.detect(pending)
        for name, imp in g['implied'].items():        # implied by the request: an assumption in the brief, not asked
            q = d.BY_ID.get(name)
            if q is not None and name not in brief.fields and (q.kind == 'text' or imp['value'] in {o.value for o in q.options}):
                brief.fields[name] = {'value': imp['value'], 'source': 'default', 'question_id': q.id, 'confidence': 'inferred'}
        for name, value in g['proposed'].items():     # sensitive: pre-selected, still confirmed by the customer
            brief.hints.setdefault(name, value)
        model_turn = str(getattr(interp, 'interpreter', '')).startswith('model')
        gateway = getattr(self.worker_interpreter, 'gateway', None) if model_turn else None   # one call, same budget
        q = Questioner(getattr(gateway, 'complete_json', None)).next(spec, pending, explain=unsure)
        return {**spec.detect(pending), 'question': None if q is None else q.__dict__, 'metrics': spec.metrics()}, q

    @staticmethod
    def _finding_message(f, lang, T):
        if lang == 'he' and f['item'].startswith('sign-in'):
            return 'התחברות והרשאות באתר שייבנה עדיין אינן זמינות. אפשר לערוך את דרישת ההתחברות או להשאיר אותה להמשך'
        return f['item'] + (T['alt'].format(x=f['alternative']) if f.get('alternative') else '')

    _last_reply_was_why = False

    def _prev_ready(self, project_id) -> bool:
        """The previous assistant turn already said the plan is ready (do not repeat the same sentence)."""
        try:
            prev = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
        except Exception:
            return False
        return bool(prev) and any(a.get('type') == 'show_plan' for a in ((prev[-1].get('interpretation') or {}).get('actions') or []))

    def _repeats(self, project_id, asked) -> bool:
        """The same open question was already the subject of the previous answer."""
        try:
            prev = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
        except Exception:
            return False
        if not prev:
            return False
        last = prev[-1].get('interpretation') or {}
        self._last_reply_was_why = bool(last.get('explained'))
        return bool(last.get('asked')) and last.get('asked') == [q.id for q in asked]

    def _ask_line(self, res, row, lang, T, *, unsure: bool) -> list[str]:
        """One short line per turn: verify a pre-selected value, explain why on
        "I don't know"/repeats, otherwise just ask. Never the same sentence twice."""
        q = res.asked[0]
        he = lang == 'he'
        if unsure and self._last_reply_was_why:
            opts = ' / '.join(o.he if he else o.en for o in q.options[:4])
            return [T['options'].format(q=q.he if he else q.en, opts=opts) if opts else T['ask_one']]
        if unsure:
            out = [T['why'].format(why=(q.why_he if he else q.why_en).rstrip('.') + '.')]
            rec = q.recommended if q.recommended and q.recommended != '__from_request__' else None
            out.append(T['unsure'].format(rec=d._label(q, rec, lang)) if rec and q.delegable else
                       (T['unsure_norec'] if q.delegable else ''))
            return [x for x in out if x]
        hint = row.brief.hints.get(q.field) if row is not None else None
        if hint and len(res.asked) == 1 and q.kind == 'choice':
            return [T['verify'].format(label=_label(q.field, hint, lang))]
        if res.contradictions or q.id == 'access_scope':
            return [T['decide']]
        return [T['ask_one'] if len(res.asked) == 1 else T['ask'] + ':']

    def _answer(self, intent, row, plan, ctx, message, T, lang) -> str:
        if intent == 'status':
            b = ctx.get('latest_build')
            if not b:
                return T['status_none']
            c = ctx.get('task_counts') or {}
            return T['status'].format(status=b.get('status'), phase=f' ({b["phase"]})' if b.get('phase') else '',
                                      done=c.get('SUCCEEDED', 0), running=c.get('RUNNING', 0),
                                      pending=c.get('PENDING', 0) + c.get('READY', 0), failed=c.get('FAILED', 0) + c.get('BLOCKED', 0))
        if row is None:
            return T['nothing']
        if intent == 'missing':
            pend = d.pending(row.brief)
            if not pend and not d.contradictions(row.brief):
                return T['missing_none']
            return T['missing'] + ' ' + '; '.join((q.he if lang == 'he' else q.en) for q in pend[:4])
        if intent == 'recommend':
            assumed = [(k, f['value']) for k, f in row.brief.fields.items() if f.get('source') in ('delegated', 'default')
                       and d.BY_ID.get(k) and d.BY_ID[k].kind == 'choice']
            return T['recommend'] + ' ' + '; '.join(_label(k, v, lang) for k, v in assumed[:8])
        if intent == 'cost':
            if not plan or not row.complete:               # before gate 1 the range is said, never hidden
                from ..intake import approval_flow as AF
                lo, hi = AF.cost_range(row.brief)
                return AF.text(lang)['range'].format(lo=lo, hi=hi) + ' ' + T['cost_unknown']
            return T['cost'].format(credits=self.credits if self.credits is not None else '—',
                                    cap=plan['budget']['graph_authorized_usd'])
        if intent == 'feasibility':
            return self._feasibility_answer(message, row, T)
        if intent == 'approve':
            if plan and plan.get('executable') and row.complete:
                return T['approve']
            reasons = [f['item'] for f in ((plan or {}).get('feasibility') or self._feasibility(row)).get('findings', [])
                       if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            pend = [(q.he if lang == 'he' else q.en) for q in d.pending(row.brief)]
            return T['approve_not_ready'] + ' ' + '; '.join((pend + reasons)[:4] or ['—'])
        if intent == 'modify':
            return T['modify']
        return T['nothing']

    def _feasibility_answer(self, message, row, T) -> str:
        """Answers "can we add X?" from the registries, never from a model."""
        import dataclasses
        from ..product_architect import strip_whatsapp_links
        message = strip_whatsapp_links(message)          # a WhatsApp link is a hyperlink, not an SMS capability
        contract = C.from_brief(row.brief)
        out = []
        for name, rx in _FEAS_KEYS:
            if not re.search(rx, message, re.I):
                continue
            probe = contract
            if name == 'sign-in':
                probe = dataclasses.replace(contract, authentication_requirements={'mode': 'simple', 'source': 'probe'})
            elif name in ('payments', 'email', 'sms'):
                probe = dataclasses.replace(contract, integrations=[{'kind': name, 'detected_from': 'question', 'status': 'probe'}])
            elif name == 'mobile app':
                probe = dataclasses.replace(contract, product_family='mobile_app')
            res = F.assess(probe)
            hit = [f for f in res.findings if name.split()[0] in f.item or (name == 'mobile app' and 'family' in f.item)
                   or (name == 'images' and False)]
            if name == 'publishing':
                hit = [f for f in res.findings if f.item == 'publishing']
            if name == 'images':
                from ..planning import registry_view as R
                st = R.agent_status('image_agent')
                hit = [] if st in R.VERIFIED else [F.Finding('images', F.BLOCKED, f'image generation is {st}', 'upload your own images')]
            if hit and hit[0].outcome in (F.BLOCKED, F.UNSUPPORTED, F.WITH_CONSTRAINTS):
                f = hit[0]
                # Customer wording; the registry status stays visible for the record.
                he = T is _TXT['he']
                cap = _CAP_HE.get(name, name) if he else name
                reason = (_REASON_HE.get(f.outcome, f.reason) + f' ({f.reason})') if he else f.reason
                alt = _ALT_HE.get(name, f.alternative) if he else f.alternative
                out.append(T['feas_no'].format(cap=cap, reason=reason, alt=T['alt'].format(x=alt) if alt else ''))
            else:
                out.append(T['feas_yes'].format(cap=_CAP_HE.get(name, name) if T is _TXT['he'] else name))
        return ' '.join(out) or T['nothing']
