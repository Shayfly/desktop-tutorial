"""The content-document route (the wiring judges' winner, 2026-11-20; slice 1, the CTO's decisions of 2026-11-21).

For an approved CONTENT-ONLY Hebrew business site, the model no longer writes app.py or HTML. It writes the site's
copy as ONE JSON document, validated before rendering; the platform renders the section library deterministically
with the build's design contract, fills every fact from the fact sheet (fact_canon on the approved prompt), and writes
a fixed GET-only app.py, fixed tests and a manifest that covers every acceptance id. The engine loop, the executor chain
and every gate are unchanged; only the architect, the generator and the repairer of the engine are replaced, and two
route-level executors are added (agents.AdvisoryFilterExecutor, agents.SiteParityExecutor).

  OMNI_SITE_LIBRARY = off | accounts | on   (default off; any other value raises)
  OMNI_SITE_LIBRARY_ACCOUNTS                 comma list of account ids, read when the flag is 'accounts' (an empty
                                             list with 'accounts' raises: never a silent off)

With the flag off nothing here touches the engine: install() decides 'legacy' with reason flag_off, logs it, records
it for the evidence and returns -- the build is byte-identical to a build without this module
(tests/test_site_content_route.py). Every other legacy decision names its reason too (decide()); there is no silent
path, and no fallback to the legacy generator once the route was chosen.

Slice 1 scope: Hebrew; content_only_approved; one main phone, at most one address and one e-mail; WhatsApp only when the
customer's own words name it and its number is known; every palette in section_library.DIRECTIONS; no approved
window the library does not render (it renders section_library.RENDERED_WINDOWS: the cookie banner, DECISIONS.md
question 14 (b)); no uploaded logo; images only in the hero and story places; the customer's outline only when
every title maps to a library section (OUTLINE_MAP, exact titles, never guessed); no plan-governed approved
criteria. The fonts are a pair from the font-pair library (omni_prod/typography, warehouse 126), not the Design
line's one font.
"""
from __future__ import annotations

import datetime
import logging
import os
import re
from dataclasses import dataclass, field

FLAG = 'OMNI_SITE_LIBRARY'
ACCOUNTS = 'OMNI_SITE_LIBRARY_ACCOUNTS'
MODES = ('off', 'accounts', 'on')
ROUTE = 'section_library'
LEGACY = 'legacy'
_LOG = logging.getLogger(__name__)

# The customer's section titles (page_outline.outline) that name a library section, exactly (after spaces and quotes
# are normalised). A title not listed sends the build to the legacy path with that title as the reason.
OUTLINE_MAP = {
    'hero': ('פתיח', 'פתיחה', 'הירו', 'באנר', 'באנר ראשי', 'hero', 'intro', 'introduction', 'opening'),
    'services': ('שירותים', 'השירותים שלנו', 'תחומי התמחות', 'תחומי עיסוק', 'תחומי פעילות', 'מה אנחנו עושים',
                 'הטיפולים שלנו', 'טיפולים'),
    'about': ('על המשרד', 'עלינו', 'אודות', 'על העסק', 'מי אנחנו', 'הסיפור שלנו', 'על הקליניקה', 'על המרפאה',
              'על הסטודיו', 'קצת עלינו'),
    'process': ('איך זה עובד', 'תהליך העבודה', 'איך עובדים', 'שלבי העבודה', 'התהליך', 'איך זה עובד?'),
    'faq': ('שאלות נפוצות', 'שאלות ותשובות', 'שו"ת'),
    'contact': ('צור קשר', 'צרו קשר', 'יצירת קשר', 'פרטי התקשרות', 'דברו איתנו'),
    'testimonials': ('המלצות', 'המלצות לקוחות', 'לקוחות ממליצים', 'מה אומרים עלינו'),
    'pricelist': ('מחירון', 'מחירים', 'תפריט'),
}
_TITLE_TO_KEY = {t: k for k, titles in OUTLINE_MAP.items() for t in titles}


