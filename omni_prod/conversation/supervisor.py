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


def classify_intent(message: str, *, has_version: bool, has_brief: bool) -> str:
    t = (message or '').strip().lower()
    for intent in ('status', 'approve', 'cost', 'missing', 'recommend', 'feasibility'):
        if re.search(_RX[intent], t, re.I):
            return intent
    if has_version and re.search(_MODIFY_RX, t, re.I):
        return 'modify'
    return 'requirements'


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

    def to_dict(self, lang: str) -> dict:
        return {'intent': self.intent, 'language': self.language, 'reply': self.reply,
                'questions': [{**q.to_dict(lang), 'suggested': (self.brief_row.brief.hints.get(q.field) if self.brief_row else None)}
                              for q in self.questions],
                'actions': self.actions, 'plan_id': self.plan_id,
                'plan': _plan_view(self.plan) if self.plan else None, 'contract': self.contract,
                'interpretation': self.interpretation}


def _plan_view(plan: dict) -> dict:
    """What the workspace shows: no provider/model internals by default."""
    return {k: plan[k] for k in ('status', 'product_family', 'complexity', 'architecture', 'feasibility', 'layers',
                                 'critical_path', 'executable', 'budget', 'milestones', 'capability_gaps', 'graph_problems',
                                 'brief_fingerprint') if k in plan} | {
        'tasks': [{'task_id': t['task_id'], 'task_type': t['task_type'], 'department': t['department'],
                   'agent': t['responsible_agent'], 'dependencies': t['dependencies'], 'stage': t['stage'],
                   'conditional': t['conditional'], 'executable': t['executable']} for t in plan['execution_graph']['tasks']]}


_TXT = {
    'he': {'got': 'הבנתי', 'assumed': 'בחרתי עבורכם (אפשר לשנות בכל רגע)', 'ask': 'כדי להמשיך אני צריך תשובה אחת קטנה',
           'ready': 'יש לי תמונה מלאה. הכנתי תוכנית עבודה — אפשר לעבור עליה ולאשר. שום בנייה ושום חיוב לא מתחילים לפני אישור.',
           'blocked': 'יש דרישה שאי אפשר לבנות כרגע', 'nothing': 'לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".',
           'missing_none': 'לא חסר כלום — אפשר לעבור לסיכום ולאשר.', 'missing': 'חסר לי:', 'contra': 'יש סתירה שצריך להחליט עליה:',
           'conflict': 'קודם נקבע: {current}. עכשיו הבנתי: {proposed}. לא שיניתי — מה נכון?',
           'confirm_sensitive': 'זה נושא רגיש ({field}), אז אני צריך אישור מפורש שלכם בכפתור.',
           'corrected': 'עדכנתי',
           'cost': 'עלות הבנייה: {credits} קרדיטים. תקרת ההוצאה על מודלים לבנייה הזו: עד ${cap} (מוחזק לפני תחילת העבודה; מחויבת העלות בפועל).',
           'cost_unknown': 'אחשב עלות אחרי שהדרישות יהיו מלאות.', 'approve': 'כדי להתחיל, אשרו את הסיכום והעלות בכפתור "אישור והתחלת בנייה".',
           'approve_not_ready': 'עדיין אי אפשר לאשר:', 'status_none': 'עדיין לא התחילה בנייה בפרויקט הזה.',
           'status': 'הבנייה האחרונה: {status}{phase}. משימות: {done} הושלמו, {running} בתהליך, {pending} ממתינות, {failed} נכשלו.',
           'modify': 'הבנתי שתרצו לשנות את המוצר הקיים. אשרו ואשלח את השינוי לצנרת השינויים (תוצג עלות לפני ביצוע).',
           'feas_yes': '{cap}: אפשר כבר עכשיו.', 'feas_no': '{cap}: לא זמין כרגע — {reason}.{alt}',
           'recommend': 'ההמלצות שלי (כבר בתוך הסיכום, ואפשר לשנות כל אחת):', 'alt': ' חלופה: {x}.',
           'more': ' ועוד {n} (בלשונית "דרישות")'},
    'en': {'got': 'Got it', 'assumed': 'I chose for you (change anything any time)', 'ask': 'To continue I need one short answer',
           'ready': 'I have the full picture and prepared a work plan you can review and approve. Nothing is built or charged before you approve.',
           'blocked': 'Something you asked for cannot be built right now', 'nothing': 'I did not spot new details. Tell me more, or ask "what is missing?".',
           'missing_none': 'Nothing is missing: you can review the summary and approve.', 'missing': 'Still missing:',
           'contra': 'There is a contradiction to decide:',
           'conflict': 'Earlier: {current}. Now I understood: {proposed}. I did not change it — which is right?',
           'confirm_sensitive': 'This is sensitive ({field}), so I need your explicit confirmation with the button.',
           'corrected': 'Updated',
           'cost': 'This build costs {credits} credits. Model spending for it is capped at ${cap} (reserved before work starts; you are charged actual usage).',
           'cost_unknown': 'I will calculate the cost once the requirements are complete.',
           'approve': 'To start, approve the summary and cost with "Approve and start building".',
           'approve_not_ready': 'It cannot be approved yet:', 'status_none': 'No build has started in this project yet.',
           'status': 'Latest build: {status}{phase}. Tasks: {done} done, {running} running, {pending} waiting, {failed} failed.',
           'modify': 'You want to change the existing product. Confirm and I will send it to the change pipeline (cost shown before it runs).',
           'feas_yes': '{cap}: available now.', 'feas_no': '{cap}: not available right now — {reason}.{alt}',
           'recommend': 'My recommendations (already in the summary; change any of them):', 'alt': ' Alternative: {x}.',
           'more': ' and {n} more (see "Requirements")'},
}


