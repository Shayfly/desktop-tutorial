"""The fact sheet of the content-document route: every fact a page may show, from the approved prompt only.

Facts never pass through the model (the wiring judges, 2026-11-20; the CTO's decision 4 for slice 1). The sheet is built
from `fact_canon` on the SAME approved prompt the truth gate's canon is built from (product_review.install_review_request),
so the canon hash in the content document and in the evidence is the one the gate checks against. The renderer fills
the phone, the WhatsApp number, the e-mail, the address, the hours, the reviews and the prices from here, in the
customer's own spans; the model writes copy only and sees none of these values (`for_model` blanks them).

WhatsApp is a fact: it is on the page only when the customer's own words name WhatsApp AFFIRMATIVELY, and its number
is the mobile phone the customer labelled WhatsApp ("וואטסאפ: 050-...") or, with no label, the customer's only mobile
number. Each of these is a route problem (the build takes the legacy path and says why), never a guess:
  whatsapp_negated         the customer's words say no WhatsApp ("אין לנו וואטסאפ", "בלי וואטסאפ", "without WhatsApp"),
                           anywhere -- one negated mention outweighs an affirmative one
  whatsapp_landline        the number labelled WhatsApp is a landline: a landline is never sent to wa.me
  whatsapp_number_unknown  WhatsApp is named and no mobile number is labelled, or there are several
A label never crosses a sentence or another fact's label ("וואטסאפ. טלפון: 050-..." labels nothing).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from .. import fact_canon as F

BRIEF_MARKER = '--- Approved project brief'
# The brief lines that carry the customer's own words (discovery.requirements_text); every other brief line is 148AI's
# wording (rules, decisions, the design line with its hex colours) and is not the customer's text.
CUSTOMER_LINES = ('Customer facts', 'Audience:', 'Main action:', 'Screens:', 'Initial content:')
_WHATSAPP = re.compile(r'וואטסאפ|ווטסאפ|וואצאפ|ווצאפ|whats\s*app', re.I)
# the WhatsApp word, then at most 15 characters of label punctuation/words inside the same sentence, then a phone span
_WA_LABEL = re.compile(r'(?:וואטסאפ|ווטסאפ|וואצאפ|ווצאפ|whats\s*app)([^\d\n.!?;]{0,15}?)(?=[+\d])', re.I)
# another fact's label inside that gap: the phone after it is that fact's, not WhatsApp's
_OTHER_LABEL = re.compile(r'טלפון|נייד|מייל|דוא["״]?ל|כתובת|phone|mobile|e-?mail|address', re.I)
# a negation within the three words before a WhatsApp mention, inside its clause
_NEGATION = re.compile(r"^(?:ו?(?:אין|בלי|ללא|לא|בלא)|no|not|without|don'?t|doesn'?t)$", re.I)
_CLAUSE = re.compile(r'[,.;:!?\n()]')
_PRICE = re.compile(r'(?:₪\s*\d[\d,.]*\d|₪\s*\d|\d[\d,.]*\d\s*(?:₪|ש["״]ח|שקלים|שקל|NIS)|\d\s*(?:₪|ש["״]ח|שקלים|שקל|NIS))',
                    re.I)
_ENUMERATOR = re.compile(r'(?m)^\s*\d{1,2}[.)]\s+')
_LABEL = {'phone': '«טלפון»', 'email': '«דוא״ל»', 'address': '«כתובת»', 'hours': '«שעות פעילות»'}
MAX_CONTEXT = 30


def request_text(prompt: str) -> str:
    """The customer's request: the text before the approved-brief block."""
    return (prompt or '').split(BRIEF_MARKER, 1)[0].strip()


def customer_text(prompt: str) -> str:
    """The customer's own words in an approved prompt: the request, and the brief lines that quote the customer
    (CUSTOMER_LINES). discovery.customer_text needs a Brief; the worker has only the prompt (judge 2, 2026-11-20)."""
    head, sep, brief = (prompt or '').partition(BRIEF_MARKER)
    lines = [head.strip()]
    if sep:
        lines += [ln.strip() for ln in brief.splitlines() if ln.strip().startswith(CUSTOMER_LINES)]
    return '\n'.join(x for x in lines if x)


from .numbers import norm_number  # noqa: E402  (re-exported: validate and the tests read it from here)


