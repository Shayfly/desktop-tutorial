"""The content document's schema: what the copy model may write, per section, and which sections it is offered.

SCHEMA names the document format. Every field has a type and a bound sized for the page (a title that fits the
320 px phone and G-APPLE's 30/60-character render test; a list long enough for a real page and short enough for the
45,000 characters the truth gate reads). Unknown keys are an error, never dropped (validate.py). A section is offered
only when the customer's facts give it a basis: the palette's sections (directions.json 'sections') always; a numbers
strip with at least two numbers the customer wrote; testimonials only with reviews the customer gave (references);
a price list only with prices the customer gave (references). With the customer's own outline (page_outline), the
outline IS the page: its sections, in its order, under the customer's own names (the eyebrow and the menu label are
the customer's title, filled by the platform). A section never offered is said in `skipped` with its reason.
"""
from __future__ import annotations

from dataclasses import dataclass

SCHEMA = '148ai.site_content/1'


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
    return {'eyebrow': Str(40, True), 'title': Str(70), 'lead': Str(220, True), **({'nav': Str(24)} if nav else {})}


SECTIONS = {
    'hero': {'eyebrow': Str(40, True), 'title': Str(70), 'lead': Str(220), 'cta': Str(30), 'note': Str(90, True),
             'panel_label': Str(40, True), 'panel_figure': Obj({'value': Num(), 'caption': Str(40)}, True)},
    'stats': {'label': Str(40, True), 'items': Lst(2, 4, Obj({'value': Num(), 'label': Str(30)}))},
    'services': {**_head(), 'items': Lst(2, 8, Obj({'title': Str(40), 'desc': Str(220)}))},
    'about': {**_head(), 'paragraphs': Lst(1, 3, Str(400)),
              'facts': Lst(1, 4, Obj({'label': Str(20), 'value': Str(80)}), True)},
    'process': {**_head(), 'steps': Lst(2, 6, Obj({'title': Str(40), 'desc': Str(200)}))},
    'faq': {**_head(), 'items': Lst(2, 8, Obj({'q': Str(90), 'a': Str(400)}))},
    'cta': {'title': Str(70), 'text': Str(200, True)},
    'testimonials': {**_head(), 'items': Lst(1, 6, Ref('@review'))},
    'pricelist': {**_head(), 'groups': Lst(1, 6, Obj({'title': Str(40), 'items': Lst(1, 12, Obj(
        {'name': Str(40), 'price': Ref('@price'), 'desc': Str(120, True)}))}))},
    'contact': {**_head(), 'topics': Lst(2, 6, Str(30), True)},
}
TOP = {'schema': None, 'name': Str(60), 'tagline': Str(50), 'description': Str(160), 'layout': None,
       'sections': None}
NAV_SECTIONS = ('services', 'about', 'process', 'faq', 'testimonials', 'pricelist', 'contact')
# sections the library has that this route never offers in slice 1, and why (said in `skipped`)
NEVER = {'team': 'no team members in the customer\'s facts', 'gallery': 'gallery images are not on this route yet'}


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
    basis = {'stats': len(sheet.numbers) >= 2, 'testimonials': bool(sheet.reviews), 'pricelist': bool(sheet.prices),
             'contact': True}
    reason = {'stats': 'fewer than two numbers the customer wrote', 'testimonials': 'no review the customer gave',
              'pricelist': 'no price the customer gave'}
    offered: dict[str, str] = {}
    skipped: list[tuple[str, str]] = []
    if order is not None:
        for key in ['hero'] + [k for k in order if k != 'hero']:
            if key in NEVER or not basis.get(key, True):
                raise ValueError(f'outline section {key!r} has no basis on this route: {NEVER.get(key) or reason[key]}')
            offered[key] = 'required'
        skipped += [(k, "not in the customer's outline") for k in SECTIONS if k not in offered]
    else:
        for key in palette['sections']:
            offered[key] = 'required'
        for key in ('stats', 'testimonials', 'pricelist'):
            if key in offered:
                continue
            if basis[key]:
                offered[key] = 'optional'
            else:
                skipped.append((key, reason[key]))
    skipped += [(k, why) for k, why in NEVER.items()]
    return offered, skipped


def _describe(spec) -> object:
    if isinstance(spec, Str):
        return f"string, at most {spec.max} characters, Hebrew" + (' (optional)' if spec.optional else '')
    if isinstance(spec, Num):
        return ('one of numbers_you_may_use, written as the customer wrote it (may start with "+")'
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
        top['name'] = ("the business name exactly as the customer wrote it (a part of the customer's text), "
                       'at most 60 characters')
    top.update({'tagline': _describe(TOP['tagline']), 'description': _describe(TOP['description']),
                'layout (optional)': {axis: f'one of {list(opts)}' for axis, opts in layouts.items()},
                'sections': sections})
    return top
