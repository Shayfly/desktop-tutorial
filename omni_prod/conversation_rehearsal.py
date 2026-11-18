"""Conversation rehearsal (conversation agent, phase 4; the owner, 2026-11-17): real conversations with the live
model, on the worker host, through the real supervisor -- with no database, no project and no credit.

The agent is real (by default the production intake path, below); the customer is scripted: for every turn it answers the
question the agent asked (recorded as `asked`) with what a real customer would type, or, when nothing was asked,
with its next line. Bounded: MAX_TURNS per scenario and the gateway budget (OMNI_EXTERNAL_BUDGET_USD).

Acceptance per scenario, all measured, never judged by eye:
  no_cards      not one question card in the whole conversation
  approval      the conversation reaches the spec approval (an `approve_spec` action)
  facts         every fact the customer gave (phone, address) is in the brief the builder gets, as written
  model         the replies were written by a model (the interpreter name), not by the rules alone
Cost (the interpreter's metered USD) and the number of turns are reported.

The path (the owner's human test, 2026-11-17): by default the agent runs on the PRODUCTION path -- the gateway the intake
worker builds for a reservation (reservation_worker.build_gateway), from the quote of the newest settled production
reservation, read from the database (CLAUDE.md section 4: global data from a global source). Its provider, allowed
models, price ceiling and per-call amount are production's own. The first version ran on the routed gateway, which
production intake does not use (production runs through Venice): it passed on Sonnet while every real conversation ran
on Haiku. Every call's real model is recorded (`provider_models`). REHEARSAL_PATH=routed keeps the old path.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

MAX_TURNS = 14
TYPED = {'content_only': 'כן, רק להציג מידע ומחירים, לא שומרים כלום מהמבקרים',
         'audience': 'לקוחות שלי ואנשים מהאזור', 'personal_data': 'לא, רק הטלפון שלי מופיע באתר',
         'login': 'בלי התחברות', 'storage_intent': 'רק פרטי העסק', 'access_scope': 'לא לשמור פרטים',
         'unavailable': 'לבנות בלי זה'}
SCENARIOS = {
    'doors': {'lines': ['''שם העסק: 148 דלתות בהנהלת: נסים אוחנה טלפון: 050-345-6723 אזור שירות: אשקלון, אשדוד, קרית גת, שדרות והסביבה
מה זה: התקנת דלתות ממד פולימריות ודלתות פנים. עבודה עצמאית, בלי קבלן ביניים, אספקה והתקנה באותו יום.
המבצע: דלת ממד פולימרית, 1,390 ₪ כולל הובלה והרכבה, אחריות שנה על ההתקנה.
טון: ישיר, מקצועי, בגובה העיניים.

מבנה הדף:
הירו — "דלת ממד פולימרית. 1,390 ₪ כולל הובלה והרכבה." שני כפתורים: וואטסאפ ראשי, חיוג משני.
מה כלול במחיר — הובלה, הרכבה, פירוק הדלת הישנה, אחריות שנה על ההתקנה.
שאלות נפוצות — חמש, עם תשובות אמיתיות.
צור קשר — טלפון לחיץ, כפתור וואטסאפ גדול. בלי טופס.

החלטות מפורשות: דף סטטי. בלי סל, בלי תשלום, בלי טופס הרשמה. בלי קרוסלה.'''],
              'facts': ['050-345-6723']},
    'butcher': {'lines': ['אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456. שעות: ראשון עד חמישי 8:00 עד '
                          '19:00, שישי 7:00 עד 14:00.'],
                'facts': ['04-8123456', 'הרצל 12']},
    'bare': {'lines': ['אתר', 'למספרה שלי, "תספורת טובה" בחולון, טלפון 03-5550000', 'מחירון ותיאום תור בוואטסאפ',
                       'נקי ומודרני'],
             'facts': ['03-5550000']},
}


class MemoryBriefs:
    """In-process brief repository (the same contract as brief_repository.PostgresBriefRepository): no database."""
    class Row:
        def __init__(self, revision, brief):
            from . import discovery as d
            self.revision, self.brief = revision, brief
            self.complete, self.fingerprint = d.complete(brief), brief.fingerprint()

    def __init__(self):
        self.rows: dict[str, list] = {}

    def latest(self, project_id):
        return (self.rows.get(project_id) or [None])[-1]

    def save(self, *, project_id, account_id, brief, expected_revision, request_key=None):
        from . import discovery as d
        from .brief_repository import StaleBrief
        current = self.latest(project_id)
        if (current.revision if current else 0) != expected_revision:
            raise StaleBrief('stale')
        row = self.Row(expected_revision + 1, d.Brief.from_dict(json.loads(json.dumps(brief.to_dict()))))
        self.rows.setdefault(project_id, []).append(row)
        return row


class _Supervisor:
    """The real ConversationSupervisor with the live model interpreter injected (no reservation, no database)."""

    def __new__(cls, interpreter):
        from .conversation.store import MemoryConversationStore
        from .conversation.supervisor import ConversationSupervisor

        class Live(ConversationSupervisor):
            def _interpreter(self, project_id, account_id=None, request_key=None, task='conversation'):
                gateway = getattr(interpreter, 'gateway', None)
                if gateway is not None:
                    gateway.task = task                      # conversation or conversation_complex, as the lane says
                return interpreter
        return Live(briefs=MemoryBriefs(), store=MemoryConversationStore(), credits=10,
                    context=lambda p: {})


PATH_ENV = 'REHEARSAL_PATH'
PATHS = ('production', 'routed', 'agent')


def production_quote(pool) -> dict:
    """The newest settled production intake reservation's quote, with its id and per-call amount. Loud when none."""
    with pool.connection() as conn:
        row = conn.execute("SELECT id, quoted_usd, quote FROM intake_reservations WHERE state = 'SETTLED' "
                           "AND quote IS NOT NULL ORDER BY settled_at DESC NULLS LAST, updated_at DESC LIMIT 1").fetchone()
    if row is None:
        raise SystemExit('no settled production intake reservation: the production path cannot be rehearsed')
    rid, quoted, quote = row[0], row[1], row[2]
    quote = quote if isinstance(quote, dict) else json.loads(quote)
    return {'reservation_id': rid, 'quoted_usd': Decimal(str(quoted)), 'quote': quote}


