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
_DIGITS = re.compile(r'\d[\d,.]*\d|\d')
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


def norm_number(raw: str) -> str:
    """A digit run as a reader compares it: digits folded, thousands separators and a trailing full stop dropped."""
    s = F.fold_digits(raw).rstrip('.')
    return re.sub(r'(?<=\d),(?=\d{3}\b)', '', s)


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

    def allowed_numbers(self) -> set[str]:
        return {n['value'] for n in self.numbers}

    def price(self, ref: str) -> dict | None:
        return next((p for p in self.prices if p['id'] == ref), None)

    def review(self, ref: str) -> dict | None:
        return next((r for r in self.reviews if r['id'] == ref), None)

    def model_text(self, text: str) -> str:
        """A customer text as the model may read it: facts blanked, each price replaced by its reference."""
        out = text or ''
        for p in sorted(self.prices, key=lambda p: -len(p['span'])):
            out = out.replace(p['span'], p['id'])
        return blank_facts(out)

    def for_model(self) -> dict:
        """What the copy model sees: the customer's words with every fact blanked, the numbers it may use, the price
        and review references, and WHICH facts the platform shows (never their values)."""
        return {
            'customer_text': self.model_text(self.customer),
            'outline': [{'title': t, 'customer_wrote': self.model_text(b)} for t, b in self.outline],
            'numbers_you_may_use': [{'value': n['value'], 'context': self.model_text(n['context'])} for n in self.numbers],
            'prices': [{'id': p['id'], 'context': self.model_text(p['context'])} for p in self.prices],
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
                'prices': self.prices, 'numbers': self.numbers, 'outline': [list(x) for x in self.outline],
                'exclusions': self.exclusions, 'images': self.images, 'problems': self.problems, 'counts': self.counts}

    def spans(self) -> list[str]:
        """Every fact the served page must show, as the customer wrote it (content/facts.json; the fixed test asserts
        each one appears in GET /)."""
        return [s for s in (self.phone, self.whatsapp, self.email, self.address, *self.hours) if s]


def _context(text: str, start: int, end: int) -> str:
    return ' '.join(text[max(0, start - MAX_CONTEXT):end + MAX_CONTEXT].split())


def _numbers(text: str) -> list[dict]:
    """Every digit run of the customer's words that is not part of a fact span, normalised, with its context."""
    clean = _ENUMERATOR.sub('', blank_facts(text))      # "3. על המשרד": a list's numbering is not a number given
    out, seen = [], set()
    for m in _DIGITS.finditer(F.fold_digits(clean)):
        value = norm_number(m.group(0))
        if value and value not in seen:
            seen.add(value)
            out.append({'value': value, 'context': _context(clean, m.start(), m.end())})
    return out


def _prices(text: str) -> list[dict]:
    clean = blank_facts(text)
    out: list[dict] = []
    for m in _PRICE.finditer(clean):
        span = ' '.join(m.group(0).split())
        if not any(p['span'] == span for p in out):
            out.append({'id': f'@price:{len(out) + 1}', 'span': span, 'context': _context(clean, m.start(), m.end())})
    return out


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
    hours = [v for k, v in F.facts_to_show(prompt) if k == 'hours']
    return FactSheet(
        prompt_sha256=hashlib.sha256((prompt or '').encode('utf-8')).hexdigest(), canon_hash=canon.hash,
        name=names[0] if len(names) == 1 else None, phone=mains[0] if len(mains) == 1 else None,
        whatsapp=whatsapp, whatsapp_basis=basis, email=emails[0] if len(emails) == 1 else None,
        address=addresses[0] if len(addresses) == 1 else None, hours=hours, reviews=_reviews(canon),
        prices=_prices(customer), numbers=_numbers(customer), customer=customer, outline=outline(prompt),
        exclusions=[x['key'] for x in read_customer_exclusions(prompt)], images=placed,
        problems=problems + image_problems,
        counts={k: sorted(canon.values(k)) for k in ('reviewCount', 'rating', 'customerCount', 'count')
                if canon.values(k)})


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
