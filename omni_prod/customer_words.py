"""One dictionary from the platform's own words to the customer's words (warehouse 132, the owner 2026-11-22).

The terms audit of 2026-11-21 (docs/audits/customer-terms-audit-2026-11-21.md) counted 15 blocking technical terms in
the conversation-and-approval route alone: the agent spoke in the system's words (spec, verifier, credits, plan,
pricing, providers, server, tab). The fix is at the root, not word by word: every name of an internal part maps to
the word a customer uses, the conversation agent is told the list (prompt_rule), and a check scans the text the
customer reads (machine_terms) so a new machinery word fails a test instead of reaching a customer.

A term is matched as a whole word, with the Hebrew one-letter prefixes (ה ו ב ל מ כ ש) allowed in front.
"""
from __future__ import annotations

import re

# (the platform's word, what the customer hears instead). Hebrew first: most customers write Hebrew.
HE = (
    ('מפרט', 'מה שהבנתי שאתם רוצים'),
    ('מאמת', '(לא נאמר ללקוח: אומרים מה קרה ומה לעשות)'),
    ('קרדיטים', 'סכום מהיתרה שלכם'),
    ('קרדיט', 'סכום מהיתרה שלכם'),
    ('מסלול', 'מה שכלול אצלכם'),
    ('תמחור', 'מחיר'),
    ('אפיון', 'מה שהבנתי שאתם רוצים'),
    ('ספקים', '(לא נאמר ללקוח)'),
    ('ספק חיצוני', '(לא נאמר ללקוח)'),
    ('מפעיל השרת', 'אנחנו'),
    ('שרת', '(לא נאמר ללקוח: "זה אצלנו, לא אצלכם")'),
    ('תשתית', '(לא נאמר ללקוח)'),
    ('לשונית', 'הכפתור שעל המסך, בשמו'),
    ('מודלים', '(לא נאמר ללקוח)'),
    ('מסד נתונים', 'המקום שבו נשמרים הפרטים'),
    ('פריסה', 'העלאה לאוויר'),
)
EN = (
    ('spec', 'what I understood you want'),
    ('verifier', '(not said to the customer: say what happened and what to do)'),
    ('credits', 'an amount from your balance'),
    ('provider', '(not said to the customer)'),
    ('server operator', 'us'),
    ('infrastructure', '(not said to the customer)'),
    ('idempotency', '(never shown)'),
    ('webhook', '(never shown)'),
    ('deploy', 'put it online'),
    ('database', 'where the details are kept'),
)

_PREFIX = r'(?:(?<=^)|(?<=[^\w֐-׿]))[הובלמכש]?'
_END = r'(?![\w֐-׿])'


def _pattern(term: str, hebrew: bool) -> re.Pattern:
    body = re.escape(term).replace(r'\ ', r'\s+')
    if hebrew:
        return re.compile(_PREFIX + body + _END)
    return re.compile(r'(?<![A-Za-z])' + body + r'(?![A-Za-z])', re.I)


_PATTERNS = [(t, _pattern(t, True)) for t, _ in HE] + [(t, _pattern(t, False)) for t, _ in EN]


def machine_terms(text: str) -> list[str]:
    """The platform words in `text`, in dictionary order, each once. Empty: the text speaks the customer's words."""
    found = []
    for term, pat in _PATTERNS:
        if pat.search(text or '') and term not in found:
            found.append(term)
    return found


def prompt_rule() -> str:
    """The sentence the conversation agent is given: the words it never says, and what it says instead."""
    pairs = '; '.join(f'"{t}" -> {r}' for t, r in HE if not t.startswith('ה')) + '; ' + \
            '; '.join(f'"{t}" -> {r}' for t, r in EN)
    return ('Words of this platform the customer never hears (say the right side instead, or nothing): ' + pairs +
            '. Talk about their business and their site, never about how this system works inside.')


# ------------------------------------------------------------------ the scan of the text a customer reads

CUSTOMER_TEXT = ('omni_prod/intake/venice.py', 'omni_prod/intake/approval_flow.py', 'omni_prod/intake/interpreter.py',
                 'omni_prod/conversation/supervisor.py', 'omni_prod/discovery.py', 'omni_prod/window_catalog.py',
                 'omni_prod/build_readiness.py', 'omni_prod/build_announcement.py', 'omni_prod/assets/app.js',
                 'omni_prod/gate_words.py',        # every blocking finding, in the customer's words (warehouse 132)
                 'omni_prod/conversation/spec_card.py',
                 'omni_prod/shot_fix.py',            # warehouse 124: what the customer reads about their screenshot
                 'omni_prod/intake/media_reading.py')   # warehouse 128: its sentences are conversation replies
# The conversation-and-approval route: here the count is zero, not a ratchet (the owner, 2026-11-22: "this is the heart").
CONVERSATION = ('omni_prod/intake/venice.py', 'omni_prod/intake/approval_flow.py', 'omni_prod/intake/interpreter.py',
                'omni_prod/conversation/supervisor.py', 'omni_prod/discovery.py', 'omni_prod/window_catalog.py',
                # 2026-11-23: the spec card writes the words of the approval screen itself (the owner's example)
                'omni_prod/conversation/spec_card.py',
                # warehouse 124: the replies of a screenshot round are stored as conversation messages
                'omni_prod/shot_fix.py',
                # warehouse 128: the supervisor sends media_reading._TEXT as conversation replies (review 2026-11-24)
                'omni_prod/intake/media_reading.py')
# A string that is not shown to the customer although it holds a platform word, with the reason.
NOT_SHOWN = {
    ('omni_prod/conversation/supervisor.py', 'קרדיטים'):
        'the cost-intent regex reads the CUSTOMER\'s message: a customer who types "קרדיטים" is asking the price',
}
_HEB = re.compile('[֐-׿]')
_FIELD = re.compile(r'\{[^{}]*\}|\$\{[^{}]*\}')        # format fields are code, not words


def _he_terms(text: str) -> list[str]:
    plain = _FIELD.sub(' ', text)
    return [t for t, pat in _PATTERNS[:len(HE)] if pat.search(plain)]


def scan(path: str, root='.') -> list[tuple[int, str, str]]:
    """(line, term, text) for every Hebrew string in `path` that holds a platform word, minus NOT_SHOWN."""
    import ast
    from pathlib import Path
    source = (Path(root) / path).read_text(encoding='utf-8')
    strings = []
    if path.endswith('.py'):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _HEB.search(node.value):
                strings.append((node.lineno, node.value))
    else:
        lit = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"|`([^`]*)`")
        for n, line in enumerate(source.splitlines(), 1):
            for m in lit.finditer(line):
                s = ''.join(g or '' for g in m.groups())
                if _HEB.search(s):
                    strings.append((n, s))
    out = []
    for line, s in strings:
        for term in _he_terms(s):
            if (path, term) not in NOT_SHOWN:
                out.append((line, term, s))
    return out