def project_cap(quote: dict) -> Decimal:
    """The per-conversation cap production reserved this quote under (its caps snapshot, the database): the worker has
    no OMNI_INTAKE_MODEL_BUDGET_USD of its own, and a cap is never guessed."""
    caps = quote.get('caps') or {}
    found = [v.get('cap') for k, v in caps.items() if str(k).startswith('project:') and isinstance(v, dict)]
    if len(found) != 1 or found[0] in (None, ''):
        raise SystemExit(f'the production quote carries no single project cap snapshot ({sorted(caps)}): the agent '
                         'path cannot hold the conversation to it')
    cap = Decimal(str(found[0]))
    if not cap.is_finite() or cap <= 0:
        raise SystemExit(f'the production project cap snapshot is not a positive amount ({found[0]!r})')
    return cap


def agent_quote(prod: dict) -> dict:
    """The conversation agent's quote (owner 2026-11-18): production's newest quote (its token bounds, the database) with
    the agent's Venice profile from the code the API quotes with (conversation_agent.venice_profile) -- one source for
    both, never a list typed into the workflow."""
    from .intake import conversation_agent as agent
    q = dict(prod['quote'])
    if q.get('provider') != 'venice':
        raise SystemExit(f"the newest production quote is not a Venice quote ({q.get('provider')!r}): the agent "
                         'profile cannot be rehearsed on it')
    p = agent.venice_profile()
    q.update({'mode': 'agent', 'venice_select': p['select'], 'venice_allowed_models': list(p['models']),
              'allowed_models': ['venice:' + m for m in p['models']],
              'venice_ceiling_usd_per_m': [str(x) for x in p['ceiling']]})
    return q


