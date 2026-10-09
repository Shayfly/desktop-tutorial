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


def _styled_page(repository: dict, context: dict) -> list[StaticFinding]:
    """Founder 2026-10-09: "no colour, not a real site that looks good". The
    page must carry a real design system, not the browser's default look."""
    files = _text_files(repository)
    pages = [c for c in files.values() if '<html' in c.lower()]
    if not pages:
        return []
    css = ' '.join(re.findall(r'<style[^>]*>(.*?)</style>', ' '.join(pages), re.S | re.I))
    css += ' '.join(c for p, c in files.items() if p.lower().endswith('.css'))
    declarations = len(re.findall(r'[a-z-]+\s*:\s*[^;{}]+;', css))
    problems = []
    if declarations < 40:
        problems.append(f'only {declarations} CSS declarations: the page shows the browser default look')
    if '--' not in css:
        problems.append('no colour/spacing tokens (CSS custom properties)')
    if '@media' not in css:
        problems.append('no responsive rule (@media) for phones')
    if not problems:
        return []
    return [StaticFinding('skill.visual_design', 'blocking', '(html page)', '; '.join(problems),
                          'add the design system described in skill.visual_design: tokens on :root, header, cards, '
                          'styled form controls and buttons, table styling, status badges, and a phone layout')]


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
        'nothing). Prevent double submission (disable the button while a request is running). A status/banner element '
        'that is hidden after a timeout must be made visible again on every later message (set hidden=false or '
        'style.display="" each time and clear the previous timer) - a message that shows once and never again is a bug.'),
    checklist=('An empty list shows an explanatory sentence.',
               'Every action shows its status message, also the second and third time (no banner left hidden).',
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

VISUAL_DESIGN = Skill(
    key='skill.visual_design', version='1',
    purpose='The product looks like a real, modern site: coherent colours, typography, spacing and components.',
    boundaries='Visual presentation only; never removes or hides functionality, never loads code from other sites.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Visual design: ship a complete, polished design system in the page (one <style> block or a CSS file served by '
        'the app), never the browser default look. Define tokens on :root: a primary colour chosen to fit the product '
        'domain (e.g. teal for health, deep blue for finance, warm orange for food, green for sport), a darker hover shade, '
        'neutral background (#f6f7f9-like), white surfaces, text and muted-text colours, success/warning/danger colours, '
        'radius 10-14px, a soft shadow, and a spacing scale. Typography: font-family "Assistant", "Rubik", system-ui, '
        'sans-serif (Hebrew-friendly; you may add <link> to Google Fonts for Assistant/Rubik), base 16px, clear heading '
        'sizes. Layout: a header bar with the product name and a one-line description; content centred with max-width '
        'about 1100px; each form and list inside a card (surface, radius, shadow, padding 20-24px) with a card title. '
        'Forms: labels above inputs, inputs full-width with padding 10-12px, 1px border, radius, visible focus ring in '
        'the primary colour; group fields in a responsive grid. Buttons: primary (filled primary colour, white text), '
        'secondary (outline) and danger (red) styles with hover, focus-visible and disabled states; never unstyled. '
        'Tables: full width, header row with tinted background, zebra rows, comfortable padding, numbers aligned, and on '
        'phones the table scrolls horizontally inside its card. Status values as coloured pill badges (e.g. open/done, '
        'late). Messages: success/error banners with the semantic colours, not plain text. Responsive: one column under '
        '640px (@media), touch-friendly sizes. Accessibility: contrast at least 4.5:1, focus outlines kept. For RTL, use '
        'logical properties (margin-inline-start, padding-inline) so the layout mirrors correctly.'),
    checklist=('The page has a coherent colour palette, header, cards, styled inputs/buttons/tables and status badges.',
               'It works on a phone width (single column, table scrolls), with visible focus and readable contrast.'),
    static_checks=(_styled_page,),
)

WEB_SKILLS: tuple[Skill, ...] = (REQUEST_FIDELITY, FORM_VALIDATION, UI_STATES, TEXT_LOCALE, DATA_INTEGRITY, VISUAL_DESIGN)


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
