"""The content document is checked before anything is rendered (deterministic input validation, no model).

validate(doc, sheet, offered, outline_titles) -> [Problem(path, code, why, severity)]. A 'block' problem sends the
document back to the model once (agents.ContentAgent), then fails the build loudly as site_content_invalid. A 'warn'
problem (UNVERIFIABLE_CLAIM while its gate SITE_CLAIMS is calibrating, skill_units/gate.CALIBRATING) goes to the evidence.

Codes (every one has a failing document in tests/test_site_content_validate.py):
  SCHEMA_SHAPE        a missing field, a wrong type, an unknown key (never dropped), a section that was not offered
  LAYOUT_UNKNOWN      a layout axis or variant the library does not have (section_library.LAYOUTS)
  TOO_LONG / TOO_FEW / TOO_MANY / EMPTY_TEXT
  NOT_HEBREW          a copy string with no Hebrew letter
  FACT_IN_COPY        a phone, e-mail, street address, opening hours or link in copy: facts are the platform's slots
  INVENTED_NUMBER     a digit run the customer never wrote (fold_digits, thousands separators normalised)
  INVENTED_COUNT      a typed count (reviews, rating, customers) the canon does not hold (fact_canon.count_facts)
  REF_UNKNOWN         a @price:N / @review:N the sheet does not have, or a review reference outside testimonials
  REVIEW_TEXT_WRITTEN a quote with a dash and a name in copy: reviews are the customer's, by reference only
  PRICE_NOT_GIVEN     a currency sign or word in copy: prices are the customer's spans, by reference only
  NAME_NOT_GIVEN      the business name is not part of the customer's text (or differs from the declared name)
  PLACEHOLDER         template text (the copy_placeholder unit's patterns, a blanked fact label «...»)
  UNVERIFIABLE_CLAIM  a superlative no fact supports ("המוביל", "הטוב ביותר", "מס׳ 1"), warn until calibrated
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import fact_canon as F
from . import schema as K

CODES = ('SCHEMA_SHAPE', 'LAYOUT_UNKNOWN', 'TOO_LONG', 'TOO_FEW', 'TOO_MANY', 'EMPTY_TEXT', 'NOT_HEBREW',
         'FACT_IN_COPY', 'INVENTED_NUMBER', 'INVENTED_COUNT', 'REF_UNKNOWN', 'REVIEW_TEXT_WRITTEN', 'PRICE_NOT_GIVEN',
         'NAME_NOT_GIVEN', 'PLACEHOLDER', 'UNVERIFIABLE_CLAIM')
CLAIMS_GATE = 'SITE_CLAIMS'
_HEBREW = re.compile('[א-ת]')
_REF = re.compile(r'@(price|review):(\d{1,3})')
_LINK = re.compile(r'https?://|www\.|wa\.me|mailto:|tel:', re.I)
_CURRENCY = re.compile(r'₪|ש["״]ח|\bשקל(?:ים)?\b|\bNIS\b|\$|€|\bUSD\b|\bEUR\b', re.I)
_BLANKED = re.compile(r'«[^»]{1,20}»')
_CLAIM = re.compile(r'(?<![א-ת])(?:ו?ה?מוביל(?:ה|ים|ות)?|ה?טוב(?:ה|ים|ות)? ביותר|הכי (?:טוב|טובה|טובים|זול|מקצועי)'
                    r'|מס[׳\'"]?\s*1|מספר 1|מספר אחת|ה?גדול(?:ה|ים)? ביותר|ה?זול(?:ה|ים)? ביותר|מובטח(?:ת|ים)?'
                    r'|ללא תחרות|אין כמונו)(?![א-ת])')
_NUM_VALUE = re.compile(r'^\+?\d[\d,]*$')
_NUMBER_PATH = re.compile(r'(?:stats\.items\[\d+\]|hero\.panel_figure)\.value$')     # a customer number, not copy


@dataclass(frozen=True)
class Problem:
    path: str
    code: str
    why: str
    severity: str = 'block'

    def to_dict(self) -> dict:
        return {'path': self.path, 'code': self.code, 'why': self.why, 'severity': self.severity}


def leaves(doc: dict) -> list[tuple[str, str]]:
    """(path, text) of every model-written copy string: the section strings, the tagline and the description. The
    business name is the customer's own words and a reference is the customer's fact -- neither is copy."""
    out: list[tuple[str, str]] = []

    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f'{path}.{k}')
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f'{path}[{i}]')
        elif isinstance(value, str) and not re.fullmatch(r'@(?:price|review):\d{1,3}', value) \
                and not _NUMBER_PATH.search(path):
            out.append((path.lstrip('.'), value))
    for key in ('tagline', 'description'):
        if isinstance(doc.get(key), str):
            out.append((key, doc[key]))
    walk(doc.get('sections') if isinstance(doc.get('sections'), dict) else {}, 'sections')
    return out


def _shape(value, spec, path, out, *, key=None):
    if isinstance(spec, K.Str):
        if not isinstance(value, str):
            out.append(Problem(path, 'SCHEMA_SHAPE', f'expected a string, got {type(value).__name__}'))
        elif not value.strip():
            out.append(Problem(path, 'EMPTY_TEXT', 'an empty string: leave an optional field out instead'))
        elif len(value) > spec.max:
            out.append(Problem(path, 'TOO_LONG', f'{len(value)} characters; at most {spec.max}'))
    elif isinstance(spec, K.Num):
        if not isinstance(value, str) or not _NUM_VALUE.match(value.strip()):
            out.append(Problem(path, 'SCHEMA_SHAPE', 'expected a number as the customer wrote it, e.g. "2008" or "+1,500"'))
    elif isinstance(spec, K.Ref):
        if not isinstance(value, str) or not re.fullmatch(re.escape(spec.prefix) + r':\d{1,3}', value):
            out.append(Problem(path, 'SCHEMA_SHAPE', f'expected a reference "{spec.prefix}:N"'))
    elif isinstance(spec, K.Lst):
        if not isinstance(value, list):
            out.append(Problem(path, 'SCHEMA_SHAPE', f'expected a list, got {type(value).__name__}'))
            return
        if len(value) < spec.min:
            out.append(Problem(path, 'TOO_FEW', f'{len(value)} item(s); at least {spec.min}'))
        if len(value) > spec.max:
            out.append(Problem(path, 'TOO_MANY', f'{len(value)} items; at most {spec.max}'))
        for i, item in enumerate(value[:spec.max]):
            _shape(item, spec.item, f'{path}[{i}]', out)
    elif isinstance(spec, K.Obj):
        _fields(value, spec.fields, path, out)
    else:
        raise TypeError(f'unknown field spec at {path}: {spec!r}')


def _fields(value, fields: dict, path: str, out: list):
    if not isinstance(value, dict):
        out.append(Problem(path, 'SCHEMA_SHAPE', f'expected an object, got {type(value).__name__}'))
        return
    for k in value:
        if k not in fields:
            out.append(Problem(f'{path}.{k}', 'SCHEMA_SHAPE', f'unknown key {k!r} (allowed: {sorted(fields)})'))
    for k, spec in fields.items():
        if k not in value:
            if not getattr(spec, 'optional', False):
                out.append(Problem(f'{path}.{k}', 'SCHEMA_SHAPE', 'a required field is missing'))
            continue
        _shape(value[k], spec, f'{path}.{k}', out)


def _text_problems(path: str, text: str, sheet, claim_severity: str) -> list[Problem]:
    from ..opening_hours import spans as hour_spans
    out = []
    plain = _REF.sub(' ', text)
    if not _HEBREW.search(plain):
        out.append(Problem(path, 'NOT_HEBREW', 'a copy string with no Hebrew letter'))
    shown, odd = F.page_phones(plain)
    if (shown or odd or F._EMAIL.search(plain) or F._STREET.search(plain) or hour_spans(plain)
            or F._HOURS.search(plain) or _LINK.search(plain)):
        out.append(Problem(path, 'FACT_IN_COPY', 'a phone, e-mail, address, opening hours or link in copy: the '
                                                 'platform shows the facts in their own places; leave them out'))
    allowed = sheet.allowed_numbers()
    from .facts import norm_number
    invented = sorted({norm_number(m.group(0)) for m in re.finditer(r'\d[\d,.]*\d|\d', F.fold_digits(plain))}
                      - allowed)
    if invented:
        out.append(Problem(path, 'INVENTED_NUMBER', f'number(s) the customer never wrote: {", ".join(invented)}'))
    counts = sheet.counts or {}
    bad = [ref for kind, value, ref in F.count_facts(plain) if value not in (counts.get(kind) or ())]
    if bad:
        out.append(Problem(path, 'INVENTED_COUNT', f'count(s) the customer never gave: {", ".join(bad)}'))
    if F._QUOTE.search(plain):
        out.append(Problem(path, 'REVIEW_TEXT_WRITTEN', 'a quote with a name: reviews are the customer\'s, by reference'))
    if _CURRENCY.search(plain):
        out.append(Problem(path, 'PRICE_NOT_GIVEN', 'a price in copy: write the customer\'s price as its @price:N'))
    for m in _REF.finditer(text):
        kind, ref = m.group(1), m.group(0)
        if kind == 'review':
            out.append(Problem(path, 'REF_UNKNOWN', f'{ref} in copy: a review is shown only in testimonials'))
        elif sheet.price(ref) is None:
            out.append(Problem(path, 'REF_UNKNOWN', f'{ref} is not one of the customer\'s prices'))
    from ..skill_units.copy_placeholder.probe import _TEXT as _PLACEHOLDER
    if _PLACEHOLDER.search(plain) or _BLANKED.search(plain):
        out.append(Problem(path, 'PLACEHOLDER', 'template text or a blanked fact label left in copy'))
    m = _CLAIM.search(plain)
    if m:
        out.append(Problem(path, 'UNVERIFIABLE_CLAIM', f'"{m.group(0)}": a claim no fact the customer gave supports',
                           claim_severity))
    return out


def validate(doc, sheet, offered: dict, outline_titles: dict | None = None, *, layouts: dict | None = None,
             claim_mode: str | None = None) -> list[Problem]:
    """Every problem of a content document against the sheet and the offered sections."""
    from ..section_library import LAYOUTS
    from ..skill_units import gate as G
    outline_titles = outline_titles or {}
    layouts = LAYOUTS if layouts is None else layouts
    mode = claim_mode or G.mode(CLAIMS_GATE)
    claim_severity = 'block' if mode == 'block' else 'warn'
    out: list[Problem] = []
    if not isinstance(doc, dict):
        return [Problem('', 'SCHEMA_SHAPE', f'expected one JSON object, got {type(doc).__name__}')]
    for k in doc:
        if k not in K.TOP:
            out.append(Problem(k, 'SCHEMA_SHAPE', f'unknown key {k!r} (allowed: {sorted(K.TOP)})'))
    if doc.get('schema') != K.SCHEMA:
        out.append(Problem('schema', 'SCHEMA_SHAPE', f'must be {K.SCHEMA!r}'))
    for key in ('tagline', 'description'):
        if key not in doc:
            out.append(Problem(key, 'SCHEMA_SHAPE', 'a required field is missing'))
        else:
            _shape(doc[key], K.TOP[key], key, out)
    name = doc.get('name')
    if sheet.name:
        if name is not None and name != sheet.name:
            out.append(Problem('name', 'NAME_NOT_GIVEN', f'the customer declared the name {sheet.name!r}'))
    elif not isinstance(name, str) or not name.strip():
        out.append(Problem('name', 'SCHEMA_SHAPE', 'the business name is required'))
    else:
        _shape(name, K.TOP['name'], 'name', out)
        if ' '.join(name.split()) not in ' '.join(sheet.customer.split()):
            out.append(Problem('name', 'NAME_NOT_GIVEN', 'the business name must be written as the customer wrote it'))
    layout = doc.get('layout')
    if layout is not None:
        if not isinstance(layout, dict):
            out.append(Problem('layout', 'SCHEMA_SHAPE', 'expected an object {axis: variant}'))
        else:
            for axis, variant in layout.items():
                if axis not in layouts or variant not in layouts[axis]:
                    out.append(Problem(f'layout.{axis}', 'LAYOUT_UNKNOWN',
                                       f'{axis}={variant!r}; the library has {dict(layouts)}'))
    sections = doc.get('sections')
    if not isinstance(sections, dict):
        out.append(Problem('sections', 'SCHEMA_SHAPE', 'expected an object of sections'))
        return out
    for key in sections:
        if key not in offered:
            out.append(Problem(f'sections.{key}', 'SCHEMA_SHAPE', f'section {key!r} was not offered'))
    for key, need in offered.items():
        if key not in sections:
            if need == 'required':
                out.append(Problem(f'sections.{key}', 'SCHEMA_SHAPE', 'a required section is missing'))
            continue
        _fields(sections[key], K.spec_for(key, outline_titles), f'sections.{key}', out)
    for path, text in leaves(doc):
        out += _text_problems(path, text, sheet, claim_severity)
    allowed = sheet.allowed_numbers()
    from .facts import norm_number
    for path, value in _number_values(sections):
        if isinstance(value, str) and _NUM_VALUE.match(value.strip()) and norm_number(value.lstrip('+')) not in allowed:
            out.append(Problem(path, 'INVENTED_NUMBER', f'{value!r} is not a number the customer wrote'))
    for path, value in _refs(sections):
        if (value.startswith('@price') and sheet.price(value) is None) or \
                (value.startswith('@review') and sheet.review(value) is None):
            out.append(Problem(path, 'REF_UNKNOWN', f'{value} is not in the customer\'s facts'))
    return out


def _number_values(sections: dict):
    for key in ('hero', 'stats'):
        s = sections.get(key)
        if not isinstance(s, dict):
            continue
        if key == 'hero' and isinstance(s.get('panel_figure'), dict):
            yield 'sections.hero.panel_figure.value', s['panel_figure'].get('value')
        if key == 'stats' and isinstance(s.get('items'), list):
            for i, item in enumerate(s['items']):
                if isinstance(item, dict):
                    yield f'sections.stats.items[{i}].value', item.get('value')


def _refs(sections: dict):
    t = sections.get('testimonials')
    if isinstance(t, dict) and isinstance(t.get('items'), list):
        for i, v in enumerate(t['items']):
            if isinstance(v, str) and v.startswith('@'):
                yield f'sections.testimonials.items[{i}]', v
    p = sections.get('pricelist')
    if isinstance(p, dict) and isinstance(p.get('groups'), list):
        for gi, g in enumerate(p['groups']):
            for ii, item in enumerate((g or {}).get('items') or [] if isinstance(g, dict) else []):
                if isinstance(item, dict) and isinstance(item.get('price'), str) and item['price'].startswith('@'):
                    yield f'sections.pricelist.groups[{gi}].items[{ii}].price', item['price']


def blocking(problems: list[Problem]) -> list[Problem]:
    return [p for p in problems if p.severity == 'block']