def mode() -> str:
    """OMNI_SITE_LIBRARY: off | accounts | on. Any other value raises; never a silent default."""
    value = os.environ.get(FLAG, 'off').strip().lower()
    if value not in MODES:
        raise ValueError(f'{FLAG} must be one of {MODES}, not {value!r}')
    return value


def accounts() -> set[str]:
    listed = {a.strip() for a in os.environ.get(ACCOUNTS, '').split(',') if a.strip()}
    if not listed:
        raise ValueError(f'{FLAG}=accounts needs {ACCOUNTS}; none is listed')
    return listed


@dataclass
class Route:
    route: str
    reason: str
    prompt: str = ''
    palette: str | None = None
    palette_entry: dict = field(default_factory=dict)
    direction: str | None = None
    voice: str = ''
    contract: dict | None = None
    contract_fp: str | None = None
    contract_source: str | None = None
    canon_hash: str | None = None
    order: list[str] | None = None
    outline_titles: dict = field(default_factory=dict)
    title: str = ''
    year: str = ''
    # Warehouse 127: the business category, how it was found ('named' in the brief, or 'nearest' by similarity), and
    # the domain file it reads (None: no domain file for this category yet -- recorded, never a neighbour).
    category: str | None = None
    category_found: str | None = None
    domain: str | None = None
    domain_facts: list = field(default_factory=list)
    domain_words: list = field(default_factory=list)       # the trade's verified Hebrew words (warehouse 127)
    windows: tuple[str, ...] = ()          # the approved windows the library renders on this route
    # Warehouse 129/126: the page's script and the font pair locked into its contract (None off the route).
    script: str | None = None
    font_pair: str | None = None

    def to_dict(self) -> dict:
        return {'route': self.route, 'reason': self.reason, 'palette': self.palette, 'direction': self.direction,
                'contract': self.contract_fp, 'contract_source': self.contract_source, 'canon_hash': self.canon_hash,
                'order': self.order, 'outline_titles': self.outline_titles, 'category': self.category,
                'category_found': self.category_found, 'domain': self.domain, 'domain_facts': self.domain_facts,
                'windows': list(self.windows),
                'script': self.script, 'font_pair': self.font_pair,
                'fonts': (self.contract or {}).get('fonts')}


def _norm_title(title: str) -> str:
    return ' '.join(re.sub(r'["\'״׳:.]+$|^["\']+', '', (title or '').strip()).split())


def map_outline(sections: list[tuple[str, str]]) -> tuple[list[str] | None, dict, str | None]:
    """(section keys in the customer's order, {key: the customer's title}, the reason it cannot be mapped or None)."""
    if not sections:
        return None, {}, None
    keys, titles = [], {}
    for title, _ in sections:
        key = _TITLE_TO_KEY.get(_norm_title(title))
        if key is None:
            return None, {}, f'outline_unmapped: {title[:40]}'
        if key in keys:
            return None, {}, f'outline_repeated: {key}'
        keys.append(key)
        if key != 'hero':
            titles[key] = title.strip()
    if 'hero' in keys and keys[0] != 'hero':
        return None, {}, 'outline_hero_not_first'
    return keys, titles, None


def _account(request) -> str | None:
    value = (request or {}).get('user_id')
    return str(value) if value else None


