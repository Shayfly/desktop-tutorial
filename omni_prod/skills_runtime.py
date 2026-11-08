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


_CONVERSION = re.compile(r'(?<![\w.])(int|float)\(')
_INPUT_HINTS = ('json', 'payload', 'body', 'request.get_json', '["', "['")


def _call_argument(line: str, open_paren: int) -> str:
    """The text between the conversion's parenthesis and its matching close (same line)."""
    depth = 0
    for i in range(open_paren, len(line)):
        if line[i] == '(':
            depth += 1
        elif line[i] == ')':
            depth -= 1
            if depth == 0:
                return line[open_paren + 1:i]
    return line[open_paren + 1:]


def _unguarded_int_conversion(repository: dict, context: dict) -> list[StaticFinding]:
    """Run 39313029465 (2026-10-19): POST /api/matches did int(score), so 2.9 and true were accepted as other scores.
    An int()/float() of request input with no try in the 15 lines up to it and no isinstance( before it in them."""
    out = []
    for path, text in _text_files(repository).items():
        if not path.endswith('.py'):
            continue
        lines = text.splitlines()
        for n, line in enumerate(lines):
            for m in _CONVERSION.finditer(line):
                arg = _call_argument(line, m.end() - 1)
                if not any(h in arg for h in _INPUT_HINTS):
                    continue
                window = lines[max(0, n - 14):n] + [line[:m.start()]]
                if any(re.search(r'^\s*try\s*:', w) for w in window) or any('isinstance(' in w for w in window):
                    continue
                out.append(StaticFinding('skill.data_integrity', 'blocking', f'{path}:{n + 1}',
                                         f'{m.group(1)}() of request input without a type check: {line.strip()[:120]}',
                                         'validate type before converting; return 400 on a bad value'))
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


_CSS_COMMENT = re.compile(r'/\*.*?\*/', re.S)
_CSS_URL = re.compile(r'url\([^)]*\)', re.I)
_CSS_BLOCK = re.compile(r'\{([^{}]*)\}')                 # innermost blocks: rules, also inside @media
_CSS_DECL = re.compile(r'^\s*-{0,2}[A-Za-z][\w-]*\s*:\s*\S')


def css_declaration_count(css: str) -> int:
    """Declarations in rule blocks, the last one of a block included whether or not it ends with ';'.

    Paid run 39377332673 (2026-10-20): the old count matched only `prop: value;`, so in minified CSS
    (`a{color:red}`) the last declaration of every block was dropped -- 10 of 13 on the build's own CSS -- and
    the page was reported as "only 22-35 CSS declarations". url(...) contents (data: URIs carry ';') and comments
    are removed first; a selector like `a:hover` is outside the braces and never counted."""
    css = _CSS_URL.sub('url()', _CSS_COMMENT.sub('', css))
    return sum(1 for block in _CSS_BLOCK.findall(css) for part in block.split(';') if _CSS_DECL.match(part))