def _label(field_: str, value, lang: str) -> str:
    q = d.BY_ID.get(field_)
    return f'{(q.he if lang == "he" else q.en) if q else field_} → {d._label(q, value, lang) if q else value}'


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
        return intake_mode.resolve_with_spend(spend, has_direct_gateway=self.gateway is not None)

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
             request_key: str | None = None, lang: str | None = None) -> Turn:
        message = (message or '').strip()[:8000]
        lang = lang or language_of(message or 'שלום')
        T = _TXT['he' if lang == 'he' else 'en']
        ctx = self.context(project_id) or {}
        row = self.briefs.latest(project_id)
        shown = message or '; '.join(_label(d.BY_ID[q].field if q in d.BY_ID else q,
                                            v if v != d.DELEGATE else ('בחרו עבורי' if lang == 'he' else 'choose for me'), lang)
                                     for q, v in (answers or {}).items())
        if shown:
            self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                                   brief_revision=row.revision if row else None, request_key=request_key)
        intent = 'answer' if answers else classify_intent(message, has_version=bool(ctx.get('latest_version_id')),
                                                          has_brief=row is not None)
        turn = Turn(intent, lang, '')
        if intent in ('answer', 'requirements'):
            turn = self._requirements(project_id, account_id, row, message, answers or {}, request_key, lang, T)
        else:
            turn.brief_row = row
            if row is not None:
                turn.plan, turn.plan_id, turn.contract = self._plan(project_id, row)
            turn.reply = self._answer(intent, row, turn.plan, ctx, message, T, lang)
            if intent == 'approve' and turn.plan and turn.plan.get('executable') and row and row.complete:
                turn.actions.append({'type': 'approve_build', 'brief_revision': row.revision})
            if intent == 'modify':
                turn.actions.append({'type': 'confirm_modification', 'version_id': ctx.get('latest_version_id'),
                                     'request': message})
            if row is not None:
                turn.questions = intake_agent.apply(row.brief, DeterministicInterpreter().interpret('', row.brief),
                                                    infer_defaults=False).asked if intent == 'missing' else []
        paid = turn.reservation_id is not None
        self.store.add_message(project_id=project_id, account_id=account_id, role='assistant', content=turn.reply,
                               brief_revision=turn.brief_row.revision if turn.brief_row else None,
                               interpretation={'intent': turn.intent, **(turn.interpretation or {}),
                                               'actions': turn.actions, 'plan_id': turn.plan_id},
                               interpreter=(turn.interpretation or {}).get('interpreter', 'deterministic'),
                               cost_usd=turn.cost_usd, request_key=request_key,
                               cost_state=turn.cost_state if paid else None, reservation_id=turn.reservation_id)
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

    def _requirements(self, project_id, account_id, row, message, answers, request_key, lang, T) -> Turn:
        from ..intake import lanes
        cls, lane = (self._classify(project_id, row, message) if message else (None, None))
        interp = None
        if message:
            source = (self._interpreter(project_id, account_id, request_key, task=lane['task'])
                      if lane['lane'] in lanes.MODEL_LANES else DeterministicInterpreter())
            interp = source.interpret(message, row.brief if row else None)
        brief = row.brief if row else d.start(message or '', d.GUIDED)
        for qid, value in answers.items():
            brief = intake_agent.answer_question(brief, qid, value)
        sensitive = bool(lane and lane.get('requires_explicit_confirmation'))
        res = intake_agent.apply(brief, interp, require_confirmation=sensitive) if interp else intake_agent.apply(
            brief, DeterministicInterpreter().interpret('', brief))
        new_brief = res.brief
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
        parts = []
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
                         + (T['more'].format(n=more) if more > 0 else '') + '.')
        if res.contradictions:
            parts.append(T['contra'])
        if row.complete:
            turn.plan, turn.plan_id, turn.contract = self._plan(project_id, row)
            feas = (turn.plan or {}).get('feasibility', {})
            if feas.get('buildable'):
                parts.append(T['ready'])
                turn.actions.append({'type': 'show_plan', 'brief_revision': row.revision})
            else:
                blocked = [f for f in feas.get('findings', []) if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                parts.append(T['blocked'] + ': ' + '; '.join(
                    f['item'] + (T['alt'].format(x=f['alternative']) if f.get('alternative') else '') for f in blocked[:3]))
        elif res.asked:
            parts.append(T['ask'] + ':')
        if not parts:
            parts.append(T['nothing'])
        turn.reply = ' '.join(parts)
        return turn

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
            if not plan or not row.complete:
                return T['cost_unknown']
            return T['cost'].format(credits=self.credits if self.credits is not None else '—',
                                    cap=plan['budget']['graph_authorized_usd'])
        if intent == 'feasibility':
            return self._feasibility_answer(message, row, T)
        if intent == 'approve':
            if plan and plan.get('executable') and row.complete:
                return T['approve']
            reasons = [f['item'] for f in (plan or {}).get('feasibility', {}).get('findings', [])
                       if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            pend = [(q.he if lang == 'he' else q.en) for q in d.pending(row.brief)]
            return T['approve_not_ready'] + ' ' + '; '.join((pend + reasons)[:4] or ['—'])
        if intent == 'modify':
            return T['modify']
        return T['nothing']

    def _feasibility_answer(self, message, row, T) -> str:
        """Answers "can we add X?" from the registries, never from a model."""
        import dataclasses
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
