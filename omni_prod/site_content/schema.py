"""The content document's schema: what the copy model may write, per section, and which sections it is offered.

SCHEMA names the document format. Every field has a type and a bound sized for the page: a heading's length is a
layout rule (it fits the 320 px phone and G-APPLE's 30/60-character render test; the correction fixes a long one), and
a list holds what a real business has (the owner, 2026-11-26, WAREHOUSE 136 option a: the item counts were limits that
are not money -- 8 services, 8 questions, 6 groups of 12 prices -- and were raised; ITEM_MAXIMA_2026_11_26 keeps the
old and new numbers side by side). A page longer than the 45,000 characters the preview smoke returns is judged whole
before the sandbox (agents.prepass) and, in the sandbox, up to its last complete section (preview_smoke.served_cut):
never a fact cut in half. Unknown keys are an error, never dropped (validate.py). A section is offered
only when the customer's facts give it a basis: the palette's sections (directions.json 'sections') always; a numbers
strip with at least two numbers the customer wrote; testimonials only with reviews the customer gave (references);
a price list only with prices the customer gave (references). With the customer's own outline (page_outline), the
outline IS the page: its sections, in its order, under the customer's own names (the eyebrow and the menu label are
the customer's title, filled by the platform). A section never offered is said in `skipped` with its reason.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..typography import script as _script

SCHEMA = '148ai.site_content/1'
# The route's pages are Hebrew (site_content.decide): every heading's bound is the Hebrew script's limit (warehouse
# 129, typography/scripts.json) -- the number the section library enforces on the rendered page.
_H = _script('hebrew')['heading_max_chars']


@dataclass(frozen=True)
class Str:
    max: int
    optional: bool = False


@dataclass(frozen=True)
class Num:
    """A number the customer wrote, as the page shows it ("2008", "+1,500")."""
    optional: bool = False


@dataclass(frozen=True)
class Ref:
    prefix: str             # '@price' | '@review'
    optional: bool = False


@dataclass(frozen=True)
class Lst:
    min: int
    max: int
    item: object
    optional: bool = False


@dataclass(frozen=True)
class Obj:
    fields: dict
    optional: bool = False


def _head(nav: bool = True) -> dict:
    return {'eyebrow': Str(40, True), 'title': Str(_H['h2']), 'lead': Str(220, True), **({'nav': Str(24)} if nav else {})}


# The owner, 2026-11-26 (WAREHOUSE 136, option a): how many items a section holds is not money, so a real business
# fits. {(section, list): (old maximum, new maximum)}; the minimums are unchanged. Why each number:
#   services, faq 24     a clinic, a law firm or a salon lists 10-20 services and as many questions; 24 leaves room
#   process 12           a renovation or an onboarding in 10-12 steps
#   testimonials 12      references to reviews the customer gave; a wall of twelve quotes
#   pricelist 12 x 30    a cafe or restaurant menu: up to 12 categories of up to 30 dishes (360 prices)
#   contact topics 12    one form topic per service category
#   about 6 paragraphs, 12 facts; stats 6 (one row on a desktop, two on a tablet)
# The layout at these maxima is proven in a real browser (tests/test_section_library.py, ItemMaxima: no sideways
# scroll at 320-1440 px, nothing clipped, body text at least 14 px, the production visual check clean).
ITEM_MAXIMA_2026_11_26 = {('stats', 'items'): (4, 6), ('services', 'items'): (8, 24), ('about', 'paragraphs'): (3, 6),
                          ('about', 'facts'): (4, 12), ('process', 'steps'): (6, 12), ('faq', 'items'): (8, 24),
                          ('testimonials', 'items'): (6, 12), ('pricelist', 'groups'): (6, 12),
                          ('pricelist', 'groups.items'): (12, 30), ('contact', 'topics'): (6, 12)}
SECTIONS = {
    'hero': {'eyebrow': Str(40, True), 'title': Str(_H['h1']), 'lead': Str(220), 'cta': Str(30), 'note': Str(90, True),
             'panel_label': Str(40, True), 'panel_figure': Obj({'value': Num(), 'caption': Str(40)}, True)},
    'stats': {'label': Str(40, True), 'items': Lst(2, 6, Obj({'value': Num(), 'label': Str(30)}))},
    # `item`: when the customer's items have pictures (sheet.services_pictured) each card names the item whose picture it
    # carries, "@item:N" -- the renderer attaches the picture; the model never sees or chooses one (visual plan S3)
    'services': {**_head(), 'items': Lst(2, 24, Obj({'title': Str(_H['h3']), 'desc': Str(220), 'item': Ref('@item', True)}))},
    'gallery': {**_head()},
    'about': {**_head(), 'paragraphs': Lst(1, 6, Str(400)),
              'facts': Lst(1, 12, Obj({'label': Str(20), 'value': Str(80)}), True)},
    'process': {**_head(), 'steps': Lst(2, 12, Obj({'title': Str(_H['h3']), 'desc': Str(200)}))},
    'faq': {**_head(), 'items': Lst(2, 24, Obj({'q': Str(90), 'a': Str(400)}))},
    'cta': {'title': Str(_H['h2']), 'text': Str(200, True)},
    'testimonials': {**_head(), 'items': Lst(1, 12, Ref('@review'))},
    'pricelist': {**_head(), 'groups': Lst(1, 12, Obj({'title': Str(_H['h3']), 'items': Lst(1, 30, Obj(
        {'name': Str(_H['h4']), 'price': Ref('@price'), 'desc': Str(120, True)}))}))},
    'contact': {**_head(), 'topics': Lst(2, 12, Str(30), True)},
}
TOP = {'schema': None, 'name': Str(60), 'tagline': Str(50), 'description': Str(160), 'layout': None,
       'sections': None, 'shortened': None}
# Review S5 (2026-11-26), narrowed by the owner's order of 16:10 (no product token cap; agents.output_maximum): only
# when a list would really not fit the model's own output maximum does the model shorten it, and then it says which in
# `shortened` -- never silently, and never by spending the corrections on TOO_MANY. The lists it may name
# (section.field), each only when its section is offered:
SHORTENABLE = ('stats.items', 'services.items', 'about.paragraphs', 'about.facts', 'process.steps', 'faq.items',
               'testimonials.items', 'pricelist.groups', 'contact.topics')
NAV_SECTIONS = ('services', 'about', 'process', 'faq', 'testimonials', 'pricelist', 'gallery', 'contact')
# sections the library has that this route never offers in slice 1, and why (said in `skipped`)
NEVER = {'team': 'no team members in the customer\'s facts'}


def platform_fields(key: str, outline_titles: dict) -> set[str]:
    """Fields of a section the platform fills: with the customer's outline, its eyebrow and menu label are the
    customer's own title for the section."""
    return {'eyebrow', 'nav'} if key in outline_titles and key != 'hero' else set()


