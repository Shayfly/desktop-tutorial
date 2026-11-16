"""The catalogue of in-page windows, and the gate that holds the build to the windows the customer approved
(A2 step 8 and step 9, owner 2026-11-15/16; plan part A section 7).

Step 8 -- the catalogue. The windows A2 already recognises on reference sites (omni_prod/a2/extract.py: mega menu, age
gate, cookie banner, entry popup, cart drawer, promo bar, chips, question widget), each with its spec. The spec is WRITTEN
INTO THE BUILD PROMPT (`prompt_lines`): nothing is added to the page after the model wrote it (plan part B section 1).

Step 9 -- the gate. An approved window enters the fact canon (`canon_facts`), and the build fails, deterministically and
readably, when the page lacks an approved window or breaks the rules the catalogue can check without a browser
(`probe`). Failure codes: WINDOW_MISSING, WINDOW_RULE, WINDOW_ORDER, WINDOW_TWO_OPEN. A rule that needs a browser (focus
is really trapped, nothing is covered on a phone) is in the spec and NOT claimed by the probe; `probe` says which rules it
checked.

Every window root carries `data-148-window="<id>"`. That attribute is the contract between the prompt and the probe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ATTR = 'data-148-window'
CLOSE_ATTR = 'data-148-close'
ACCEPTANCE_PREFIX = 'window-'
CODES = ('WINDOW_MISSING', 'WINDOW_RULE', 'WINDOW_ORDER', 'WINDOW_TWO_OPEN', 'WINDOW_REJECTED')


@dataclass(frozen=True)
class WindowSpec:
    id: str
    he: str
    en: str
    modal: bool                     # covers the page and takes the focus until answered or closed
    spec: tuple[str, ...]           # what the generator is told, in English


_COMMON = (
    'Right-to-left: the page has dir="rtl" on <html> when its language is Hebrew; the window inherits it.',
    'Every button is at least 44x44 CSS pixels (min-height: 44px; min-width: 44px).',
)
_MODAL = (
    'role="dialog" and aria-modal="true" on the root, and an aria-label naming it.',
    'Focus moves into the window when it opens and stays inside it (Tab and Shift+Tab cycle inside); it returns to '
    'the element that opened it when it closes.',
    f'Escape closes it, and a visible close button with {CLOSE_ATTR} does too.',
)

CATALOG: dict[str, WindowSpec] = {w.id: w for w in (
    WindowSpec('mega_menu', 'מגה-תפריט', 'mega menu', False, _COMMON + (
        'A navigation menu with grouped sub-menus; on a phone it opens as a full-height panel with one column.',
        f'Escape closes an open sub-menu; it has a close button with {CLOSE_ATTR} on a phone.')),
    WindowSpec('age_gate', 'שער גיל', 'age gate', True, _COMMON + _MODAL[:2] + (
        'It asks one question (are you over the legal age) with two buttons; nothing else on the page can be used '
        'until it is answered. Escape does NOT dismiss it: an age gate needs an answer.',
        'It comes BEFORE the cookie banner: the cookie banner is shown only after the age gate is answered.')),
    WindowSpec('cookie_banner', 'הודעת עוגיות', 'cookie banner', False, _COMMON + (
        'A bar at the bottom with "accept" and "only necessary" buttons; on a phone it covers at most a quarter of '
        'the screen and never the main call to action.',
        f'It has a close action ({CLOSE_ATTR}) and is not shown again after an answer.')),
    WindowSpec('entry_popup', 'פופ-אפ מבצע כניסה', 'entry promotion popup', True, _COMMON + _MODAL + (
        'It opens at most once per visit, never on top of another window, and states the offer in one sentence.',)),
    WindowSpec('cart_drawer', 'סל נשלף', 'cart drawer', True, _COMMON + _MODAL + (
        'It slides in from the side (from the left on a right-to-left page) and lists the items with a checkout button.',)),
    WindowSpec('promo_bar', 'פס מבצעים', 'promotion bar', False, _COMMON + (
        'One line at the top of the page, at most 48px high, with its own close button '
        f'({CLOSE_ATTR}); it never covers the navigation.',)),
    WindowSpec('chips', "צ'יפים", 'filter chips', False, _COMMON + (
        'A row of at least three selectable chips (role="tab" or buttons with aria-pressed) that scrolls sideways on '
        'a phone instead of wrapping into many lines.',)),
    WindowSpec('question_widget', 'ווידג׳ט שאלה', 'question widget', False, _COMMON + (
        'A small button fixed in a bottom corner that opens a short question form; closed, it covers at most '
        '64x64px and never the main call to action.',
        f'Open, it behaves as a dialog: Escape and {CLOSE_ATTR} close it.')),
)}


# The approval screen (owner 2026-11-16): each window is offered with ONE sentence saying what it gives the customer's
# business; the customer approves or rejects it. Every catalogue window has one (a test holds it).
BENEFITS: dict[str, tuple[str, str]] = {
    'mega_menu': ('מבקרים מוצאים כל מחלקה בלחיצה אחת, גם כשיש הרבה מוצרים.',
                  'Visitors reach every department in one click, even with many products.'),
    'age_gate': ('האתר מבקש אישור גיל לפני הכניסה, כנדרש במכירת אלכוהול או טבק.',
                 'The site asks for an age confirmation before entry, as selling alcohol or tobacco requires.'),
    'cookie_banner': ('המבקרים מאשרים עוגיות, כפי שחוק הפרטיות מצפה כשמודדים תנועה באתר.',
                      'Visitors consent to cookies, as privacy law expects when the site measures traffic.'),
    'entry_popup': ('מבצע שקופץ פעם אחת בכניסה הופך מבקר חדש לקונה.',
                    'An offer shown once on arrival turns a new visitor into a buyer.'),
    'cart_drawer': ('הלקוח רואה את הסל בצד המסך וממשיך לקנות בלי לעזוב את הדף.',
                    'The customer sees the cart at the side and keeps shopping without leaving the page.'),
    'promo_bar': ('פס דק בראש הדף מודיע על מבצע או משלוח חינם בלי להסתיר תוכן.',
                  'A thin bar at the top announces a sale or free delivery without hiding content.'),
    'chips': ('כפתורי סינון מהירים עוזרים למצוא מוצר לפי סוג בנגיעה אחת.',
              'Quick filter chips help find a product by type in one tap.'),
    'question_widget': ('מבקר שואל שאלה מכל מקום באתר, ואתם מקבלים פנייה במקום מבקר שעזב.',
                        'A visitor asks a question from anywhere on the site, and you get an enquiry instead of a lost visitor.'),
}


def offer(lang: str = 'he', approved=(), rejected=()) -> list[dict]:
    """The windows the approval screen offers, in catalogue order, each with its one-sentence benefit and the
    customer's current decision ('approved', 'rejected' or None)."""
    he = lang != 'en'
    approved, rejected = set(approved), set(rejected)
    return [{'id': w.id, 'label': w.he if he else w.en, 'benefit': BENEFITS[w.id][0 if he else 1],
             'state': 'approved' if w.id in approved else 'rejected' if w.id in rejected else None}
            for w in CATALOG.values()]


