"""Deterministic, zero-cost complexity / risk classification of an intake turn
(Issue #12). Runs before any model is chosen and looks at prior turns, not
only the current message.

  LOW     pure greeting / thanks, and no sensitive context in recent turns
  MEDIUM  ordinary requirements -- and the floor for anything ambiguous
  HIGH    complex architecture (several integration/scale signals), long
          multi-part specs, or a contradiction with what was already confirmed
  RISKY   payments / money, deletion or destructive changes, secrets and
          credentials, personal-data / permission / security decisions,
          approvals -- or a short reply ("כן", "ok", "👍") right after the
          assistant raised any of those

Rules are conservative: a message is LOW only if it is entirely a greeting;
negation never lowers risk ("בלי תשלומים" still concerns payments); anything
unmatched is MEDIUM, never LOW.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

LOW, MEDIUM, HIGH, RISKY = 'LOW', 'MEDIUM', 'HIGH', 'RISKY'
ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2, RISKY: 3}

_MARKS = re.compile('[֑-ׇֽֿׁׂׅׄ​-‏‪-‮⁦-⁩﻿]')
_FINALS = str.maketrans({'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'})


def _norm(text: str) -> str:
    t = unicodedata.normalize('NFC', str(text or ''))
    t = _MARKS.sub('', t).lower().translate(_FINALS)
    t = t.replace('״', '"').replace('׳', "'").replace('־', '-')
    t = re.sub(r'(.)\1{2,}', r'\1\1', t)                    # "כןןןן" -> "כנן" (finals folded above)
    return re.sub(r'\s+', ' ', t).strip()


def _rx(*words: str) -> re.Pattern:
    """Hebrew words may carry one-letter prefixes (ו ה ב ל מ ש כ) and are matched on folded finals."""
    alts = []
    for w in words:
        w = _norm(w)
        if re.search('[א-ת]', w):
            alts.append(r'(?<![א-ת])(?:[והבלמשכ]{0,2})'
                        + re.escape(w).replace(r'\ ', r'\s+(?:[והבלמשכ]{0,2})'))   # prefix on every word
        else:
            alts.append(r'\b' + re.escape(w).replace(r'\ ', r'\s+') + r'\b')
    return re.compile('|'.join(alts))


RISK_PATTERNS = {
    'payment': _rx('תשלומ', 'תשלום', 'לשלמ', 'לשלם', 'משלמ', 'ישלמו', 'תשלמ', 'סליקה', 'סליקת', 'כרטיס אשראי', 'אשראי',
                   'חיוב', 'לחייב', 'חייב את', 'תחייב', 'תחייבו', 'החזר כספי', 'זיכוי', 'חשבונית', 'קבלה על', 'מנוי בתשלום', 'עמלה',
                   'כסף', 'ש"ח', 'שקל', 'שקלים', 'דולר', '₪', 'payment', 'payments', 'pay', 'paid', 'paying',
                   'checkout', 'credit card', 'billing', 'invoice', 'refund', 'charge', 'stripe', 'paypal', 'price',
                   'subscription', 'עלות', 'מחיר', 'תקציב'),
    'destructive': _rx('למחוק', 'מחיקה', 'מחיקת', 'תמחק', 'תמחקו', 'מחק', 'מחקו', 'נמחק', 'להסיר את כל', 'לאפס', 'איפוס', 'תאפס', 'תאפסו', 'נאפס', 'אפס את',
                       'תדרוס', 'תשמיד',
                       'לדרוס', 'דריסה', 'לבטל את הפרויקט', 'לסגור את החשבונ', 'להשמיד', 'delete', 'deleting', 'remove all',
                       'wipe', 'drop', 'reset', 'erase', 'destroy', 'overwrite', 'rollback', 'לשחזר', 'שחזור', 'restore'),
    'secrets': _rx('סיסמה', 'סיסמא', 'סיסמאות', 'password', 'passwords', 'api key', 'מפתח api', 'מפתח ה-api', 'מפתח גישה',
                   'טוקן', 'token', 'secret', 'סוד', 'credentials', 'פרטי התחברות', 'פרטי גישה', 'ssh', 'private key'),
    'privacy_security': _rx('מידע אישי', 'פרטים אישיים', 'מידע רגיש', 'תעודת זהות', 'ת"ז', 'מספר זהות', 'רפואי', 'רפואיים',
                            'פרטיות', 'הרשאות', 'הרשאה', 'מנהל מערכת', 'אדמין', 'admin', 'personal data', 'privacy',
                            'sensitive', 'permissions', 'gdpr', 'security', 'אבטחה', 'הצפנה', 'encryption', 'ביומטרי'),
    'approval': _rx('מאשר', 'מאשרת', 'מאשרים', 'אישור', 'תאשר', 'אשרו', 'approve', 'approved', 'approval', 'confirm',
                    'go ahead', 'תתחיל לבנות', 'תתחילו לבנות', 'תבנה את זה', 'פרסמ', 'תפרסמ', 'תפרסמו', 'נפרסמ', 'יפרסמ', 'פרסום', 'publish', 'deploy',
                    'production', 'לייב', 'עלה לאוויר', 'להעלות לאוויר'),
}
COMPLEX_PATTERNS = _rx('אינטגרציה', 'אינטגרציות', 'api', 'webhook', 'מיקרו', 'microservice', 'multi-tenant', 'ריבוי לקוחות',
                       'זמן אמת', 'real-time', 'realtime', 'סנכרון', 'sync', 'offline', 'אופליין', 'מיליון', 'million',
                       'scale', 'סקייל', 'sso', 'erp', 'crm', 'salesforce', 'sap', 'בינה מלאכותית', 'machine learning',
                       'ai', 'סוכן', 'agent', 'blockchain', 'בלוקצ\'יינ', 'הצפנה מקצה', 'kubernetes', 'רב לשוני',
                       'multilingual', 'ריבוי שפות', 'גיאוגרפי', 'מפות', 'maps', 'streaming', 'וידאו חי')
GREETING = re.compile(r'^(?:' + '|'.join(re.escape(_norm(g)) for g in (
    'שלום', 'שלום שלום', 'היי', 'הי', 'הייי', 'אהלן', 'הלו', 'בוקר טוב', 'צהריים טובים', 'ערב טוב', 'לילה טוב',
    'מה שלומך', 'מה נשמע', 'מה קורה', 'תודה', 'תודה רבה', 'תודה רבה לך', 'תודה לך', 'שבת שלום', 'חג שמח',
    'hello', 'hi', 'hey', 'good morning', 'good evening', 'thanks', 'thank you', 'thanks a lot', 'how are you')) +
    r')(?:\s+(?:' + '|'.join(re.escape(_norm(g)) for g in ('לך', 'רבה', 'there', 'again', 'so much', '148ai')) + r'))*$')
AFFIRMATION = re.compile(r'^(?:' + '|'.join(re.escape(_norm(a)) for a in (
    'כן', 'כן כן', 'כן בבקשה', 'בטח', 'בטוח', 'סבבה', 'אוקיי', 'אוקי', 'אוקיי בבקשה', 'בסדר', 'נכון', 'מאשר', 'מאשרת',
    'תאשר', 'קדימה', 'יאללה', 'יאללה קדימה', 'לך על זה', 'תעשה את זה', 'תעשו את זה', 'מעולה', 'אחלה', 'טוב', 'בדיוק',
    'ok', 'okay', 'yes', 'yep', 'yeah', 'sure', 'go', 'do it', 'confirm', 'confirmed', 'fine', 'agreed', 'right',
    '👍', '✅', '👌')) + r')[.!?\s]*$')
RISKY_ACTIONS = {'approve_build', 'confirm_modification', 'show_plan', 'confirm_payment', 'confirm_delete'}


@dataclass
class Classification:
    level: str
    reasons: list[str] = field(default_factory=list)
    signals: dict = field(default_factory=dict)

    def to_dict(self):
        return {'level': self.level, 'reasons': list(self.reasons), 'signals': dict(self.signals)}


def _risk_hits(text: str) -> list[str]:
    t = _norm(text)
    return sorted(k for k, rx in RISK_PATTERNS.items() if rx.search(t))


def _strip(text: str) -> str:
    return re.sub(r'[.!?,;:)(\-"\'״׳~*]+', ' ', _norm(text)).strip()


def classify(message: str, history: list[dict] | None = None, *, confirmed: dict | None = None,
             proposed: dict | None = None) -> Classification:
    """message: the customer's text. history: prior turns oldest->newest, each
    {'role': 'customer'|'assistant', 'content': str, 'interpretation': {...}}.
    confirmed: brief fields the customer already confirmed {field: value};
    proposed: deterministic proposals from this message {field: value}."""
    history = history or []
    text = _strip(message)
    reasons, signals = [], {}
    recent = history[-4:]
    last_assistant = next((h for h in reversed(history) if h.get('role') == 'assistant'), None)
    ctx_hits = sorted({k for h in recent for k in _risk_hits(h.get('content') or '')})
    actions = {a.get('type') for a in ((last_assistant or {}).get('interpretation') or {}).get('actions') or []
               if isinstance(a, dict)}
    last_hits = _risk_hits((last_assistant or {}).get('content') or '')
    risky_context = bool(last_hits) or bool(actions & RISKY_ACTIONS)
    signals.update(context_risk=ctx_hits, last_assistant_risk=last_hits, last_actions=sorted(a for a in actions if a))

    hits = _risk_hits(message)
    signals['message_risk'] = hits
    if hits:
        reasons.append('sensitive topic: ' + ', '.join(hits))
        return Classification(RISKY, reasons, signals)
    words = text.split()
    if risky_context and (AFFIRMATION.match(text) or len(words) <= 4):
        reasons.append('short reply right after a sensitive assistant turn ('
                       + ', '.join(last_hits + sorted(actions & RISKY_ACTIONS)) + ')')
        return Classification(RISKY, reasons, signals)
    if not text:
        reasons.append('empty or symbols only: ambiguous')
        return Classification(MEDIUM if not risky_context else RISKY, reasons, signals)

    contradictions = sorted(f for f, v in (proposed or {}).items()
                            if f in (confirmed or {}) and (confirmed or {})[f] != v)
    complex_hits = sorted({m.group(0).strip() for m in COMPLEX_PATTERNS.finditer(_norm(message))})
    signals.update(contradictions=contradictions, complex=complex_hits)
    if contradictions:
        reasons.append('contradicts confirmed requirements: ' + ', '.join(contradictions))
        return Classification(HIGH, reasons, signals)
    clauses = len(re.findall(r'[,;\n•]|\bו(?=[א-ת])|\band\b', _norm(message)))
    if len(complex_hits) >= 2 or (len(message) > 600 and clauses >= 6):
        reasons.append('complex architecture / long multi-part specification')
        return Classification(HIGH, reasons, signals)

    if GREETING.match(text) and not ctx_hits and not risky_context:
        reasons.append('greeting only, no sensitive context')
        return Classification(LOW, reasons, signals)
    reasons.append('ordinary requirements or ambiguous: standard lane')
    return Classification(MEDIUM, reasons, signals)
