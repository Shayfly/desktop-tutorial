"""The structure card (docs/spec/first-agent.md section 1): the customer sees the page as a skeleton before paying.

Built from what the customer said -- the fact canon (phone, address, hours) and the request text -- never from
invented content. A row whose content the customer has not given yet says so ("—" with `has_content: False`); the
editor then decides (completeness). The section vocabulary is the Reference Scout's (docs/spec/reference_card.schema.json)
so a library example's `section_order` can be used as is.

Tiers of the structure itself: a library example for the vertical (marked `generic: False`), else a general
suggestion (marked `generic: True`, with the reason shown on the card). Writing the card into the brief is limited to
the brief's `structure` field (the warehouse slice released 2026-11-15) and is not done here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# section -> (Hebrew title, icon, facts it shows)
SECTIONS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    'hero': ('כותרת ותמונה ראשית', 'image', ()),
    'products': ('המוצרים', 'list', ()),
    'services': ('השירותים', 'list', ()),
    'story': ('הסיפור שלנו', 'text', ()),
    'gallery': ('גלריה', 'image', ()),
    'hours': ('שעות פתיחה', 'clock', ('hours',)),
    'location': ('כתובת', 'pin', ('address',)),
    'contact': ('כפתור התקשרות', 'phone', ('phone',)),
    'testimonials': ('המלצות', 'quote', ()),
    'faq': ('שאלות נפוצות', 'help', ()),
    'footer': ('תחתית', 'footer', ()),
}
GENERIC_ORDER = ('hero', 'products', 'hours', 'location', 'contact', 'footer')
# what each product kind can hold (feasibility, editor)
KIND_SECTIONS: dict[str, frozenset[str]] = {
    'site': frozenset(SECTIONS), 'landing': frozenset(SECTIONS), 'app': frozenset(SECTIONS),
    'song': frozenset(), 'video': frozenset(), 'game': frozenset({'hero'}),
}
_ASKS = {'hours': r'שעות|hours', 'location': r'כתובת|address|מיקום', 'contact': r'טלפון|התקשר|call|phone',
         'products': r'מוצר|products|תפריט|menu', 'gallery': r'גלרי|gallery', 'testimonials': r'המלצ|testimonial',
         'faq': r'שאלות נפוצות|faq', 'story': r'סיפור|story|אודות|about'}


def _quoted(text: str) -> list[str]:
    return [m.strip() for m in re.findall(r'["“”״]([^"“”״]{2,80})["“”״]', text or '')]


def _list_after(label: str, text: str) -> list[str]:
    m = re.search(label + r'\s*:\s*([^.\n]+)', text or '')
    return [p.strip() for p in re.split(r'[,،·]', m.group(1)) if p.strip()] if m else []


@dataclass(frozen=True)
class Row:
    key: str
    title: str
    icon: str
    detail: str
    has_content: bool
    needs: tuple[str, ...]

    def to_dict(self) -> dict:
        return {'key': self.key, 'title': self.title, 'icon': self.icon, 'detail': self.detail,
                'has_content': self.has_content, 'needs': list(self.needs)}


def _detail(key: str, text: str, canon, quotes: list[str], image: str | None) -> tuple[str, bool]:
    vals = lambda k: sorted(canon.values(k)) if canon is not None else []
    if key == 'hero':
        name = quotes[0] if quotes else ''
        pic = f'{image} (התמונה תיווצר אחרי האישור)' if image else ''
        out = ' · '.join(x for x in (name, pic) if x)
        return out or '—', bool(name or image)
    if key in ('products', 'services'):
        items = _list_after('מוצרים' if key == 'products' else 'שירותים', text)
        return (' · '.join(items) or '—'), bool(items)
    if key == 'hours':
        hours = [f.source_ref for f in canon.facts if f.key == 'hours'] if canon is not None else []
        closed = 'שבת סגור' if re.search(r'שבת\s+סגור', text or '') else ''
        out = ' · '.join(hours + ([closed] if closed else []))
        return out or '—', bool(hours)
    if key == 'location':
        refs = [f.source_ref for f in canon.facts if f.key == 'address'] if canon is not None else []
        return (refs[0] if refs else '—'), bool(refs)
    if key == 'contact':
        refs = [f.source_ref for f in canon.facts if f.key == 'phone'] if canon is not None else []
        return (refs[0] if refs else '—'), bool(refs)
    if key == 'footer':
        tagline = next((q for q in quotes[1:] if len(q) > 15), '')
        return (f'"{tagline}"' if tagline else 'פרטי העסק בקצרה'), True
    return '—', False


def _image(text: str) -> str | None:
    m = re.search(r'תמונה\s+(?:ראשית\s+)?(?:גדולה\s*)?:\s*([^.\n]+)', text or '')
    return m.group(1).strip() if m else None


def build_card(request_text: str, *, canon, kind: str = 'site', library_order: list[str] | None = None,
               vertical: str | None = None) -> dict:
    """One structure card for one product. `library_order` is an approved example's section_order (tier 2); without
    it the card is a general suggestion and says so. `vertical` None: the card says the vertical is still unknown."""
    if kind not in KIND_SECTIONS:
        raise ValueError(f'unknown product kind {kind!r}; one of {sorted(KIND_SECTIONS)}')
    text = request_text or ''
    quotes, image = _quoted(text), _image(text)
    if library_order:
        unknown = [s for s in library_order if s not in SECTIONS]
        if unknown:
            raise ValueError(f'library section_order has sections outside the vocabulary: {unknown}')
        order, generic, reason = list(library_order), False, None
    else:
        order = list(GENERIC_ORDER)
        # a section the customer asked for that the general order lacks is added before the footer
        for key, pat in _ASKS.items():
            if key not in order and re.search(pat, text, re.I):
                order.insert(order.index('footer'), key)
        generic = True
        reason = ('עוד לא ידוע התחום: זו הצעה כללית' if vertical is None
                  else 'הצעה כללית: עוד אין לנו דוגמה לתחום הזה')
    rows = []
    for key in order:
        title, icon, needs = SECTIONS[key]
        detail, has = _detail(key, text, canon, quotes, image)
        rows.append(Row(key, title, icon, detail, has, needs))
    return {'kind': kind, 'vertical': vertical, 'generic': generic, 'generic_reason': reason,
            'media': image is not None, 'rows': [r.to_dict() for r in rows]}


def apply_edit(card: dict, op: str, key: str, value: str | None = None) -> dict:
    """move_up / move_down / remove / set_detail on one row; returns a new card. Unknown op or row fails loudly."""
    rows = [dict(r) for r in card['rows']]
    idx = next((i for i, r in enumerate(rows) if r['key'] == key), None)
    if idx is None:
        raise KeyError(f'no row {key!r} on this card')
    if op == 'move_up' and idx > 0:
        rows[idx - 1], rows[idx] = rows[idx], rows[idx - 1]
    elif op == 'move_down' and idx < len(rows) - 1:
        rows[idx + 1], rows[idx] = rows[idx], rows[idx + 1]
    elif op == 'remove':
        rows.pop(idx)
    elif op == 'set_detail':
        if not isinstance(value, str) or not value.strip():
            raise ValueError('set_detail needs the new text')
        rows[idx]['detail'], rows[idx]['has_content'], rows[idx]['edited'] = value.strip(), True, True
    elif op not in ('move_up', 'move_down'):
        raise ValueError(f'unknown edit {op!r}')
    return {**card, 'rows': rows}
