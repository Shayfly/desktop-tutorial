"""M7: intake as a conversation -- one agent from the first message to the architecture handoff.

Founder spec 2026-10-24:
  1. A conversation, not a form: the discovery questions are the agent's skill (intake.skill).
  2. The agent PROPOSES what it understood and the customer corrects it. It does not interrogate.
  3. The product kind is discovered from the customer's words, never assumed; an unsupported kind is said aloud.
  4. Initiative in asking, discipline in binding: the agent may ask, it may never bind without a source.
  5. Every requirement has a source record: a span of the customer's words. No span -> not binding. USBR = 0.
  6. Defaults are tagged and shown: "ביקשת" (you asked) vs "הנחנו" (we assumed). A default never drives a gate.
  7. A question is asked only when it is build-blocking AND ambiguous AND a wrong answer changes the artifact.
  8. A requirement without a source is not thrown away: it is kept, flagged, and forbidden to drive a gate.

Deterministic and free: no model is called here. Every stated requirement is a regex match over the
customer's own message, recorded as (message, start, end, quote) and re-verified by `sources.Ledger`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import skill as S
from .families import EXECUTABLE
from .sources import ASSUMED, STATED, UNSOURCED, Ledger, Requirement, Span

# ---------------------------------------------------------------- what the agent listens for

_NEG = re.compile(r"(?:^|[\s,.(])(?:בלי|ללא|לא|אין|אל|without|no|not|don'?t|never)(?:\s+\S+){0,2}\s*$", re.I)

# (key, value, pattern). Order inside a key does not matter: the earliest match in a message wins,
# a later message overrides an earlier one (the customer corrected us).
_KIND = (
    ('mobile_app', r'אנדרואיד|android|\bios\b|אייפון|iphone|app store|play store|חנות האפליקציות|'
                   r'אפליקציה (?:לנייד|לטלפון|לאייפון|לאנדרואיד)|אפליקציית מובייל|mobile app|native app'),
    ('game', r'משחק|\bgames?\b'),
    ('ai_agent', r'סוכן ai|צ\'?אטבוט|chatbot|\bai agent\b'),
    ('media', r'סרטון|וידאו|וידיאו|\bvideo\b|פודקאסט|podcast'),
    ('automation', r'אוטומציה|\bautomation\b|\bworkflow\b'),
    ('website', r'אתר תדמית|דף נחיתה|landing page|אתר|\bwebsite\b|\bsite\b|portfolio|תיק עבודות|בלוג|\bblog\b'),
    ('web_app', r'אפליקצי(?:ה|ית)|מערכת|\bweb app\b|\bapp\b|dashboard|דשבורד|כלי (?:ניהול|פנימי)'),
)
_UNSUPPORTED_HE = {'mobile_app': 'אפליקציה לחנות (Android / iOS)', 'game': 'משחק', 'ai_agent': 'סוכן AI',
                   'media': 'הפקת מדיה (וידאו / אודיו)', 'automation': 'אוטומציה'}
_ALTERNATIVE_HE = {'mobile_app': 'אפליקציית ווב שנפתחת בדפדפן ועובדת גם בנייד',
                   'game': 'אתר או אפליקציית ווב', 'ai_agent': 'אפליקציית ווב', 'media': 'אתר שמציג את המדיה שתעלה',
                   'automation': 'אפליקציית ווב'}

_BEHAVIOR = (
    ('data_create', r'לקבוע|קביעת|לזמן|זימון|להזמין|הזמנ[הות]|להירשם|הרשמה|להוסיף|הוספת|לשמור|שמירת|טופס|לרשום|רישום|'
                    r'\bbook(?:ing)?s?\b|\bappointments?\b|\breservations?\b|sign[- ]?up|\bregister\b|\border\b|'
                    r'\badd\b|\bsubmit\b|\bform\b'),
    ('data_update', r'לערוך|עריכה|לעדכן|עדכון|לשנות (?:את )?(?:התור|תור|ההזמנה|הזמנה|פרטים)|לדחות|\bedit\b|\bupdate\b|reschedule'),
    ('data_delete', r'למחוק|מחיקה|לבטל|ביטול|\bcancel\b|\bdelete\b|\bremove\b'),
)
# Explicit "content only" words. "Tell about the business" is a content SIGNAL (it shows information) but does not
# by itself say that nothing is stored; that stays an assumption.
_CONTENT_ONLY = r'אתר תדמית|דף נחיתה|landing page|brochure|רק מציג|רק להציג|לא שומר כלום|בלי שמירת (?:נתונים|מידע)'
_CONTENT_SIGNAL = r'(?:לספר|תספר|ספר) (?:קצת )?על|להציג|מציג|showcase|about (?:us|the business)'
_LOGIN = (('roles', r'הרשאות|תפקידים|\broles\b|\badmin\b'),
          ('simple', r'התחברות|להתחבר|סיסמ[הא]|\blog ?in\b|sign[- ]?in|password'))
_PERSONAL = r'טלפון|מספר נייד|אימייל|מייל|דוא"ל|כתובת מגורים|ת\.?ז|שם מלא|פרטים אישיים|\bphone\b|e-?mail|personal (?:data|details)'
_PUBLIC = r'לציבור|פתוח לכולם|לכל הגולשים|כל אחד יוכל|\bpublic\b'
_LANG = (('he_en', r'עברית ואנגלית|hebrew and english'), ('en', r'באנגלית|in english'), ('he', r'בעברית|in hebrew'))


_NEG_WORD = re.compile(r"בלי|ללא|לא|אין|אל|without|no|not|don'?t|never", re.I)


class _Hit:
    """A match whose span starts at the negation word when there is one, so the quote is what was really said
    ("בלי התחברות", not "התחברות")."""
    def __init__(self, text: str, m: re.Match, neg_start: int | None):
        self._start = m.start() if neg_start is None else neg_start
        self._end = m.end()
        self._text = text

    def start(self):
        return self._start

    def end(self):
        return self._end

    def group(self, _=0):
        return self._text[self._start:self._end]


def _negation_start(text: str, start: int) -> int | None:
    lo = max(0, start - 40)
    window = text[lo:start]
    if not _NEG.search(window):
        return None
    words = [w for w in _NEG_WORD.finditer(window)
             if (w.start() == 0 or not window[w.start() - 1].isalnum())
             and (w.end() == len(window) or not window[w.end()].isalnum())]
    return lo + words[-1].start() if words else None


def _matches(text: str, pattern: str):
    for m in re.finditer(pattern, text, re.I):
        neg = _negation_start(text, m.start())
        yield _Hit(text, m, neg), neg is not None


# ---------------------------------------------------------------- the turn the customer sees


@dataclass
class AgentTurn:
    reply: str
    product_kind: str | None
    supported: bool | None
    asked: list[dict] = field(default_factory=list)          # {field, proposal}
    stated: list[dict] = field(default_factory=list)          # "ביקשת"
    assumed: list[dict] = field(default_factory=list)         # "הנחנו"
    unsourced: list[dict] = field(default_factory=list)       # kept, flagged
    required_behaviors: list[str] = field(default_factory=list)   # binding only: what a gate may require
    verification: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class IntakeConversationAgent:
    """Holds the customer's messages; every turn re-reads all of them (corrections included)."""

    MAX_QUESTIONS = 2

    def __init__(self, messages: list[str] | None = None):
        self.messages: list[str] = list(messages or [])
        self.claims: list[Requirement] = []          # claims from outside the words (e.g. a model): never binding

    # ---- input
    def say(self, message: str) -> AgentTurn:
        self.messages.append(message or '')
        return self.turn()

    def answer(self, field_: str, value: str) -> AgentTurn:
        """A quick-reply button is the customer's words too: its label is recorded as a message and is the source."""
        q = S.entry(field_).question
        label = next((o.he for o in (q.options if q else ()) if o.value == value), None)
        if label is None:
            raise ValueError(f'{field_}: unknown option {value!r}')
        self.messages.append(label)
        self._answers = getattr(self, '_answers', {}) | {len(self.messages) - 1: (field_, value)}
        return self.turn()

    def claim(self, key: str, value, origin: str) -> None:
        """Something asserted without the customer's words (a model's reading, a template). Kept and flagged."""
        self.claims.append(Requirement(key, value, UNSOURCED, None, why=f'from {origin}, not from the customer\'s words'))

    # ---- understanding
    def ledger(self) -> Ledger:
        led = Ledger(self.messages)
        answers = getattr(self, '_answers', {})
        for i, text in enumerate(self.messages):
            if i in answers:
                field_, value = answers[i]
                led.add(Requirement(field_, value, STATED, Span(i, 0, len(text), text)))
                continue
            self._read(led, i, text)
        self._derive(led)
        for c in self.claims:
            led.add(c)
        self._assume(led)
        return led

    def _stated(self, led, key, value, i, m):
        led.add(Requirement(key, value, STATED, Span(i, m.start(), m.end(), m.group(0))))

    def _read(self, led: Ledger, i: int, text: str) -> None:
        kinds = []
        for kind, pat in _KIND:
            for m, neg in _matches(text, pat):
                if not neg:
                    kinds.append((m.start(), kind, m))
        if kinds:
            # The first product the customer names is the product ("a site with a video" is a site). Native mobile
            # words are the exception: "an app ... for Android" names a different product than "an app", so they win.
            native = [k for k in kinds if k[1] == 'mobile_app']
            _, kind, m = min(native or kinds, key=lambda k: k[0])
            self._stated(led, 'product_kind', kind, i, m)
        for kind, pat in _BEHAVIOR:
            for m, neg in _matches(text, pat):
                self._stated(led, f'behavior.{kind}', not neg, i, m)
                break
        for m, neg in _matches(text, _CONTENT_ONLY):
            self._stated(led, 'content_only', 'yes', i, m)
            break
        for m, neg in _matches(text, _CONTENT_SIGNAL):
            if not neg:
                self._stated(led, 'content_signal', True, i, m)
                break
        for value, pat in _LOGIN:
            hit = next(_matches(text, pat), None)
            if hit:
                m, neg = hit
                self._stated(led, 'login', 'none' if neg else value, i, m)
                break
        for m, neg in _matches(text, _PERSONAL):
            self._stated(led, 'personal_data', 'no' if neg else 'yes', i, m)
            break
        for m, neg in _matches(text, _PUBLIC):
            if not neg:
                self._stated(led, 'access_scope', 'public', i, m)
                break
        for value, pat in _LANG:
            hit = next(_matches(text, pat), None)
            if hit and not hit[1]:
                self._stated(led, 'languages', value, i, hit[0])
                break

    def _derive(self, led: Ledger) -> None:
        """Requirements that follow from words already stated keep THOSE words as their source."""
        kind = led.current('product_kind')
        if kind is not None and kind.binding and kind.value in EXECUTABLE:
            led.add(Requirement('behavior.data_read', True, STATED, kind.span))
        create = led.current('behavior.data_create')
        if (create is not None and create.binding and create.value is True and led.current('content_only') is None
                and kind is not None and kind.binding and kind.value == 'website'):
            led.add(Requirement('content_only', 'no', STATED, create.span))   # "a form that saves" is not content-only

    def _assume(self, led: Ledger) -> None:
        kind = led.current('product_kind')
        kind_value = kind.value if kind is not None else None
        create = led.current('behavior.data_create')
        saves = bool(create is not None and create.binding and create.value is True)
        for e in S.ENTRIES.values():
            if led.current(e.field) is not None:
                continue
            if e.field == 'content_only' and kind_value != 'website':
                continue
            if e.field in ('dates', 'duplicates', 'personal_data') and not saves:
                continue
            led.add(Requirement(e.field, e.assume_value, ASSUMED, None, why=e.assume_he))
        if kind_value == 'web_app' and led.current('platform') is None:
            led.add(Requirement('platform', 'web', ASSUMED, None,
                                why='אפליקציית ווב שנפתחת בדפדפן ועובדת גם בנייד — לא אפליקציה לחנות (Android / iOS)'))

    def ambiguous(self, field_: str, led: Ledger) -> bool:
        cur = led.current(field_)
        if cur is not None and cur.binding:
            if field_ == 'content_only' and cur.value == 'yes':
                create = led.current('behavior.data_create')
                return bool(create is not None and create.binding and create.value is True)   # said both
            return False
        kind = led.current('product_kind')
        create = led.current('behavior.data_create')
        saves = bool(create is not None and create.binding and create.value is True)
        personal = led.current('personal_data')
        personal_yes = bool(personal is not None and personal.binding and personal.value == 'yes')
        if field_ == 'content_only':
            signal = led.current('content_signal')
            return bool(kind is not None and kind.value == 'website' and not saves and signal is None)
        if field_ == 'personal_data':
            return saves
        if field_ == 'login':
            return personal_yes
        if field_ == 'access_scope':
            login = led.current('login')
            return personal_yes and (login is None or not login.binding or login.value == 'none')
        return False

    def may_ask(self, field_: str, led: Ledger) -> tuple[bool, str]:
        """Rule 7, with the reason, so a refused question is explainable."""
        e = S.ENTRIES.get(field_)
        if e is None:
            return False, 'not an intake question'
        if not e.build_blocking:
            return False, 'not build-blocking: a default is shown instead'
        if not e.changes_artifact:
            return False, 'a wrong value does not change what is built'
        if not self.ambiguous(field_, led):
            return False, 'the customer\'s words already settle it (or it does not apply)'
        return True, 'build-blocking, ambiguous and changes the artifact'

    # ---- the turn
    def turn(self) -> AgentTurn:
        led = self.ledger()
        kind = led.current('product_kind')
        supported = None if kind is None else kind.value in EXECUTABLE
        asked = []
        for f in ('content_only', 'personal_data', 'login', 'access_scope'):
            ok, _ = self.may_ask(f, led)
            if ok and supported is not False and len(asked) < self.MAX_QUESTIONS:   # the kind comes first
                asked.append({'field': f, 'proposal': S.entry(f).propose_he})
        stated = [r.to_dict() for r in led.binding() if r.key != 'content_signal']
        assumed = [r.to_dict() for r in led.assumed()]
        behaviors = sorted({r.key.split('.', 1)[1] for r in led.binding()
                            if r.key.startswith('behavior.') and r.value is True})
        if supported is False:
            behaviors = []                      # nothing is built for an unsupported kind, so nothing is required
        turn = AgentTurn('', kind.value if kind else None, supported, asked, stated, assumed,
                         [r.to_dict() for r in led.unsourced()], behaviors, led.verify())
        turn.reply = self._reply(turn, kind)
        return turn

    def _reply(self, t: AgentTurn, kind) -> str:
        parts = []
        if kind is None:
            parts.append('ספר לי במשפט מה אתה רוצה שנבנה — אתר שמציג מידע, או אפליקציה שבה שומרים ומעדכנים דברים?')
        else:
            if t.supported is False:
                parts.append(f'כתבת "{kind.span.quote}" — {_UNSUPPORTED_HE.get(kind.value, kind.value)}. '
                             f'את זה עוד אין לנו דרך אמיתית לבנות ולבדוק, אז לא אבטיח את זה. '
                             f'מה שאפשר עכשיו: {_ALTERNATIVE_HE.get(kind.value, "אפליקציית ווב")}.')
            parts.append('הבנתי ככה — תתקן אותי אם טעיתי:')
            said = [f'{_label(r)} ("{r["source"]["quote"]}")' for r in t.stated if _label(r)]
            if said:
                parts.append('ביקשת: ' + '; '.join(said[:4]) + '.')
            asking = {q['field'] for q in t.asked}
            shown = [r['why'] for r in sorted(t.assumed, key=lambda r: _SHOWN_ASSUMPTIONS.index(r['key'])
                                              if r['key'] in _SHOWN_ASSUMPTIONS else 99)
                     if r['key'] in _SHOWN_ASSUMPTIONS and r['key'] not in asking]
            if shown:
                parts.append('הנחנו: ' + '; '.join(shown[:3]) + '.')
        for q in t.asked:
            parts.append(q['proposal'])
        return ' '.join(parts)

    # ---- architecture handoff
    def handoff(self) -> dict:
        t = self.turn()
        return {'schema': 'intake-handoff/1', 'product_kind': t.product_kind, 'supported': t.supported,
                'binding': t.stated, 'assumed': t.assumed, 'unsourced': t.unsourced,
                'required_behaviors': t.required_behaviors, 'open_questions': [q['field'] for q in t.asked],
                'verification': t.verification, 'messages': list(self.messages)}


