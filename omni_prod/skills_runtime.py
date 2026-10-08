"""Skills that actually run in the web build path (Agent OS spec §10, 2026-10-08).

`skills_registry.py` lists 104 capability skills, none of which shaped what the
agents wrote. The founder's first real product (task list, 2026-10-08)
showed what was missing: a due date in year 2356 accepted, errors in alert(),
an active filter that silently hid new rows, apostrophes shown as "&#x27;",
a "done" button on finished tasks, and login requirements added although the
request said "without login".

Each skill here follows the shared contract: purpose and boundaries, which
agent roles use it, guidance injected into those agents' prompts, a
checklist the QA Verifier reviews against, and deterministic static checks
over the generated repository. Skills have no side effects of their own (no
provider calls, no writes); the QA Verifier that uses them does, under the
build's budget. A build records which skills (key@version) were applied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable

ROLE_ARCHITECT = 'architect'
ROLE_GENERATOR = 'generator'
ROLE_REPAIR = 'repair'
ROLE_EVOLUTION = 'evolution'
ROLE_REVIEWER = 'reviewer'


@dataclass(frozen=True)
class StaticFinding:
    skill: str
    severity: str  # 'blocking' | 'advisory'
    file: str
    problem: str
    fix: str

    def to_dict(self) -> dict:
        return {'skill': self.skill, 'severity': self.severity, 'file': self.file,
                'problem': self.problem, 'fix': self.fix, 'source': 'static'}


@dataclass(frozen=True)
class Skill:
    key: str
    version: str
    purpose: str
    boundaries: str
    roles: tuple[str, ...]
    guidance: str
    checklist: tuple[str, ...]
    static_checks: tuple[Callable[[dict, dict], list[StaticFinding]], ...] = ()
    # Contract fields (§10) that are the same for every skill in this pack.
    side_effects: str = 'none (pure guidance and repository inspection)'
    budget: str = 'no direct spend; reviewer calls are charged to the build budget'
    failure_modes: tuple[str, ...] = field(default_factory=lambda: (
        'blocking finding -> repairable REVIEW failure', 'advisory finding -> recorded in evidence only'))

    def ref(self) -> dict:
        return {'key': self.key, 'version': self.version}


def _text_files(repository: dict) -> dict[str, str]:
    return {p: c for p, c in repository.items() if isinstance(c, str)
            and p.lower().endswith(('.py', '.html', '.js', '.mjs', '.css', '.htm'))
            and not p.startswith(('tests/', 'test_')) and '/test_' not in p}


def _hebrew(context: dict) -> bool:
    return bool(re.search(r'[֐-׿]', context.get('request', '') or ''))


# ---------------------------------------------------------------- static checks

def _no_browser_dialogs(repository: dict, context: dict) -> list[StaticFinding]:
    out = []
    for path, text in _text_files(repository).items():
        if re.search(r'(?<![\w.])(alert|confirm|prompt)\s*\(', text) or re.search(r'window\.(alert|confirm|prompt)\s*\(', text):
            out.append(StaticFinding('skill.form_validation', 'blocking', path,
                                     'uses a browser dialog (alert/confirm/prompt) to talk to the user',
                                     'show the message inside the page next to the field or in a status area'))
    return out


def _escape_once(repository: dict, context: dict) -> list[StaticFinding]:
    out = []
    for path, text in _text_files(repository).items():
        if path.endswith('.py') and re.search(r'html\.escape\(', text) and re.search(r'INSERT\s+INTO', text, re.I):
            out.append(StaticFinding('skill.text_locale', 'blocking', path,
                                     'escapes text before storing it (html.escape near INSERT), so quotes show as &#x27;',
                                     'store the raw text; escape only when rendering (textContent in the page)'))
    return out


def _rtl_for_hebrew(repository: dict, context: dict) -> list[StaticFinding]:
    if not _hebrew(context):
        return []
    pages = [c for p, c in _text_files(repository).items() if '<html' in c.lower()]
    if pages and not any(re.search(r'dir\s*=\s*["\']rtl', c, re.I) for c in pages):
        return [StaticFinding('skill.text_locale', 'blocking', '(html page)',
                              'Hebrew product without dir="rtl" on the page',
                              'set <html lang="he" dir="rtl">')]
    return []


def _innerhtml_interpolation(repository: dict, context: dict) -> list[StaticFinding]:
    out = []
    for path, text in _text_files(repository).items():
        if re.search(r'\.innerHTML\s*[+]?=\s*`[^`]*\$\{', text):
            out.append(StaticFinding('skill.text_locale', 'advisory', path,
                                     'builds HTML from data with innerHTML and ${...}',
                                     'create elements and set textContent for user data'))
    return out


# ---------------------------------------------------------------- the skill pack

REQUEST_FIDELITY = Skill(
    key='skill.request_fidelity', version='1',
    purpose='What the user stated explicitly decides scope; defaults never override it.',
    boundaries='Scope and requirements only; does not choose libraries or layout.',
    roles=(ROLE_ARCHITECT, ROLE_GENERATOR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Request fidelity: an explicit statement in the request overrides every platform default. If the request says '
        'there is no login / no users ("בלי התחברות"), do not add sign-up, login, sessions, roles or permissions anywhere '
        '(requirements, acceptance, code, tests, web_saas_acceptance kinds). Do not add features the user did not ask for, '
        'except the quality basics below. Keep the request language for every user-facing text.'),
    checklist=('Nothing the user explicitly excluded exists in the product (e.g. login when "without login").',
               'Every feature the user listed is reachable from the main page.'),
)

FORM_VALIDATION = Skill(
    key='skill.form_validation', version='1',
    purpose='Every input is checked on the server and the user sees a clear message next to the problem.',
    boundaries='Forms and API input; not business rules unique to the product.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Forms: validate every field on the server and answer HTTP 400 with JSON {"error": "<message in the request '
        'language>", "field": "<name>"}; also validate in the page before sending. Required fields cannot be empty or only '
        'spaces; limit text length (e.g. 200). Dates must be real calendar dates in a sensible window: a deadline or '
        'appointment is not in the past and not more than 5 years ahead unless the request says otherwise; reject years '
        'like 0002 or 2356. Show the error inside the page next to the field or in a status line, never with alert(), '
        'confirm() or prompt(), and keep what the user typed. Add a test for at least one invalid input per form.'),
    checklist=('Invalid input (empty, too long, impossible date) is refused by the server with 400 and a readable message.',
               'Errors appear inside the page, never in a browser dialog.',
               'The form keeps the typed values after an error.'),
    static_checks=(_no_browser_dialogs,),
)

UI_STATES = Skill(
    key='skill.ui_states', version='1',
    purpose='The page never leaves the user guessing: empty, loading, error, filtered and done states are visible.',
    boundaries='Presentation of state; not visual branding.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'UI states: show an empty-state sentence when a list has no rows; show a short status after every action '
        '(added, deleted, error). When a filter or search is active, show it above the list ("מוצג סינון לפי: X") with a '
        'clear button, and after adding an item make sure the user sees it (clear the filter or say it is hidden by the '
        'filter). Offer only actions that make sense for the row state (no "mark done" on a done item; offer "undo" or '
        'nothing). Prevent double submission (disable the button while a request is running).'),
    checklist=('An empty list shows an explanatory sentence.',
               'An active filter is visible and can be cleared; a newly added item is not silently hidden.',
               'Row actions match the row state; buttons are disabled while a request runs.'),
)

TEXT_LOCALE = Skill(
    key='skill.text_locale', version='1',
    purpose='Text is stored once, escaped once, and shown in the user\'s language and formats.',
    boundaries='Encoding, direction, dates/numbers formatting.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Text and locale: store user text exactly as typed (parameterised SQL) and escape it only when rendering - set '
        'textContent / create elements, never html.escape before saving and never innerHTML with user data. For a Hebrew '
        'request use <html lang="he" dir="rtl"> and Hebrew labels; store dates as ISO (YYYY-MM-DD) and show them as '
        'DD/MM/YYYY; times as HH:MM 24h.'),
    checklist=('A name with quotes or <b> is shown exactly as typed, not as &#x27; or bold.',
               'Hebrew pages are RTL; dates show as DD/MM/YYYY.'),
    static_checks=(_escape_once, _rtl_for_hebrew, _innerhtml_interpolation),
)

DATA_INTEGRITY = Skill(
    key='skill.data_integrity', version='1',
    purpose='The server is the authority on business rules; data stays consistent.',
    boundaries='Server-side rules and storage; not UI.',
    roles=(ROLE_ARCHITECT, ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Data integrity: enforce business rules on the server (e.g. no two bookings in the same slot, no duplicate names '
        'when the request implies uniqueness) and answer 409 with a readable message on a conflict; acting on a missing '
        'id answers 404. Data lives under DATA_DIR. The architect turns each such rule into an acceptance criterion.'),
    checklist=('Rules implied by the request (uniqueness, no double booking, valid ranges) are enforced by the server.',
               'Missing ids give 404, conflicts 409, with a readable message.'),
)

WEB_SKILLS: tuple[Skill, ...] = (REQUEST_FIDELITY, FORM_VALIDATION, UI_STATES, TEXT_LOCALE, DATA_INTEGRITY)


def skills_for(role: str, skills: tuple[Skill, ...] = WEB_SKILLS) -> tuple[Skill, ...]:
    return tuple(s for s in skills if role in s.roles)


def guidance_for(role: str) -> str:
    chosen = skills_for(role)
    if not chosen:
        return ''
    return ' Product quality skills (' + ', '.join(f'{s.key}@{s.version}' for s in chosen) + '): ' + \
        ' '.join(s.guidance for s in chosen)


def checklist_for_review() -> list[dict]:
    return [{'skill': s.key, 'checks': list(s.checklist)} for s in skills_for(ROLE_REVIEWER)]


def static_findings(repository: dict, context: dict | None = None) -> list[StaticFinding]:
    context = context or {}
    out: list[StaticFinding] = []
    for skill in WEB_SKILLS:
        for check in skill.static_checks:
            out.extend(check(repository, context))
    return out


def applied_skills() -> list[dict]:
    return [s.ref() for s in WEB_SKILLS]
