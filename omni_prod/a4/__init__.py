"""A4, the assets agent (plan part A section 4: "which assets, budget, placement"; the owner, 2026-11-16 stage D).

No model and no network. Before A4 the decisions about a page's images were scattered: an uploaded photo had the place
the customer chose, but a GENERATED image had no place at all -- the code model was told "use every one of them" and
chose where (generated_images.prompt_block), and nothing counted how heavy the images made the page together.

A4 makes ONE asset plan per build, from the images the worker already bound:

1. `plan(uploaded, generated)` -- every image gets exactly one place, by stated rules:
   - a customer's photo keeps the place the customer chose (hero / story / products / gallery);
   - a generated icon goes to the header (`icon`);
   - the first generated picture is the hero -- unless the customer's own photo already is, in which case the
     customer's photo keeps the hero and the generated picture goes to the gallery (said in the plan, never silent);
   - every further generated picture goes to the gallery.
   Two images claiming the hero, more than MAX_ASSETS images, or images heavier together than PAGE_IMAGE_BUDGET_BYTES
   raise AssetPlanError: the build stops before a line of code is paid for.
2. `rules(plan)` -- the plan as text for the generator: where each image goes, in the generator's own terms.
3. `check(repository, plan)` -- on the page as built: each image is where the plan put it. The check is a new gate
   (`A4`), so it enters at warn (gate.CALIBRATING): its findings go to the log and the build evidence, and it blocks
   only after it is calibrated on three builds.
4. `report(engine)` -- the plan and the last check, for the build evidence (`asset_plan`).

What A4 does NOT do yet: decide HOW MANY images to generate (capability_planner still does: one requirement), price
them, or choose between candidate images. Those need the planner to ask A4 before generation (the A4 -> A3 link).
"""
from __future__ import annotations

import logging
import re

GATE = 'A4'
ACCEPTANCE_ID = 'asset-plan'
PLACES = ('icon', 'hero', 'story', 'products', 'gallery')
MAX_ASSETS = 12                         # images on one page; past this the plan is refused, not trimmed
PAGE_IMAGE_BUDGET_BYTES = 1_500_000     # all images of the page together, as carried (web_rendition keeps each light)
_LOG = logging.getLogger(__name__)
_PLACE_EN = {'icon': 'in the header, next to the business name', 'hero': 'the first image of the page, in its top area',
             'story': 'inside the "our story" section', 'products': 'inside the products section',
             'gallery': 'inside the gallery section'}
_IMG = re.compile(r'<img\b[^>]*>', re.I | re.S)


class AssetPlanError(ValueError):
    """The images cannot be planned onto one page as they are. The build stops; nothing is dropped in silence."""


def _slot(img, source: str, place: str, why: str) -> dict:
    return {'place': place, 'source': source, 'index': img.index, 'marker': img.marker, 'alt': img.alt,
            'sha256': getattr(img, 'sha256', None), 'bytes': len(getattr(img, 'data', b'') or b''), 'why': why}


def plan(uploaded=(), generated=()) -> list[dict]:
    """The asset plan: one slot per image, in the order the page shows them (icon, hero, story, products, gallery)."""
    from ..generated_images import _kind
    slots: list[dict] = []
    for img in uploaded or ():
        place = getattr(img, 'place', None)
        if place not in PLACES or place == 'icon':
            raise AssetPlanError(f'uploaded image {img.index} has no known place: {place!r}')
        slots.append(_slot(img, 'upload', place, 'the place the customer chose'))
    heroes = [s for s in slots if s['place'] == 'hero']
    if len(heroes) > 1:
        raise AssetPlanError('two uploaded images claim the hero: ' + ', '.join(s['marker'] for s in heroes))
    hero_taken = bool(heroes)
    for img in generated or ():
        if _kind(getattr(img, 'purpose', '')) == 'icon':
            slots.append(_slot(img, 'generated', 'icon', 'a generated icon belongs in the header'))
        elif not hero_taken:
            hero_taken = True
            slots.append(_slot(img, 'generated', 'hero', 'the first generated picture is the main image'))
        else:
            slots.append(_slot(img, 'generated', 'gallery',
                               "the main image is already taken; a further picture goes to the gallery"))
    if len(slots) > MAX_ASSETS:
        raise AssetPlanError(f'{len(slots)} images for one page; at most {MAX_ASSETS}')
    total = sum(s['bytes'] for s in slots)
    if total > PAGE_IMAGE_BUDGET_BYTES:
        raise AssetPlanError(f'the images weigh {total:,} bytes together; a page carries at most '
                             f'{PAGE_IMAGE_BUDGET_BYTES:,}')
    slots.sort(key=lambda s: (PLACES.index(s['place']), s['source'] != 'upload', s['index']))
    return slots