def decide(prompt: str, request=None, *, plan_governed: bool = False, year: str | None = None) -> Route:
    """The route of one build, with its reason. Every precondition that fails names itself."""
    m = mode()
    if m == 'off':
        return Route(LEGACY, 'flag_off')
    if m == 'accounts' and _account(request) not in accounts():
        return Route(LEGACY, 'account_not_listed')
    from ..product_architect import content_only_approved
    if not content_only_approved(prompt):
        return Route(LEGACY, 'not_content_only')
    from ..page_locale import rtl_language
    lang = rtl_language(prompt)
    if lang != 'he':
        return Route(LEGACY, 'not_hebrew')
    if plan_governed:
        return Route(LEGACY, 'plan_governed')
    from ..uploaded_assets import _BINDING, _IMAGE_BINDING
    if _BINDING.search(prompt or ''):
        return Route(LEGACY, 'uploaded_logo')
    from ..section_library import RENDERED_WINDOWS
    from ..window_catalog import approved_in_prompt
    approved = approved_in_prompt(prompt)
    windows = [w for w in approved if w not in RENDERED_WINDOWS]       # approved, and not rendered by the library
    if windows:
        # A window the library does not render still goes to the old path -- by name: the owner's build bld_ab78f528
        # (2026-11-22) went legacy as 'approved_windows' and nobody could tell which window did it (cookie_banner and
        # question_widget are offered to every site). The library renders the cookie banner (DECISIONS.md 14 (b)).
        return Route(LEGACY, 'approved_windows: ' + ', '.join(windows))
    from . import facts as Fx
    request_text = Fx.request_text(prompt)
    places = [m_[5] for m_ in _IMAGE_BINDING.finditer(prompt or '')]
    bad = [p for p in places if p not in ('hero', 'story')] + [p for p in set(places) if places.count(p) > 1]
    if bad:
        return Route(LEGACY, f'image_place_{bad[0]}')
    from ..media_pipeline import _ICON_TERMS
    said = ' '.join(request_text.split()).lower()
    if any(t in said for t in _ICON_TERMS):
        return Route(LEGACY, 'icon_image')
    from ..a4 import pictures
    if pictures(prompt)['asked'] > 1:
        return Route(LEGACY, 'several_pictures')
    from .. import vertical_palettes as VP
    from ..section_library import DIRECTIONS
    named = VP.category_of(request_text)
    category = named or VP.nearest_category(request_text)[0]
    from ..domain_registry import domain_for, trade_words
    domain = domain_for(category)
    domain_kw = dict(category=category, category_found='named' if named else 'nearest',
                     domain=domain['slug'] if domain else None,
                     domain_facts=[f['fact'] for f in domain['mandatory_facts'] if f['when'] is None] if domain else [],
                     domain_words=trade_words(domain))
    palette, colours = VP.palette_for(category)
    if palette not in DIRECTIONS['palettes']:
        return Route(LEGACY, f'palette_not_in_library: {palette}')
    entry = DIRECTIONS['palettes'][palette]
    # Warehouse 126/129: the page's script follows the customer's language, and its fonts are a pair from the library
    # -- the category's art direction allows two pairs, the business (its name, or the name the customer quoted)
    # picks one -- locked into the design contract in place of the Design line's one font (Heebo by default).
    from .. import typography as T
    script = T.script_for_language(lang)
    sheet = Fx.fact_sheet(prompt)
    business = sheet.name or next(iter(sheet.name_candidates), None)
    pair = T.pair_for(script, category=category, tone=entry['direction'], business=business) if business else None
    from ..g_apple.contract import ContractError
    from .render import render_contract
    try:
        contract, source = render_contract(prompt, colours, fonts=T.contract_fonts(pair) if pair else None)
    except ContractError as exc:
        return Route(LEGACY, f'no_design_contract: {exc}'[:200])
    if sheet.problems:
        return Route(LEGACY, sheet.problems[0])
    if not sheet.name and not sheet.name_candidates:
        return Route(LEGACY, 'name_not_declared')          # the model never chooses the business name
    if pair is None:                                       # unreachable: a business key exists past the line above
        raise RuntimeError('the content route reached its end without a font pair')
    order, titles, why = map_outline(sheet.outline)
    if why:
        return Route(LEGACY, why)
    from .schema import offered_sections
    try:
        offered_sections(sheet, entry, order, titles)
    except ValueError as exc:
        return Route(LEGACY, f'outline_without_basis: {exc}'[:200])
    return Route(ROUTE, 'all preconditions hold', prompt=prompt, palette=palette, palette_entry=entry,
                 direction=entry['direction'], voice=entry['voice'], contract=contract,
                 contract_fp=contract['fingerprint'], contract_source=source, canon_hash=sheet.canon_hash,
                 order=order, outline_titles=titles, title=sheet.name or 'אתר תדמית',
                 year=year or str(datetime.date.today().year), windows=tuple(approved), script=script,
                 font_pair=pair['id'], **domain_kw)