def known(window_id: str) -> WindowSpec:
    if window_id not in CATALOG:
        raise KeyError(f'unknown window {window_id!r}; one of {sorted(CATALOG)}')
    return CATALOG[window_id]


def prompt_lines(approved) -> list[str]:
    """The spec of every approved window, as the build prompt carries it. An unknown id raises (no silent skip)."""
    specs = [known(w) for w in approved]
    if not specs:
        return []
    out = ['Approved windows (each root element carries ' + ATTR + '="<id>"; the build is checked against this list):']
    for w in specs:
        out.append(f'- {w.id} ({w.en}):')
        out.extend(f'  * {line}' for line in w.spec)
    if {'age_gate', 'cookie_banner'} <= {w.id for w in specs}:
        out.append('- Order: the age gate comes first in the page; the cookie banner appears only after it is answered.')
    out.append('- Never two windows open at once: at most one modal window is visible when the page loads.')
    return out


APPROVED_PREFIX = 'Approved windows (each root element carries '
_APPROVED_LINE = re.compile(r'^- ([a-z_]+) \(', re.M)


def approved_in_prompt(prompt: str) -> list[str]:
    """The approved window ids the build prompt carries (read back from `prompt_lines`), in order."""
    text = prompt or ''
    if APPROVED_PREFIX not in text:
        return []
    block = text[text.index(APPROVED_PREFIX):]
    return [w for w in _APPROVED_LINE.findall(block) if w in CATALOG]


