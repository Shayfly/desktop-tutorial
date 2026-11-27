"""The direction sketch (S6.3, slice 1): a page the customer sees within seconds of a first request, drawn by the SAME
functions the build uses, with no model and at no cost. Palette, art direction, font pair, section outline and layout
come from `site_content.direction` (the one function decide() also calls) and the section library; nothing here picks a
colour, a font or a section of its own. The page is marked "draft" and says which of its words are placeholders.

This slice is pure: no model call, no database, no route, no screen. It writes no plan, contract, approval or build row
and never changes the brief (it imports none of that code). Later slices reserve a model call for the headline (the
owner's decision of 2026-11-26: the first sketch in a project is on the company, capped at $0.10), store the sketch and
serve it.

  OMNI_DIRECTION_SKETCH = off | accounts | on   (default off; any other value raises)
  OMNI_DIRECTION_SKETCH_ACCOUNTS                 comma list of account ids, read when the flag is 'accounts' (an empty
                                                 list with 'accounts' raises: never a silent off)

`ready()` is a pure function of the brief, the account and the project's state; the first condition that fails names
itself (the reason is never silent and never a guess)."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

FLAG = 'OMNI_DIRECTION_SKETCH'
ACCOUNTS = 'OMNI_DIRECTION_SKETCH_ACCOUNTS'
MODES = ('off', 'accounts', 'on')
PROMPT_BOUND = 12000          # the design's bound on the brief text a sketch reads (the build's own bound is larger)


def mode() -> str:
    """OMNI_DIRECTION_SKETCH: off | accounts | on. Any other value raises; never a silent default."""
    value = os.environ.get(FLAG, 'off').strip().lower()
    if value not in MODES:
        raise ValueError(f'{FLAG} must be one of {MODES}, not {value!r}')
    return value


def accounts() -> set[str]:
    listed = {a.strip() for a in os.environ.get(ACCOUNTS, '').split(',') if a.strip()}
    if not listed:
        raise ValueError(f'{FLAG}=accounts needs {ACCOUNTS}; none is listed')
    return listed


@dataclass(frozen=True)
class SketchDirection:
    """What a sketch shows, as plain data (`to_dict`) plus the fact sheet the words are bound to."""
    business: str
    category: str | None
    category_found: str | None
    palette: str
    art_direction: str
    colours: dict
    pair: str
    script: str
    contract: dict
    sections: list            # section keys in page order, the hero first: what the build's outline will be
    titles: dict              # the customer's own section titles, by key
    layout: dict
    phone_given: bool
    voice: str = ''           # the palette's voice and the trade's verified words: what the words' writer is told
    domain_words: tuple = ()
    sheet: object = field(default=None, compare=False, repr=False)

    def to_dict(self) -> dict:
        return {'business': self.business, 'category': self.category, 'category_found': self.category_found,
                'palette': self.palette, 'art_direction': self.art_direction, 'colours': dict(self.colours),
                'pair': self.pair, 'script': self.script, 'contract_fp': self.contract['fingerprint'],
                'sections': list(self.sections), 'titles': dict(self.titles), 'layout': dict(self.layout),
                'phone_given': self.phone_given}


@dataclass(frozen=True)
class Ready:
    ok: bool
    reason: str | None = None
    direction: SketchDirection | None = None


def prompt_of(brief) -> str:
    """The text a sketch reads: the prompt the BUILD would start from for this brief (discovery.build_prompt: the
    customer's request, then the decisions block), cut at PROMPT_BOUND characters. Raises ValueError when the brief's
    decisions alone are past the build's bound (ready() says `prompt_too_long`)."""
    from .. import discovery
    return discovery.build_prompt(brief)[0][-PROMPT_BOUND:]


def direction_of(brief) -> SketchDirection:
    """The direction the build would take for this (draft) brief, from `site_content.direction`. Raises ValueError
    with the reason when the build would not take the library route (ready() turns that into `not_ready`)."""
    from .. import site_content as SC
    from .. import section_library as L
    from ..site_content.schema import offered_sections
    d = SC.direction(prompt_of(brief), lang='he', phone_optional=True)
    if d.reason:
        raise ValueError(d.reason)
    business = d.business
    offered, _ = offered_sections(d.sheet, d.entry, d.order, d.titles)
    keys = [k for k, v in offered.items() if v == 'required' and k != 'stats']   # the numbers strip needs real numbers
    ordered = ['hero'] + [k for k in (d.order if d.order is not None else [k for k, _ in L.ORDER]) if k in keys and k != 'hero']
    layout = L.layout_for({'name': business, 'direction': d.entry['direction']})
    return SketchDirection(
        business=business, category=d.category, category_found=d.domain_kw['category_found'], palette=d.palette,
        art_direction=d.entry['direction'], colours=d.colours, pair=d.pair['id'], script=d.script, contract=d.contract,
        sections=ordered, titles=dict(d.titles), layout=layout, phone_given=bool(d.sheet.phone), voice=d.entry['voice'],
        domain_words=tuple(d.domain_kw.get('domain_words') or ()), sheet=d.sheet)


def ready(brief, *, account_id: str | None, has_version: bool, has_open_build: bool) -> Ready:
    """The nine conditions of the design, in order; the first that fails names itself."""
    from .. import discovery, site_content as SC
    # 1. the flag admits the account
    m = mode()
    if m == 'off':
        return Ready(False, 'flag_off')
    if m == 'accounts' and account_id not in accounts():
        return Ready(False, 'account_not_listed')
    # 2. the site library route admits the account (the sketch shows what that route builds)
    lib = SC.mode()
    if lib == 'off' or (lib == 'accounts' and account_id not in SC.accounts()):
        return Ready(False, 'library_route_off')
    # 3. a website
    if not discovery.is_website(brief):
        return Ready(False, 'not_a_site')
    try:
        prompt = prompt_of(brief)
    except ValueError:
        return Ready(False, 'prompt_too_long')
    # 4. Hebrew: the library writes Hebrew only
    from ..page_locale import rtl_language
    if rtl_language(prompt) != 'he':
        return Ready(False, 'not_hebrew')
    # 5. nothing was built yet
    if has_version or has_open_build:
        return Ready(False, 'already_built')
    # 8 (read from the brief itself): the site does not already say it stores records or needs sign-in
    values = brief.values()
    if (discovery.stores_by_own_answer(brief) or values.get('content_only') == 'no'
            or values.get('login') in ('simple', 'roles')):
        return Ready(False, 'not_content_site')
    # 6, 7, 9: the direction itself, from the build's own function
    d = SC.direction(prompt, lang='he', phone_optional=True)
    if d.business is None:
        return Ready(False, 'no_name')
    colour_answered = (brief.fields.get('color') or {}).get('source') in ('answer', 'message')
    if d.domain_kw['category_found'] == 'none' and not colour_answered:
        return Ready(False, 'no_subject')
    if d.reason:
        return Ready(False, d.reason)           # names itself: no_design_contract: ..., phone_not_one, outline_..., ...
    return Ready(True, None, direction_of(brief))


def direction_fp(d: SketchDirection) -> str:
    """sha256 over what the customer sees as the direction: the palette's colours and the colours shown, the art direction, the font pair,
    the section order, the layout and the library version. A new sketch is offered only when it changes."""
    from .. import section_library as L
    # the colours the page really shows (the contract's): a colour the customer named changes the primary only
    shown = {k: v for k, v in d.contract['tokens'].items() if k.startswith('--color-')}
    body = {'colours': d.colours, 'shown': shown, 'art_direction': d.art_direction, 'pair': d.pair, 'sections': d.sections,
            'layout': d.layout, 'library': L.LIBRARY_VERSION}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def copy_fp(d: SketchDirection) -> str:
    """sha256 over the business name, the category and the customer's own words: the model's words are reused for as
    long as these do not change."""
    customer = hashlib.sha256((getattr(d.sheet, 'customer', '') or '').encode('utf-8')).hexdigest()
    body = {'business': d.business, 'category': d.category, 'customer': customer}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