def install(engine, *, prompt: str, gateway, request=None, plan_governed: bool = False, year: str | None = None) -> Route:
    """Decide the route and, on the library route, replace the engine's architect, generator and repairer and add the
    route's two executors. Installed right after components_factory(), before any install that wraps the architect.
    The decision is logged (SITE_ROUTE) and kept on the engine for the evidence on every build."""
    core = getattr(engine, 'core', engine)
    route = decide(prompt, request, plan_governed=plan_governed, year=year)
    if route.route != ROUTE:
        core.site_route = route
        _LOG.info('SITE_ROUTE route=%s reason=%s palette=%s contract=%s', route.route, route.reason, route.palette,
                  route.contract_fp)
        return route
    # Everything that can raise is resolved before the engine is touched (a bad OMNI_GATE_SITE_PARITY value raises
    # here, and the engine stays exactly as it was: never a half-installed route); then all parts are set together.
    from ..attempt_ledger import TaskTaggedGateway
    from ..behavior_acceptance import find_in_chain
    from ..preview_smoke import PreviewReadyExecutor
    from ..quality_gate import QualityAwareExecutor
    from ..skill_units import gate as G
    from ..verification_group import VerificationGroup
    from . import agents as A
    parity_mode = G.mode('SITE_PARITY')
    writer = A.ContentAgent(TaskTaggedGateway(gateway, 'codegen'))
    rewriter = A.ContentRepairAgent(TaskTaggedGateway(gateway, 'repair'))
    architect = A.ContentSpecArchitect(core, route)
    generator = A.ContentSiteGenerator(core, writer, rewriter)
    repairer = A.ContentSiteRepairer(core, rewriter)
    quality = find_in_chain(core.executor, QualityAwareExecutor)
    group = find_in_chain(quality._inner if quality is not None else core.executor, VerificationGroup)
    preview = find_in_chain(core.executor, PreviewReadyExecutor)
    recorder = A.ThresholdRecorder(group._threshold) if group is not None else None
    core.site_route = route
    _LOG.info('SITE_ROUTE route=%s reason=%s palette=%s contract=%s', route.route, route.reason, route.palette,
              route.contract_fp)
    core.site_report, core.site_feedback, core.site_sheet = {}, [], None
    core.architect, core.generator, core.repairer = architect, generator, repairer
    if preview is not None:
        # the owner, 2026-11-26: a page may now run past the 45,000 characters the preview smoke returns (raised item
        # maxima); the review stage reads it up to its last complete section, never a fact cut in half (served_cut)
        preview.trim_cut = True
    if group is not None:
        group._threshold = recorder
    if quality is not None:
        # inside the quality gate, around the group: a round turned into a pass still meets the quality assessment
        quality._inner = A.AdvisoryFilterExecutor(quality._inner, core, recorder)
        core.executor = A.SiteParityExecutor(core.executor, core, parity_mode)
    else:
        core.executor = A.SiteParityExecutor(A.AdvisoryFilterExecutor(core.executor, core, recorder), core,
                                             parity_mode)
    return route


def on_route(engine) -> bool:
    route = getattr(getattr(engine, 'core', engine), 'site_route', None)
    return isinstance(route, Route) and route.route == ROUTE


def report(engine) -> dict | None:
    """For the build evidence ('site_route'): the decision and, on the route, what it did."""
    core = getattr(engine, 'core', engine)
    route = getattr(core, 'site_route', None)
    if not isinstance(route, Route):
        return None
    out = route.to_dict()
    if route.route == ROUTE:
        from .render import RENDERER_VERSION
        repairer = getattr(core, 'repairer', None)
        out.update(renderer=RENDERER_VERSION, headings=f'the display face of font pair {route.font_pair} (warehouse 126)',
                   **{k: v for k, v in (getattr(core, 'site_report', None) or {}).items()},
                   library_feedback=list(getattr(core, 'site_feedback', None) or [])[:40],
                   repair_trace=list(getattr(repairer, 'trace', None) or [])[-20:])
    return out