_SHOWN_ASSUMPTIONS = ('platform', 'content_only', 'login', 'personal_data', 'access_scope', 'languages', 'dates')
_KIND_HE = {'website': 'אתר', 'web_app': 'אפליקציית ווב', **_UNSUPPORTED_HE}
_BEHAVIOR_HE = {'data_create': 'לשמור / להוסיף', 'data_update': 'לעדכן', 'data_delete': 'למחוק / לבטל'}


def _label(r: dict) -> str:
    k, v = r['key'], r['value']
    if k == 'product_kind':
        return _KIND_HE.get(v, v)
    if k.startswith('behavior.'):
        b = k.split('.', 1)[1]
        if b == 'data_read':
            return ''
        return (_BEHAVIOR_HE.get(b, b) if v else 'בלי ' + _BEHAVIOR_HE.get(b, b))
    return {('content_only', 'yes'): 'אתר תוכן בלבד', ('content_only', 'no'): 'נשמר מידע מהמבקרים',
            ('login', 'none'): 'בלי התחברות', ('login', 'simple'): 'התחברות עם סיסמה', ('login', 'roles'): 'הרשאות לפי תפקיד',
            ('personal_data', 'yes'): 'נשמרים פרטים אישיים', ('personal_data', 'no'): 'בלי פרטים אישיים',
            ('access_scope', 'public'): 'פתוח לציבור', ('languages', 'he'): 'עברית', ('languages', 'en'): 'אנגלית',
            ('languages', 'he_en'): 'עברית ואנגלית'}.get((k, v), f'{k}={v}')