def _fact_spans(text: str) -> list[tuple[str, str]]:
    """(key, span) of every phone, e-mail, street address and hours statement in a text, longest first."""
    from ..opening_hours import spans as hour_spans
    clean = F.decode_entities(text)
    found = [('phone', m.group(0)) for m in F._PHONE.finditer(clean) if F.parse_phone(m.group(0)).ok]
    found += [('email', m.group(0)) for m in F._EMAIL.finditer(clean)]
    found += [('address', m.group(0)) for m in F._STREET.finditer(clean)]
    found += [('hours', s) for s in hour_spans(clean)]
    found += [('hours', m.group(0)) for m in F._HOURS.finditer(clean)]
    return sorted(set(found), key=lambda kv: -len(kv[1]))


def blank_facts(text: str) -> str:
    """The text with every fact span replaced by its label («טלפון», «כתובת» ...): what the model may read."""
    out = F.decode_entities(text or '')
    for key, span in _fact_spans(out):
        out = out.replace(span, _LABEL[key])
    return out


@dataclass
class FactSheet:
    prompt_sha256: str
    canon_hash: str
    name: str | None
    phone: str | None
    whatsapp: str | None
    whatsapp_basis: str | None
    email: str | None
    address: str | None
    hours: list[str]
    reviews: list[dict]
    prices: list[dict]
    numbers: list[dict]
    customer: str
    outline: list[tuple[str, str]]
    exclusions: list[str]
    images: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)          # typed counts the customer gave (fact_canon.count_facts)
    withheld_prices: list = field(default_factory=list)  # prices of the build itself (a budget): never on the page

    def allowed_numbers(self) -> set[str]:
        return {n['value'] for n in self.numbers}

    def numbers_for(self, value: str) -> list[dict]:
        """The customer's numbers with this value, each with what it counted ('noun') and its kind."""
        return [n for n in self.numbers if n['value'] == value]

    def price(self, ref: str) -> dict | None:
        return next((p for p in self.prices if p['id'] == ref), None)

    def review(self, ref: str) -> dict | None:
        return next((r for r in self.reviews if r['id'] == ref), None)

    def model_text(self, text: str) -> str:
        """A customer text as the model may read it: facts blanked, each price replaced by its reference."""
        out = text or ''
        for p in sorted(self.prices, key=lambda p: -len(p['span'])):
            out = out.replace(p['span'], p['id'])
        for p in sorted(self.withheld_prices, key=lambda p: -len(p['span'])):
            out = out.replace(p['span'], '«מחיר שאינו לאתר»')
        return blank_facts(out)

    def for_model(self) -> dict:
        """What the copy model sees: the customer's words with every fact blanked, the numbers it may use, the price
        and review references, and WHICH facts the platform shows (never their values)."""
        return {
            'customer_text': self.model_text(self.customer),
            'outline': [{'title': t, 'customer_wrote': self.model_text(b)} for t, b in self.outline],
            'numbers_you_may_use': [{'value': n['value'], 'counts': ('a year' if n['kind'] == 'year' else n['noun']),
                                     'context': self.model_text(n['context'])} for n in self.numbers],
            'prices': [{'id': p['id'], 'label': p['label'], 'context': self.model_text(p['context'])}
                       for p in self.prices],
            'reviews': [{'id': r['id'], 'author': r['author']} for r in self.reviews],
            'business_name_given': self.name,
            'facts_the_platform_shows': [k for k in ('phone', 'whatsapp', 'email', 'address', 'hours')
                                         if getattr(self, k)],
            'images': sorted(self.images),
        }

    def to_dict(self) -> dict:
        return {'prompt_sha256': self.prompt_sha256, 'canon_hash': self.canon_hash, 'name': self.name,
                'phone': self.phone, 'whatsapp': self.whatsapp, 'whatsapp_basis': self.whatsapp_basis,
                'email': self.email, 'address': self.address, 'hours': list(self.hours), 'reviews': self.reviews,
                'prices': self.prices, 'withheld_prices': self.withheld_prices, 'numbers': self.numbers,
                'outline': [list(x) for x in self.outline],
                'exclusions': self.exclusions, 'images': self.images, 'problems': self.problems, 'counts': self.counts}

    def spans(self) -> list[str]:
        """Every fact the served page must show, as the customer wrote it (content/facts.json; the fixed test asserts
        each one appears in GET /): the contact facts, the hours and every price the customer gave for the page."""
        return [s for s in (self.phone, self.whatsapp, self.email, self.address, *self.hours,
                            *(p['span'] for p in self.prices)) if s]


def _context(text: str, start: int, end: int) -> str:
    return ' '.join(text[max(0, start - MAX_CONTEXT):end + MAX_CONTEXT].split())


