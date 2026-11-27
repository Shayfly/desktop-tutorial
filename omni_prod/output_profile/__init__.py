"""Output profiles and the A0 router (warehouse item 69, released by the owner 2026-11-15).

One pipeline, one profile per output type (docs/OUTPUT_PLATFORM_PLAN_HE.md, part A section 2). A profile DECLARES
what the pipeline builds for a type: the builder, the checks every build of that type must pass, the brief fields
it needs and the ones it must not carry, and the cost ceiling and repair limit the engine enforces today. A type
with no profile is refused out loud on the first turn, in the customer's words ("not yet; this, yes"), and is never
built halfway: no default chosen, no question asked, no brief saved, no model called.

Truth, not marketing. The profiles here are exactly the families `intake.families.EXECUTABLE` names, the engine's
verified execution path. `check_truth` runs at import: a profile for a type the engine cannot build, or an executable
type without a profile, stops the import. Every number is read from the module that enforces it (`pricing`), so it
cannot drift from the engine. A family the registry does not know at all raises `ProfileMissing`: an unknown value
is an error, never a quiet default (CLAUDE.md section 3).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..intake import artifact_fields as AF
from ..intake.families import EXECUTABLE, FAMILIES
from ..planning.feasibility import CORE_CHECKS
from .. import pricing
from . import page_types as PT

BUILDER_WEB_V1 = 'web_graph_v1'        # planning.architect.web_graph + the autonomous core: the one engine that exists


class ProfileMissing(LookupError):
    """A family the registry knows neither as a profile nor as an unsupported type."""


@dataclass(frozen=True)
class OutputProfile:
    type: str
    builder: str
    required_brief_fields: tuple[str, ...]
    forbidden_brief_fields: tuple[str, ...]
    asset_kinds: tuple[str, ...]
    gates: tuple[str, ...]                 # truth-matrix capability names feasibility requires of every build
    acceptance_checks: tuple[str, ...]     # omni_prod modules that judge a finished build
    cost_ceiling_usd: Decimal              # the per-build model-spend cap the engine enforces today (LIGHT class)
    repair_rounds_max: int                 # pricing.DEFAULT_REPAIR_ROUNDS, what the engine allows today
    human_review: bool                     # no human reviewer exists in the pipeline today
    page_types: tuple[str, ...] = ()       # warehouse 123: the kinds of page this output type is (page_types.py); () = not a page

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d['cost_ceiling_usd'] = str(self.cost_ceiling_usd)
        return d


@dataclass(frozen=True)
class Unsupported:
    type: str
    reason: str          # for the record, in English
    not_yet_he: str      # the customer's sentence: what is not yet possible, what is, and how to continue
    not_yet_en: str


@dataclass(frozen=True)
class Routing:
    family: str
    profile: OutputProfile | None
    unsupported: Unsupported | None

    @property
    def supported(self) -> bool:
        return self.profile is not None

    def not_yet(self, lang: str) -> str:
        if self.unsupported is None:
            raise ValueError(f'{self.family} is supported; there is no refusal to show')
        return self.unsupported.not_yet_he if lang == 'he' else self.unsupported.not_yet_en


def _field_names(kind: str) -> tuple[str, ...]:
    return tuple(f.name for f in AF.fields_for(kind))


PAGE_FAMILIES = ('website',)       # the output types that are pages; a web_app is a tool, with no page type


def _profile(kind: str) -> OutputProfile:
    others = {f for other in EXECUTABLE if other != kind for f in _field_names(other)}
    required = _field_names(kind)
    return OutputProfile(
        type=kind, builder=BUILDER_WEB_V1,
        required_brief_fields=required,
        forbidden_brief_fields=tuple(sorted(others - set(required))),
        asset_kinds=('logo', 'image'),
        gates=tuple(CORE_CHECKS),
        acceptance_checks=('omni_prod.behavior_acceptance', 'omni_prod.browser_probe', 'omni_prod.visual_qa'),
        cost_ceiling_usd=pricing.m5_class_llm_cap(pricing.CostClass.LIGHT),
        repair_rounds_max=pricing.DEFAULT_REPAIR_ROUNDS,
        human_review=False,
        page_types=PT.TYPES if kind in PAGE_FAMILIES else (),
    )


_EXIT_HE = ' כתבו במשפט מה האתר או האפליקציה צריכים לעשות, ונמשיך משם. ההודעה שלכם נשמרה בשיחה.'
_EXIT_EN = ' Tell me in a sentence what the site or app should do, and we continue from there. Your message is kept in this conversation.'
_WEB_HE = 'אתר או אפליקציה שנפתחים בטלפון ובמחשב, בלי להתקין כלום'
_WEB_EN = 'a site or an app that opens on the phone and the computer, nothing to install'

_UNSUPPORTED: dict[str, tuple[str, str, str]] = {
    # family: (reason for the record, Hebrew sentence, English sentence). Structure: not yet / yes / how to continue.
    'game': ('no runtime or load gate (G8) and no game builder; P3 of the output-platform plan',
             f'משחק עוד לא. כן: {_WEB_HE}.',
             f'A game, not yet. Yes: {_WEB_EN}.'),
    'media': ('no media fidelity gate (G7), no audio/video rights check (A7); P4-P5 of the plan',
              f'שיר, סרטון או מוזיקה עוד לא. כן: {_WEB_HE}, ותמונות וסרטונים שיש לכם אפשר להעלות לתוכם.',
              f'A song, a video or music, not yet. Yes: {_WEB_EN}, and photos or videos you already have can go into it.'),
    'mobile_app': ('no native build, signing or store submission path; out of scope (section 13)',
                   f'אפליקציה להורדה מחנות האפליקציות (אייפון או אנדרואיד) עוד לא. כן: אפליקציה שנפתחת בטלפון בלי להתקין כלום, ואפשר להוסיף אותה למסך הבית.',
                   f'An app to download from the app store (iPhone or Android), not yet. Yes: an app that opens on the phone with nothing to install, and can be added to the home screen.'),
    'ai_agent': ('no agent runtime, knowledge sources or conversation channel integration',
                 f'בוט או עוזר שמשוחח עם הלקוחות שלכם עוד לא. כן: {_WEB_HE}, עם טופס פנייה, טלפון ווואטסאפ.',
                 f'A bot or assistant that chats with your customers, not yet. Yes: {_WEB_EN}, with a contact form, phone and WhatsApp.'),
    'automation': ('no scheduler, trigger or step runner for background workflows',
                   f'תהליך שרץ לבד ברקע עוד לא. כן: אפליקציה שבה אתם או הצוות מבצעים את הפעולה בלחיצה.',
                   f'A process that runs by itself in the background, not yet. Yes: an app where you or your team do the action with one click.'),
    'api_integration': ('the integration agent is not executable; credentials are never taken in chat',
                        f'חיבור למערכת חיצונית עוד לא. כן: {_WEB_HE}, שעובדים בעצמם בלי החיבור.',
                        f'A connection to an outside system, not yet. Yes: {_WEB_EN}, working on its own without the connection.'),
    '3d_experience': ('no 3D runtime, model pipeline or performance gate',
                      f'תלת-ממד עוד לא. כן: {_WEB_HE}, עם תמונות וסרטון.',
                      f'3D, not yet. Yes: {_WEB_EN}, with photos and a video.'),
}

PROFILES: dict[str, OutputProfile] = {kind: _profile(kind) for kind in sorted(EXECUTABLE)}
UNSUPPORTED: dict[str, Unsupported] = {
    fam: Unsupported(fam, reason, he + _EXIT_HE, en + _EXIT_EN) for fam, (reason, he, en) in _UNSUPPORTED.items()}


def check_truth(profiles, unsupported, executable, families) -> None:
    """The registry tells the truth about the engine, or the module does not load."""
    if set(profiles) != set(executable):
        raise RuntimeError(f'output profiles {sorted(profiles)} are not the executable families {sorted(executable)}: '
                           'a profile is a promise the engine must keep')
    if set(profiles) & set(unsupported):
        raise RuntimeError(f'declared both supported and unsupported: {sorted(set(profiles) & set(unsupported))}')
    if set(profiles) | set(unsupported) != set(families):
        raise RuntimeError(f'every family needs a profile or an unsupported entry; missing '
                           f'{sorted(set(families) - set(profiles) - set(unsupported))}, '
                           f'unknown {sorted((set(profiles) | set(unsupported)) - set(families))}')


check_truth(PROFILES, UNSUPPORTED, EXECUTABLE, FAMILIES)
if not set(PAGE_FAMILIES) <= set(PROFILES):
    raise RuntimeError(f'page families {PAGE_FAMILIES} have no output profile')


def profile_for(family: str) -> OutputProfile | None:
    return PROFILES.get(family)


def route(family: str) -> Routing:
    """A0: the routing of one family. Supported -> its profile; declared unsupported -> the customer's sentence;
    anything else raises, because a type the pipeline does not know must never be defaulted."""
    if family in PROFILES:
        return Routing(family, PROFILES[family], None)
    if family in UNSUPPORTED:
        return Routing(family, None, UNSUPPORTED[family])
    raise ProfileMissing(f'no output profile and no unsupported entry for product family {family!r}')


def detect_page_type(family: str, prompt: str) -> PT.Detection:
    """Warehouse 123: the page type of an approved prompt, for an output family. Only a page family has one: a web_app, or
    a family declared unsupported, is `not_a_page`. An unknown family raises ProfileMissing, never a default. The stable
    key is `.page_type` (None when the customer's words name none or two equally; `.found` says which)."""
    routing = route(family)
    if routing.profile is None or not routing.profile.page_types:
        return PT.Detection(None, 'not_a_page')
    return PT.detect(prompt)