REJECTED_PREFIX = 'Rejected windows (the customer said no; do not add them to the page): '
_REJECTED_LINE = re.compile(re.escape(REJECTED_PREFIX) + r'([a-z_, ]+)\.')


def rejected_lines(rejected) -> list[str]:
    """The windows the customer rejected, as one prompt line. An unknown id raises."""
    ids = [known(w).id for w in rejected]
    return [REJECTED_PREFIX + ', '.join(ids) + '.'] if ids else []


def rejected_in_prompt(prompt: str) -> list[str]:
    m = _REJECTED_LINE.search(prompt or '')
    return [w.strip() for w in m.group(1).split(',') if w.strip() in CATALOG] if m else []


def canon_facts(approved) -> list[dict]:
    """An approved window is a fact the page must show (step 9: it enters the fact canon)."""
    return [{'key': 'window', 'value': known(w).id, 'source': 'approval', 'source_ref': known(w).he} for w in approved]


# ---- the probe: deterministic, static, readable ----------------------------------------------------------------

_TAG = re.compile(r'<([a-zA-Z][\w-]*)\b([^>]*)>', re.S)


def _attrs(raw: str) -> dict[str, str]:
    return {k.lower(): (v if v is not None else '') for k, _, v in
            ((m.group(1), None, m.group(3) if m.group(3) is not None else m.group(4))
             for m in re.finditer(r'([\w:-]+)(\s*=\s*(?:"([^"]*)"|\'([^\']*)\'))?', raw))}


def window_roots(html: str) -> list[tuple[int, str, dict]]:
    """(position, window id, attributes) for every element carrying data-148-window, in page order."""
    out = []
    for m in _TAG.finditer(html or ''):
        a = _attrs(m.group(2))
        if ATTR in a:
            out.append((m.start(), a[ATTR], a))
    return out