def _numbers(text: str) -> list[dict]:
    """Every number of the customer's words -- digit runs and Hebrew number words -- that is not part of a fact span
    and not a price, normalised, with WHAT IT COUNTED: 'noun' is the customer's words right after it ("3 עורכי דין" ->
    'עורכי דין'), kind 'year' for a year ("מאז 2008"), else 'count'. A price is the customer's span, reachable only as
    its @price:N reference, so its digits are not a number the copy may use (250 of "250 ₪" never becomes
    "250 שנות ניסיון")."""
    from . import numbers as N
    clean = _ENUMERATOR.sub('', blank_facts(text))      # "3. על המשרד": a list's numbering is not a number given
    masked = _PRICE.sub(lambda m: ' ' * len(m.group(0)), clean)
    out, seen = [], set()
    for m in N.mentions(masked):
        if m.value is None:
            continue
        kind = 'year' if N.is_year(m.value) and m.kind == 'digits' else 'count'
        noun = ' '.join(m.after) or None
        if (m.value, noun) in seen:
            continue
        seen.add((m.value, noun))
        out.append({'value': m.value, 'noun': noun, 'kind': kind, 'context': _context(clean, m.start, m.end)})
    return out


# a clause that names the build itself: its price is the customer's budget for 148AI, not a price for the page
_BUILD_PRICE = re.compile(r'תקציב|בניית האתר|לבניית|עלות האתר|מחיר האתר|לאתר עצמו|\bbudget\b', re.I)
_LABEL_CUT = re.compile(r'[:,;.!?()\n]|(?<!\d)\d{1,2}[.)]\s')
PRICE_STOPWORDS = frozenset({'כמה', 'עולה', 'עולים', 'עולות', 'עלות', 'מחיר', 'מחירים', 'המחיר', 'של', 'את', 'עם', 'על',
                             'זה', 'הוא', 'היא', 'האם', 'רק', 'גם', 'עד', 'כל', 'לכל', 'בערך', 'החל', 'מ-', 'ב-', 'ל-'})


def price_words(label: str) -> list[str]:
    """The content words of a price's label ("כמה עולה ייעוץ ראשון" -> ['ייעוץ', 'ראשון'])."""
    return [w for w in re.findall(r'[א-תA-Za-z"״׳\']{2,}', label or '') if w not in PRICE_STOPWORDS]


def _label(clean: str, start: int) -> str:
    """The customer's words before a price, inside its clause: "5. שאלות נפוצות: כמה עולה ייעוץ ראשון (250 ₪)" ->
    'כמה עולה ייעוץ ראשון'."""
    before = clean[max(0, start - 120):start].rstrip(' \t(:–—-')
    return ' '.join(_LABEL_CUT.split(before)[-1].split())


def _prices(text: str) -> tuple[list[dict], list[dict]]:
    """(the prices the customer gave for the page, the prices of the build itself). A page price is shown by its
    reference @price:N, next to its own label ('label', 'words'); the same span written twice is one price whose
    words are every label it was written with."""
    clean = blank_facts(text)
    out: list[dict] = []
    withheld: list[dict] = []
    for m in _PRICE.finditer(clean):
        span = ' '.join(m.group(0).split())
        label = _label(clean, m.start())
        clause = label + ' ' + clean[m.end():m.end() + 60].split('\n')[0]
        if _BUILD_PRICE.search(label) or _BUILD_PRICE.search(clause.split('.')[0]):
            if not any(p['span'] == span for p in withheld):
                withheld.append({'span': span, 'label': label})
            continue
        known = next((p for p in out if p['span'] == span), None)
        if known is None:
            out.append({'id': f'@price:{len(out) + 1}', 'span': span, 'label': label,
                        'words': price_words(label), 'context': _context(clean, m.start(), m.end())})
        else:
            known['words'] += [w for w in price_words(label) if w not in known['words']]
    page_spans = {p['span'] for p in out}
    return out, [w for w in withheld if w['span'] not in page_spans]


def _reviews(canon) -> list[dict]:
    out = []
    for f in canon.facts:
        if f.key != 'review':
            continue
        m = F._QUOTE.search(f.source_ref)
        if m:
            out.append({'id': f'@review:{len(out) + 1}', 'text': m.group(1).strip(), 'author': m.group(2).strip()})
    return out


def negated(text: str, start: int) -> bool:
    """True when one of the three words before position `start`, inside its clause, is a negation ("אין לנו
    וואטסאפ", "בלי כפתור וואטסאפ", "no WhatsApp")."""
    before = _CLAUSE.split(text[max(0, start - 80):start])[-1]
    words = [w.strip('"\'״׳-') for w in before.split()][-3:]
    return any(_NEGATION.match(w) for w in words if w)