class ProductionPathGateway:
    """Every call builds the gateway the intake worker builds for a reservation, from production's own quote. The
    per-call amount is the quote's bound recomputed for THIS call's input (the same formula as budget.quote), so a
    longer conversation is not refused by an amount priced for a shorter one. Records the model every call ran on."""

    accepts_call_id = True

    def __init__(self, quote: dict, *, cap_usd: Decimal | None = None, max_turns: int | None = None):
        self.quote = quote
        self.recorder = None
        self.models_used: list[str] = []
        # the agent path holds each conversation to the production limits, checked as reserve() checks them: before
        # the call, at its worst case (an unknown cost counts at its worst case, never $0)
        self.cap_usd, self.max_turns = cap_usd, max_turns
        self.spent, self.turns = Decimal('0'), 0

    def reset(self) -> None:
        self.spent, self.turns, self.models_used = Decimal('0'), 0, []

    def amount(self, system: str, user: str, max_tokens: int) -> Decimal:
        from decimal import ROUND_CEILING
        q = self.quote
        if q.get('provider') == 'venice':
            cin, cout = (Decimal(str(x)) for x in q['venice_ceiling_usd_per_m'])
            tokens_in = len(f'{system}{user}'.encode('utf-8')) + 64
            return ((Decimal(tokens_in) * cin + Decimal(max_tokens) * cout) / Decimal(1_000_000)).quantize(
                Decimal('0.00000001'), rounding=ROUND_CEILING)
        from .intake import budget as B
        return B.quote(system=system, user=user, max_tokens=max_tokens, task='conversation',
                       models=tuple(q.get('allowed_models') or ()) or None).amount_usd

    def complete_json(self, *, system: str, user: str, max_tokens: int, call_id: str,
                      task: str = 'conversation') -> dict:
        from types import SimpleNamespace
        from .intake.reservation_worker import build_gateway
        q = self.quote
        # building never contacts a provider: if it fails, THIS call has an empty ledger (not contacted), never the
        # previous call's
        self.recorder = SimpleNamespace(records=[])
        amount = self.amount(system, user, max_tokens)
        from .intake import budget as B
        if self.max_turns is not None and self.turns >= self.max_turns:
            raise B.TurnCapReached('project:rehearsal', self.max_turns, self.turns, 0)
        if self.cap_usd is not None and self.spent + amount > self.cap_usd:
            raise B.BudgetExceeded('project:rehearsal', self.cap_usd, self.spent, amount)
        gateway = build_gateway(amount, tuple(q.get('allowed_models') or ()), q)
        self.recorder = getattr(gateway, 'recorder', None)
        try:
            return gateway.complete_json(system=system, user=user, max_tokens=max_tokens, task=task, call_id=call_id)
        finally:
            records = [r for r in (getattr(self.recorder, 'records', None) or []) if getattr(r, 'call_id', None) == call_id]
            for r in records:
                if getattr(r, 'model', None):
                    self.models_used.append(str(r.model))
            if records:
                self.turns += 1
                costs = [getattr(r, 'provider_reported_cost_usd', None) for r in records]
                self.spent += sum(costs) if all(c is not None for c in costs) else amount


class RoutedPathGateway:
    """The routed gateway under task `conversation`. From the gateway's own route events of each call (by its call id)
    it records which route answered and which refused, and why: run 44263232985 (2026-11-18) passed on this path with
    provider_models=None, so it could not say whether Sonnet answered or a fallback did.

    The routed gateway's ledger keeps every attempt of the run; each turn is priced by its own call id
    (reservation_worker.meter), never by the whole ledger -- which is what made every routed rehearsal cost to
    2026-11-18 invalid."""

    accepts_call_id = True

    def __init__(self, routed):
        from .attempt_ledger import TaskTaggedGateway
        if not isinstance(getattr(routed, 'events', None), list) or \
                not isinstance(getattr(getattr(routed, 'recorder', None), 'records', None), list) or \
                not getattr(routed, 'accepts_call_id', False):
            raise SystemExit('the routed gateway keeps no route events, no attempt ledger or no call ids: the '
                             'rehearsal could not say which model answered or what a turn cost')
        self.routed = routed
        self.tagged = TaskTaggedGateway(routed, 'conversation')
        self.recorder = routed.recorder
        self.models_used: list[str] = []
        self.route_failures: list[str] = []

    @property
    def task(self) -> str:
        return self.tagged.task

    @task.setter
    def task(self, value: str) -> None:
        # the lane's task (conversation / conversation_complex) reaches the routed gateway: _Supervisor sets it per turn
        self.tagged.task = value

    def complete_json(self, *, call_id: str, **kwargs):
        if not call_id:
            raise ValueError('a rehearsal call without a call id cannot be priced or attributed')
        try:
            return self.tagged.complete_json(call_id=call_id, **kwargs)
        finally:
            for e in self.routed.events:
                if getattr(e, 'call_id', '') != call_id:
                    continue
                if e.ok:
                    self.models_used.append(f'{e.provider}:{e.model}' if e.model else e.provider)
                else:
                    self.route_failures.append(f'{e.provider}: {e.error}'[:240])