def probe(html: str, approved, *, scripts: str = '', lang: str = 'he', rejected=()) -> dict:
    """Check a page against its approved windows. Returns {'failures': [{code, window, message}], 'checked': [...]}.
    `scripts` is the page's JavaScript (inline and files), where the Escape and Tab handling live."""
    roots = window_roots(html)
    by_id = {}
    for pos, wid, a in roots:
        by_id.setdefault(wid, (pos, a))
    failures, checked = [], []

    def fail(code, wid, message):
        failures.append({'code': code, 'window': wid, 'message': message})

    js = (scripts or '') + '\n' + '\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>', html or '', re.S | re.I))
    for wid in approved:
        w = known(wid)
        if wid not in by_id:
            fail('WINDOW_MISSING', wid, f'the approved {w.en} is not on the page: no element with {ATTR}="{wid}"')
            continue
        _, a = by_id[wid]
        if w.modal:
            checked.append(f'{wid}: role=dialog, aria-modal, keyboard')
            if a.get('role') != 'dialog' or a.get('aria-modal') != 'true':
                fail('WINDOW_RULE', wid, f'the {w.en} needs role="dialog" and aria-modal="true" on its root')
            if 'Tab' not in js:
                fail('WINDOW_RULE', wid, f'the {w.en} does not keep the focus inside: no Tab handling in the page script')
            if wid != 'age_gate' and 'Escape' not in js:
                fail('WINDOW_RULE', wid, f'Escape does not close the {w.en}: no Escape handling in the page script')
        if wid in ('cookie_banner', 'entry_popup', 'cart_drawer', 'promo_bar', 'question_widget'):
            checked.append(f'{wid}: close button')
            start = by_id[wid][0]
            if CLOSE_ATTR not in (html or '')[start:start + 6000]:
                fail('WINDOW_RULE', wid, f'the {w.en} has no close button with {CLOSE_ATTR}')
    for wid in rejected:
        checked.append(f'{wid}: rejected, not on the page')
        if wid in by_id:
            fail('WINDOW_REJECTED', wid, f'the customer rejected the {known(wid).en}, and the page has one '
                                         f'({ATTR}="{wid}")')
    if lang == 'he' and approved:
        checked.append('page: dir=rtl')
        m = re.search(r'<html\b([^>]*)>', html or '', re.I)
        if not m or _attrs(m.group(1)).get('dir') != 'rtl':
            fail('WINDOW_RULE', '*', 'a Hebrew page needs dir="rtl" on <html>')
    if 'age_gate' in by_id and 'cookie_banner' in by_id:
        checked.append('order: age gate before cookies')
        if by_id['age_gate'][0] > by_id['cookie_banner'][0]:
            fail('WINDOW_ORDER', 'age_gate', 'the age gate must come before the cookie banner')
    open_modals = [wid for _, wid, a in roots if wid in CATALOG and CATALOG[wid].modal and 'hidden' not in a
                   and 'display:none' not in a.get('style', '').replace(' ', '')]
    checked.append('at most one modal window open on load')
    if len(open_modals) > 1:
        fail('WINDOW_TWO_OPEN', ','.join(open_modals), 'two windows are open at once when the page loads: '
             + ', '.join(open_modals))
    return {'failures': failures, 'checked': checked}


def _page(repository: dict[str, str]) -> tuple[str, str]:
    html = '\n'.join(v for k, v in sorted(repository.items()) if k.endswith(('.html', '.htm', '.py', '.jinja', '.j2')))
    js = '\n'.join(v for k, v in sorted(repository.items()) if k.endswith(('.js', '.mjs')))
    return html, js


class WindowGateExecutor:
    """The build is not accepted until every approved window is on the page and keeps the checkable rules, and no
    rejected window is on it."""

    def __init__(self, inner, approved, *, lang: str = 'he', rejected=()):
        self._inner, self.approved, self.lang = inner, [known(w).id for w in approved], lang
        self.rejected = [known(w).id for w in rejected]
        self.last_windows = None

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from .autonomous_core import AcceptanceFailure, ExecutionReport
        report = self._inner.execute(repository=repository, spec=spec)
        html, js = _page(repository)
        result = probe(html, self.approved, scripts=js, lang=self.lang, rejected=self.rejected)
        self.last_windows = result
        if not result['failures']:
            return report
        problems = tuple(AcceptanceFailure(f"{ACCEPTANCE_PREFIX}{f['window']}", f"{f['code']}: {f['message']}")
                         for f in result['failures'])
        return ExecutionReport(False, tuple(report.failures) + problems, report.build_log)


def install(engine, *, prompt: str, lang: str = 'he') -> list[str]:
    """Wrap the engine's executor with the window gate when the build prompt carries approved or rejected windows.
    Returns the approved ids."""
    approved, rejected = approved_in_prompt(prompt), rejected_in_prompt(prompt)
    if approved or rejected:
        core = getattr(engine, 'core', engine)
        core.executor = WindowGateExecutor(core.executor, approved, lang=lang, rejected=rejected)
    return approved