def spec_for(key: str, outline_titles: dict) -> dict:
    drop = platform_fields(key, outline_titles)
    return {k: v for k, v in SECTIONS[key].items() if k not in drop}


def offered_sections(sheet, palette: dict, order: list[str] | None, outline_titles: dict | None = None
                     ) -> tuple[dict, list[tuple[str, str]]]:
    """({section: 'required' | 'optional'}, [(section, why it is not offered)])."""
    outline_titles = outline_titles or {}
    basis = {'stats': len(sheet.allowed_numbers()) >= 2, 'testimonials': bool(sheet.reviews), 'pricelist': bool(sheet.prices),
             'gallery': bool(sheet.gallery_pictures()), 'contact': True}
    reason = {'stats': 'fewer than two numbers the customer wrote', 'testimonials': 'no review the customer gave',
              'pricelist': 'no price the customer gave', 'gallery': 'no picture for a gallery'}
    offered: dict[str, str] = {}
    skipped: list[tuple[str, str]] = []
    if order is not None:
        for key in ['hero'] + [k for k in order if k != 'hero']:
            if key in NEVER or not basis.get(key, True):
                raise ValueError(f'outline section {key!r} has no basis on this route: {NEVER.get(key) or reason[key]}')
            offered[key] = 'required'
        if basis['gallery'] and 'gallery' not in offered:
            offered['gallery'] = 'required'      # a picture the page must show has its section, after the customer's own
        skipped += [(k, "not in the customer's outline") for k in SECTIONS if k not in offered]
    else:
        for key in palette['sections']:
            offered[key] = 'required'
        for key in palette.get('optional_sections', ()):    # an unnamed business (site_content.unnamed_entry)
            offered.setdefault(key, 'optional')
        for key in ('stats', 'testimonials', 'pricelist', 'gallery'):
            if key in offered:
                continue
            if basis[key]:
                offered[key] = 'required' if key == 'gallery' else 'optional'     # pictures paid for are shown
            else:
                skipped.append((key, reason[key]))
        said = {k for k, _ in skipped}
        skipped += [(k, "not one of this palette's sections") for k in SECTIONS if k not in offered and k not in said]
    skipped += [(k, why) for k, why in NEVER.items()]
    return offered, skipped


def _describe(spec) -> object:
    if isinstance(spec, Str):
        return f"string, at most {spec.max} characters, Hebrew" + (' (optional)' if spec.optional else '')
    if isinstance(spec, Num):
        return ('one of numbers_you_may_use, written as the customer wrote it (may start with "+"); its caption or '
                'label names what that number counts'
                + (' (optional)' if spec.optional else ''))
    if isinstance(spec, Ref):
        return f'a reference "{spec.prefix}:N" from the list you were given' + (' (optional)' if spec.optional else '')
    if isinstance(spec, Lst):
        return {'list': f'{spec.min} to {spec.max} items' + (' (optional)' if spec.optional else ''),
                'item': _describe(spec.item)}
    if isinstance(spec, Obj):
        out = {k: _describe(v) for k, v in spec.fields.items()}
        return {'object (optional)': out} if spec.optional else out
    raise TypeError(f'unknown field spec {spec!r}')


def schema_for_model(offered: dict, outline_titles: dict, *, name_given: bool, layouts: dict) -> dict:
    """The JSON shape the model is asked to return."""
    sections = {}
    for key, need in offered.items():
        body = {k: _describe(v) for k, v in spec_for(key, outline_titles).items()}
        sections[key + ('' if need == 'required' else ' (optional section: include it only with real content)')] = body
    top = {'schema': SCHEMA}
    if not name_given:
        top['name'] = ("the business name: one of business_names_quoted exactly, or the part of one before its "
                       "' – ', at most 60 characters")
    top.update({'tagline': _describe(TOP['tagline']), 'description': _describe(TOP['description']),
                'layout (optional)': {axis: f'one of {list(opts)}' for axis, opts in layouts.items()},
                'sections': sections,
                'shortened (optional)': [{'list': 'one of ' + str([p for p in SHORTENABLE if p.split('.')[0] in offered]),
                                          'left_out': 'how many of the customer\'s items this list leaves out (1 or more)',
                                          'why': 'one short English sentence'}]})
    return top


def page_order(sheet, order: list[str] | None) -> list[str] | None:
    """The order the page is rendered in: the customer's outline, and -- when the sheet has pictures for a gallery that
    the outline does not name -- the gallery after it (offered_sections offers it as required)."""
    if order is None or 'gallery' in order or not sheet.gallery_pictures():
        return order
    return [*order, 'gallery']