def _styled_page(repository: dict, context: dict) -> list[StaticFinding]:
    """Founder 2026-10-09: "no colour, not a real site that looks good". The
    page must carry a real design system, not the browser's default look."""
    files = _text_files(repository)
    pages = [c for c in files.values() if '<html' in c.lower()]
    if not pages:
        return []
    css = ' '.join(re.findall(r'<style[^>]*>(.*?)</style>', ' '.join(pages), re.S | re.I))
    css += ' '.join(c for p, c in files.items() if p.lower().endswith('.css'))
    declarations = css_declaration_count(css)
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
        'id answers 404. Data lives under DATA_DIR. The architect turns each such rule into an acceptance criterion. '
        # T8 (founder 2026-10-21): a resource that can be booked for a time range.
        'ONLY when the product books a resource for a time range (a room, a slot, a class, any resource with capacity) -- skip this for every other product: the overlap rule lives IN THE SERVER, inside '
        'one write transaction, never only in the page. With SQLite (no SELECT ... FOR UPDATE) the equivalent is: '
        'open the connection with isolation_level=None, run BEGIN IMMEDIATE (takes the write lock before reading), '
        'SELECT the resource row, then SELECT any booking of that resource with start < :new_end AND end > :new_start '
        '(on an edit also AND id != :id), and only if none exists INSERT/UPDATE, then COMMIT; on a conflict ROLLBACK '
        'and answer 409 with a readable message. Add a BEFORE INSERT and a BEFORE UPDATE trigger that RAISE(ABORT) on '
        'the same overlap, so the database itself refuses it. Serve with http.server.ThreadingHTTPServer and one '
        'sqlite3 connection per request (timeout=10). Store start and end as UTC ISO-8601 ending in Z; the form gives '
        'local Asia/Jerusalem date and time: convert with zoneinfo.ZoneInfo("Asia/Jerusalem") (daylight time included) '
        'and show every time back in Asia/Jerusalem as DD/MM/YYYY HH:MM. Return start_utc/end_utc (Z) and '
        'start_local/end_local (with the +02:00/+03:00 offset) in the JSON. The architect adds to the acceptance plan: '
        'a step with "concurrent": 2 that POSTs the same booking twice at once and expects exactly one 201 and one 409 '
        '("expect_status": 201, "expect_conflict_status": 409), an edit (PUT/PATCH) that moves a booking onto another '
        'one and expects 409, and a create whose JSON answer has the exact expected start_utc. '
        # Run 39313029465 (2026-10-19): int(score) turned 2.9 into 2 and true into 1.
        'Numeric input contract: every numeric field that comes from the request is converted with a guard: check '
        'the type first (isinstance(v, bool) is NOT a number: true/false are refused; for an integer field accept an int '
        'or a string of digits only, so "2.9" or 2.9 answers 400; for a decimal field "2.9" becomes 2.9), and a value '
        'that cannot be converted answers 400 with a readable message, never 500 and never a different number.'),
    checklist=('Rules implied by the request (uniqueness, no double booking, valid ranges) are enforced by the server.',
               'Missing ids give 404, conflicts 409, with a readable message.',
               'Bookings: two simultaneous requests for one slot -> exactly one accepted (BEGIN IMMEDIATE + trigger); '
               'an edit onto another booking -> 409; times stored UTC (Z), shown Asia/Jerusalem.',
               'Every numeric field from the request is type-checked before int()/float(); a bad value answers 400, '
               'never 500 and never a silently different number.'),
    static_checks=(_unguarded_int_conversion,),
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


# CEO 2026-11-08 ("skills precise at world-class programmer level, really tied to what each model does"): the pack
# above is product quality only. Founder build bld_ca727ba7 showed what the stations themselves lacked: a chained
# acceptance plan whose first capture failed took three checks with it, the repair answer explained instead of
# patching, and the weekly view was an unfiltered list. These skills describe HOW each station works.

ACCEPTANCE_PLAN = Skill(
    key='skill.acceptance_plan', version='1',
    purpose='The web_saas_acceptance plan proves the approved criteria against the real app, step by step, without '
            'false failures.',
    boundaries='The plan in .omni/project.json; not product code.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION),
    guidance=(
        'Acceptance plan (how a senior QA engineer writes it): each step is one HTTP request whose expectation is '
        'derived from the code you wrote, never guessed. Order steps as a story: read -> create -> read back -> '
        'update -> delete -> confirm gone. Prefer data the plan creates itself over seed rows: create the record, '
        'capture its id from THAT response ("capture": {"item_id": "id"}), then use ${item_id}. When you capture from a '
        'list, the response must be a JSON array or an object holding one, and the path must exist in it ("[0].id" for '
        'a top-level array, "items[0].id" for {"items": [...]}); a capture that does not resolve fails every later step '
        'that uses the variable. Assert what the criterion is about (status plus one or two expect_json_contains keys '
        'whose values you control), not incidental fields such as generated timestamps. Dates: ${today} or '
        '${date_plus_N}, never a fixed calendar date. Every acceptance id appears on at least one step of a kind that '
        'really exercises it; before answering, walk the plan once against your own handlers and fix any step that '
        'your code would answer differently.'),
    checklist=('Every capture path resolves in the response the step receives.',
               'Each acceptance id is covered by a step that exercises it end-to-end.'),
)