def run_scenario(name: str, interpreter) -> dict:
    from . import discovery as d
    spec = SCENARIOS[name]
    sup = _Supervisor(interpreter)
    lines, turns, cards, cost, models, reached = list(spec['lines']), [], 0, Decimal('0'), set(), False
    unknown = 0
    message = lines.pop(0)
    for _ in range(MAX_TURNS):
        t = sup.turn(project_id=name, account_id='rehearsal', message=message, lang='he')
        meta = (sup.store.messages_for(name)[-1].get('interpretation') or {})
        cards += len(t.questions)
        if t.cost_usd is None:           # UNKNOWN / PENDING: never counted as $0
            unknown += 1
        else:
            cost += t.cost_usd
        models.add(str(meta.get('interpreter') or (t.interpretation or {}).get('interpreter') or 'deterministic'))
        turns.append({'customer': message[:160], 'agent': t.reply[:600], 'asked': meta.get('asked') or [],
                      'cost_usd': None if t.cost_usd is None else str(t.cost_usd), 'cost_state': t.cost_state})
        if any(a['type'] == 'approve_spec' for a in t.actions):
            reached = True
            break
        asked = [x for x in meta.get('asked') or [] if x in TYPED]
        message = TYPED[asked[0]] if asked else (lines.pop(0) if lines else 'תחליטו אתם על השאר')
    row = sup.briefs.latest(name)
    built_from = (row.brief.prompt + '\n' + d.requirements_text(row.brief)) if row else ''
    missing = [f for f in spec['facts'] if f not in built_from]
    used = getattr(getattr(interpreter, 'gateway', None), 'models_used', None)
    result = {'scenario': name, 'turns': len(turns), 'cards': cards, 'approval': reached, 'facts_missing': missing,
              'models': sorted(models), 'cost_usd': None if unknown else str(cost), 'cost_unknown_turns': unknown,
              'transcript': turns, 'provider_models': sorted(set(used)) if used is not None else None,
              'route_failures': list(getattr(getattr(interpreter, 'gateway', None), 'route_failures', None) or [])[:20]}
    result['passed'] = accepted(cards=cards, reached=reached, missing=missing, models=models)
    return result


def accepted(*, cards: int, reached: bool, missing, models) -> bool:
    """No card, the approval reached, no fact missing, and at least one reply written by a model."""
    return cards == 0 and reached and not missing and any(str(m).startswith('model') for m in models)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.environ['OMNI_INTAKE_AGENT'] = '1'
    names = [n for n in (argv or list(SCENARIOS)) if n]
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        raise SystemExit(f'unknown scenario(s): {unknown}; known: {sorted(SCENARIOS)}')
    from .intake.interpreter import ModelInterpreter
    path = os.environ.get(PATH_ENV, 'production').strip() or 'production'
    if path not in PATHS:
        raise SystemExit(f'{PATH_ENV} must be one of {PATHS}, not {path!r}')
    if path in ('production', 'agent'):
        from .db import DatabasePool
        pool = DatabasePool(os.environ['OMNI_DATABASE_URL'], min_size=1, max_size=2).open()
        try:
            prod = production_quote(pool)
        finally:
            pool.close()
        q = prod['quote'] if path == 'production' else agent_quote(prod)
        print(f"::notice title=conversation path::{path} -- the quote of reservation {prod['reservation_id']}"
              f"{' with the agent profile from the code' if path == 'agent' else ''}: "
              f"provider {q.get('provider') or 'routed'}, allowed {q.get('allowed_models')}, "
              f"select {q.get('venice_select', 'cheapest')}, ceiling {q.get('venice_ceiling_usd_per_m')}, "
              f"max_tokens {q.get('max_tokens')}")
        if path == 'agent':                           # the production limits, per conversation (owner 2026-11-18)
            from .intake import conversation_agent as agent
            gateway = ProductionPathGateway(q, cap_usd=project_cap(prod['quote']), max_turns=agent.MAX_TURNS)
            print(f"::notice title=conversation limits::per conversation: {agent.MAX_TURNS} turns, "
                  f"${gateway.cap_usd} (worst case checked before each call, as reserve() does)")
        else:
            gateway = ProductionPathGateway(q)
    else:
        from .investor_app import _live_components
        _, inner = _live_components()
        gateway = RoutedPathGateway(getattr(inner, '_inner', inner))
        print('::notice title=conversation path::routed -- NOT the production intake path')
    results = []
    for n in names:
        gateway.models_used = []                      # per scenario: which models answered THIS conversation
        if path == 'agent':
            gateway.reset()                           # each scenario is its own conversation: its own 8 and $0.15
        if path == 'routed':
            gateway.route_failures = []
        results.append(run_scenario(n, ModelInterpreter(gateway)))
    for r in results:
        print('CONVERSATION ' + json.dumps(r, ensure_ascii=False))
        level = 'notice' if r['passed'] else 'error'
        print(f"::{level} title=conversation {r['scenario']}::passed={r['passed']} turns={r['turns']} "
              f"cards={r['cards']} approval={r['approval']} facts_missing={r['facts_missing']} "
              f"models={r['models']} provider_models={r['provider_models']} cost_usd={r['cost_usd']} "
              f"cost_unknown_turns={r['cost_unknown_turns']}")
        for f in r['route_failures']:
            print(f"::warning title=conversation {r['scenario']} route refused::{f}".replace('\n', ' '))
        for i, t in enumerate(r['transcript'], 1):
            print(f"::notice title=conversation {r['scenario']} turn {i}::cost_usd={t['cost_usd']} ({t['cost_state']}) "
                  f"|| customer: {t['customer']} || agent: {t['agent']}".replace('\n', ' ')[:1800])
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