def _whatsapp(prompt: str, canon, customer: str) -> tuple[str | None, str | None, list[str]]:
    """(WhatsApp span, basis, phones left as the main phone(s)) -- None when the customer's words do not name it.
    basis: 'labelled' | 'only_mobile' | None (not named) | 'negated' | 'landline' | 'unknown' (the last three are
    route problems, said by fact_sheet)."""
    phones = [f for f in canon.facts if f.key == 'phone']
    every = [f.source_ref for f in phones]
    said = [F.decode_entities(customer), F.decode_entities(request_text(prompt))]
    mentions = [(text, m.start()) for text in said for m in _WHATSAPP.finditer(text)]
    if not mentions:
        return None, None, every
    if any(negated(text, at) for text, at in mentions):
        return None, 'negated', every
    text = F.decode_entities(prompt)
    labelled = []
    for m in _WA_LABEL.finditer(text):
        if _OTHER_LABEL.search(m.group(1)):
            continue
        span = F._PHONE.match(text, m.end())
        parsed = F.parse_phone(span.group(0)) if span else None
        if parsed is not None and parsed.ok and parsed.e164 not in labelled:
            labelled.append(parsed.e164)
    by_value = {f.value: f.source_ref for f in phones}
    if len(labelled) == 1 and labelled[0] in by_value:
        if F.parse_phone(by_value[labelled[0]]).kind != 'mobile':
            return None, 'landline', every
        rest = [f.source_ref for f in phones if f.value != labelled[0]] or [by_value[labelled[0]]]
        return by_value[labelled[0]], 'labelled', rest
    mobiles = [f for f in phones if F.parse_phone(f.source_ref).kind == 'mobile']
    if not labelled and len(mobiles) == 1:
        rest = [f.source_ref for f in phones if f.value != mobiles[0].value] or [mobiles[0].source_ref]
        return mobiles[0].source_ref, 'only_mobile', rest
    return None, 'unknown', [f.source_ref for f in phones]


def _images(asset_plan, images) -> tuple[dict, list[str]]:
    """{place: {src, alt, width, height}} for the hero and story places; a place the route cannot render is a problem."""
    sizes = {getattr(i, 'marker', None): (getattr(i, 'width', None), getattr(i, 'height', None)) for i in images or ()}
    out, problems = {}, []
    for slot in asset_plan or ():
        place = slot['place']
        if place not in ('hero', 'story') or place in out:
            problems.append(f'image_place_{place}')
            continue
        w, h = sizes.get(slot['marker'], (None, None))
        out[place] = {'src': slot['marker'], 'alt': slot['alt'], **({'width': w} if w else {}),
                      **({'height': h} if h else {})}
    return out, problems


_WHATSAPP_PROBLEM = {'negated': 'whatsapp_negated', 'landline': 'whatsapp_landline', 'unknown': 'whatsapp_number_unknown'}


def fact_sheet(prompt: str, *, asset_plan=None, images=()) -> FactSheet:
    """The sheet for one build, from the approved prompt (the truth gate's own text)."""
    from ..page_outline import outline
    from ..product_architect import read_customer_exclusions
    canon = F.build_canon(prompt)
    customer = customer_text(prompt)
    whatsapp, basis, mains = _whatsapp(prompt, canon, customer)
    problems = []
    if basis in _WHATSAPP_PROBLEM:
        problems.append(_WHATSAPP_PROBLEM[basis])
    if len(mains) != 1:
        problems.append('phone_not_one')
    emails = [f.source_ref for f in canon.facts if f.key == 'email']
    addresses = [f.source_ref for f in canon.facts if f.key == 'address']
    if len(emails) > 1:
        problems.append('email_not_one')
    if len(addresses) > 1:
        problems.append('address_not_one')
    names = sorted(canon.values('name'))
    if len(names) > 1:
        problems.append('name_not_one')
    placed, image_problems = _images(asset_plan, images)
    prices, withheld = _prices(customer)
    hours = [v for k, v in F.facts_to_show(prompt) if k == 'hours']
    return FactSheet(
        prompt_sha256=hashlib.sha256((prompt or '').encode('utf-8')).hexdigest(), canon_hash=canon.hash,
        name=names[0] if len(names) == 1 else None, phone=mains[0] if len(mains) == 1 else None,
        whatsapp=whatsapp, whatsapp_basis=basis, email=emails[0] if len(emails) == 1 else None,
        address=addresses[0] if len(addresses) == 1 else None, hours=hours, reviews=_reviews(canon),
        prices=prices, withheld_prices=withheld, numbers=_numbers(customer), customer=customer, outline=outline(prompt),
        exclusions=[x['key'] for x in read_customer_exclusions(prompt)], images=placed,
        problems=problems + image_problems,
        counts={k: sorted(canon.values(k)) for k in ('reviewCount', 'rating', 'customerCount', 'count')
                if canon.values(k)})


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