TEST_DESIGN = Skill(
    key='skill.test_design', version='1',
    purpose='The repository tests prove the acceptance criteria and fail for the right reason.',
    boundaries='tests/ only; the sandbox rules (stdlib + pytest, loopback, 180 s) stay as stated.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION),
    guidance=(
        'Tests: one test function per acceptance criterion, named after it (test_a2_register_for_class), plus one '
        'invalid-input test per form. Each test sets DATA_DIR to tmp_path BEFORE importing or starting the app, so the '
        'database starts empty and tests do not depend on each other or on order. Arrange the data the test needs '
        'through the public API, act once, then assert status AND body. Start the server once per module with a fixture '
        '(port 0, daemon thread, shutdown in teardown). A test that fails must print what it got: assert with a '
        'message containing the status and the first 300 characters of the body. Never weaken an assertion to make it '
        'pass; fix the product.'),
    checklist=('Every acceptance criterion has a test that would fail if the behaviour broke.',
               'Tests are independent: each uses its own empty DATA_DIR.'),
)

REPAIR_METHOD = Skill(
    key='skill.repair_method', version='1',
    purpose='A repair round finds the root cause of each failure and changes exactly the code that causes it.',
    boundaries='Repair and evolution rounds; does not change the approved scope.',
    roles=(ROLE_REPAIR, ROLE_EVOLUTION),
    guidance=(
        'Repair method (how a senior engineer debugs): 1) Read every failure and its evidence; group failures that '
        'share one cause (a crash in init_db() fails every test: fix that first). 2) For each group find the exact file '
        'and function from the traceback or the failing request, and read that code in the repository you were given. '
        '3) Decide whether the product, the test, or the acceptance step is wrong: the approved acceptance text is the '
        'authority -- fix the product when it disagrees; fix a test or plan step only when it contradicts the approved '
        'text or uses a path/variable that does not exist (e.g. a capture path missing from the response). 4) Make the '
        'smallest change that removes the cause, keep every behaviour that already passed, and return each changed '
        'file in full. 5) Before answering, re-run the failing step in your head against the new code. If the previous '
        'round changed nothing (NO_PROGRESS), your diagnosis was wrong: pick a different cause. Never put the '
        'explanation outside the JSON.'),
    checklist=('Each failure group was traced to code and changed there.',
               'Nothing that passed before was removed or weakened.'),
)

SECURITY_BASICS = Skill(
    key='skill.security_basics', version='1',
    purpose='The product is safe by default: no injection, no leaked secrets, no unsafe trust in the client.',
    boundaries='Application code; platform sign-in rules stay with the platform.',
    roles=(ROLE_GENERATOR, ROLE_REPAIR, ROLE_EVOLUTION, ROLE_REVIEWER),
    guidance=(
        'Security basics: every SQL statement uses parameters (?), never string formatting; user input never reaches '
        'a shell, eval/exec, open() of a client-chosen path, or a redirect target without an allow-list. No secret, '
        'key or password in code, HTML or logs; read configuration from os.environ. The server re-checks every rule '
        'the page checks (prices, capacity, ownership) and never trusts ids or roles sent by the client. Answer errors '
        'with a short message, never a traceback. Send Content-Type on every response and "X-Content-Type-Options: '
        'nosniff" on HTML and JSON.'),
    checklist=('All SQL is parameterised; no secrets in the repository; errors show no traceback.',
               'Server re-validates every client-side rule.'),
)

SPEC_PRECISION = Skill(
    key='skill.spec_precision', version='1',
    purpose='Every requirement is concrete enough that two engineers would build the same behaviour.',
    boundaries='The architect specification; not code.',
    roles=(ROLE_ARCHITECT, ROLE_REVIEWER),
    guidance=(
        'Specification precision (how a senior product architect writes it): turn every phrase of the request into '
        'observable behaviour with its boundaries. A time view names its window ("weekly schedule" = the classes of the '
        'current week, Sunday 00:00 to Saturday 23:59 Asia/Jerusalem unless the request says otherwise, with previous/next '
        'week navigation), a list names its order and filter, a limit names what happens when it is reached (full class '
        '-> waitlist or a 409 with a message), and every state change names who may do it. Each acceptance criterion '
        'states the input, the action and the exact observable result, so its test is obvious. Do not leave a word such '
        'as "manage", "track" or "schedule" without saying which screens and actions it means.'),
    checklist=('Every view states its window, order and filter; every limit states its outcome.',),
)

WEB_SKILLS: tuple[Skill, ...] = (REQUEST_FIDELITY, FORM_VALIDATION, UI_STATES, TEXT_LOCALE, DATA_INTEGRITY, VISUAL_DESIGN,
                                   SPEC_PRECISION, ACCEPTANCE_PLAN, TEST_DESIGN, REPAIR_METHOD, SECURITY_BASICS)


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