def rules(slots: list[dict]) -> str:
    """The plan in the generator's words. '' when the page has no platform image."""
    if not slots:
        return ''
    lines = ['Asset plan (decided by 148AI; checked on the finished page). Each image has ONE place:']
    for s in slots:
        lines.append(f'- src="{s["marker"]}" ({s["source"]}): {_PLACE_EN[s["place"]]}.')
    if any(s['place'] == 'hero' for s in slots):
        lines.append('The main image comes before every other picture of the page (an icon in the header may come '
                     'first).')
    return '\n'.join(lines)


def _first_use(text: str, img) -> int:
    """The offset of the first <img> that shows this image, or -1."""
    hits = [m.start() for m in _IMG.finditer(text) if img.marker in m.group(0) or img.uri in m.group(0)]
    return hits[0] if hits else -1


def check(repository: dict, slots: list[dict], images: dict) -> list[dict]:
    """[{marker, place, state, why}] for every slot that is not where the plan put it. `images`: marker -> image."""
    from ..skill_units.gate import pages
    from ..uploaded_assets import place_state
    found = pages(repository)
    problems = []
    for s in slots:
        img = images[s['marker']]
        uses = [(path, _first_use(html, img)) for path, html in found]
        uses = [(path, at) for path, at in uses if at >= 0]
        if not uses:
            continue                       # "not on the page" is the image checks' own failure, said once there
        if s['place'] in ('story', 'products', 'gallery'):
            state = place_state(repository, type('Placed', (), {'place': s['place'], 'marker': img.marker,
                                                               'uri': img.uri})())
            if state != 'ok':
                problems.append({'marker': s['marker'], 'place': s['place'], 'state': state,
                                 'why': f'it is not inside the {s["place"]} section'})
        elif s['place'] == 'hero':
            path, at = uses[0]
            html = dict(found)[path]
            earlier = [o['marker'] for o in slots if o is not s and o['place'] != 'icon'
                       and 0 <= _first_use(html, images[o['marker']]) < at]
            if earlier:
                problems.append({'marker': s['marker'], 'place': 'hero', 'state': 'not_first',
                                 'why': 'another picture comes before the main image: ' + ', '.join(earlier)})
    return problems


class AssetPlanExecutor:
    """warn: the findings are recorded and the build goes on. block: each finding is a failed acceptance check."""

    def __init__(self, inner, slots: list[dict], images: dict, mode: str):
        self._inner, self.slots, self.images, self.mode, self.last_check = inner, slots, images, mode, None

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from ..autonomous_core import AcceptanceFailure, ExecutionReport
        report = self._inner.execute(repository=repository, spec=spec)
        problems = check(repository, self.slots, self.images)
        self.last_check = {'status': 'fail' if problems else 'pass', 'mode': self.mode, 'problems': problems}
        if not problems:
            return report
        _LOG.warning('A4_PLACEMENT mode=%s problems=%s', self.mode, [(p['marker'], p['state']) for p in problems])
        if self.mode != 'block':
            return report
        failures = tuple(AcceptanceFailure(ACCEPTANCE_ID, (
            f'Image {p["marker"]} belongs {_PLACE_EN[p["place"]]}, and {p["why"]}. Move its <img> there; do not '
            'remove or replace the image.')) for p in problems)
        return ExecutionReport(False, tuple(report.failures) + failures, report.build_log)


def install(engine, *, prompt: str) -> str:
    """Plan the images the worker bound (raising on a plan that cannot be), keep the plan on the engine, install the
    placement check in its gate mode, and return the prompt with the plan's rules. Unchanged when there is no image.
    Called after the generated images and the customer's photos are installed."""
    from ..skill_units import gate as G
    core = getattr(engine, 'core', engine)
    uploaded = getattr(core, 'uploaded_images', None)
    generated = getattr(core, 'generated_images', None)
    uploaded = uploaded if isinstance(uploaded, (list, tuple)) else ()
    generated = generated if isinstance(generated, (list, tuple)) else ()
    slots = plan(uploaded, generated)
    mode = G.mode(GATE)
    modes = dict(getattr(core, 'gate_modes', None) or {})
    modes[GATE] = mode
    core.gate_modes = modes
    core.asset_plan = slots
    _LOG.info('A4_PLAN assets=%d mode=%s places=%s', len(slots), mode, [(s['marker'], s['place']) for s in slots])
    if not slots:
        return prompt
    if mode != 'off':
        images = {img.marker: img for img in (*uploaded, *generated)}
        core.executor = core.asset_plan_check = AssetPlanExecutor(core.executor, slots, images, mode)
    else:
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s): this build is NOT checked by %s', GATE, GATE, GATE)
    return prompt + '\n\n' + rules(slots)


def report(engine) -> dict:
    """For the build evidence: the plan (no bytes) and the last placement check."""
    core = getattr(engine, 'core', engine)
    slots = getattr(core, 'asset_plan', None)
    checker = getattr(core, 'asset_plan_check', None)
    modes = getattr(core, 'gate_modes', None)
    return {'agent': 'A4', 'mode': modes.get(GATE) if isinstance(modes, dict) else None,
            'plan': slots if isinstance(slots, list) else None,
            'check': checker.last_check if isinstance(checker, AssetPlanExecutor) else None}
