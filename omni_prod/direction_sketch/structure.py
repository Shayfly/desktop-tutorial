"""The content of a sketch page: what the section library is given for a direction (S6.3, slice 1).

Nothing is invented and presented as the customer's. Without the model's words (`copy=None`) the hero shows the
business name as its title, the customer's own category word as its eyebrow when the brief names one, and marked
placeholder lines; every other section is an outline block (its real heading, its real tone, skeleton lines). With the
words (the validated `148ai.site_content/1` document restricted to the hero and the services) the hero and the services
are real; the rest stay outlines. A phone the customer has not given is the placeholder label. Every placeholder used is
returned beside the content, by name."""
from __future__ import annotations

import dataclasses

PHONE_LABEL = 'הטלפון שלכם'
HERO_LEAD = 'כאן תופיע שורת הפתיחה של האתר'
HERO_CTA = 'ליצירת קשר'
DESCRIPTION = 'סקיצת כיוון לאתר {name}'
# The library's own menu word for a section the customer did not title (the generic ones of site_content.OUTLINE_MAP).
SECTION_WORDS = {'services': 'שירותים', 'about': 'עלינו', 'process': 'איך זה עובד', 'faq': 'שאלות נפוצות',
                 'contact': 'צור קשר', 'cta': 'קריאה לפעולה', 'testimonials': 'המלצות', 'pricelist': 'מחירון'}
NAV_KEYS = ('services', 'pricelist', 'about', 'process', 'testimonials', 'faq', 'contact')


def _title(key: str, titles: dict) -> str:
    if key not in SECTION_WORDS and key not in titles:
        raise ValueError(f'no heading for section {key!r}: the sketch outlines only sections it can name')
    return titles.get(key) or SECTION_WORDS[key]


def _category_word(direction) -> str | None:
    """The word of the customer's own request that named the category (only when the brief names it), else None."""
    if direction.category_found != 'named' or not direction.category:
        return None
    from ..vertical_palettes import load
    text = (getattr(direction.sheet, 'customer', '') or '').lower()
    for word in load()['categories'][direction.category]['words']:
        if word.lower() in text:
            return word
    return None


def content(direction, copy: dict | None = None, *, year: str) -> tuple[dict, list[str]]:
    """(the library's content dict, the placeholders it uses). `copy` is a validated site-content document with at
    least the hero and the services, or None."""
    sheet = direction.sheet
    placeholders: list[str] = []
    phone = sheet.phone
    if not phone:
        phone = PHONE_LABEL
        placeholders.append('phone')
    keys = list(direction.sections)
    if copy is None:
        c = {'name': direction.business, 'title': f'{direction.business} – סקיצה', 'year': year,
             'description': DESCRIPTION.format(name=direction.business), 'direction': direction.art_direction,
             'phone': phone}
        placeholders.append('description')
        for key in ('whatsapp', 'email', 'address'):
            if getattr(sheet, key, None):
                c[key] = getattr(sheet, key)
        if getattr(sheet, 'hours', None):
            c['hours'] = ' · '.join(sheet.hours)
        hero = {'title': direction.business, 'lead': HERO_LEAD, 'cta': HERO_CTA}
        word = _category_word(direction)
        if word:
            hero['eyebrow'] = word
        placeholders += ['hero.lead', 'hero.cta']
        c['hero'] = hero
        written = {'hero'}
    else:
        from ..site_content.render import to_library
        shown = dataclasses.replace(sheet, phone=phone)
        c = to_library(copy, shown, direction=direction.art_direction, year=year, outline_titles=direction.titles,
                       order=keys)
        # the sketch's own menu: the sections of the page, whether written or outlined
        written = {'hero'} | {k for k in ('services',) if k in copy['sections']}
    for key in keys:
        if key in written:
            continue
        c[key] = {'outline': True, 'title': _title(key, direction.titles)}
        placeholders.append(f'skeleton:{key}')
    c['nav'] = [(k, _title(k, direction.titles)) for k in keys if k in NAV_KEYS]
    return c, placeholders
