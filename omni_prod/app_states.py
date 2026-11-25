"""APP_STATES: every data screen of a generated APP shows loading, empty and error, and a server error reaches the
customer as a sentence with an action, never a stack trace (warehouse 130, first slice; released by the owner 2026-11-22).

The new engine serves content-only sites; an app stays on the existing path (site_content.decide: 'not_content_only').
This gate is the first piece of the app pipeline. It is installed on every build whose approved request is NOT a
content-only site -- product_architect.content_only_approved, the same function the route decides with -- and never on
a content-only site. The decision and its reason are written to the build evidence on every build ('app_states').

Static, deterministic, no model, bounded (MAX_FILE_CHARS per file, MAX_FINDINGS kept, MAX_CHAIN_LINKS and
MAX_CALL_DEPTH for the walks). It reads the repository the sandbox ran: the page as served when the preview smoke of
this round returned it (skill_units.gate.served_copy), otherwise as written.

Client, per page (every HTML document, with its inline scripts and the repository's script files it loads):
  a DATA READ is a fetch() call that does not name a write method (POST, PUT, PATCH, DELETE); a static asset (.css,
  .js, an image, a font) is not one. A page with a data read is a DATA SCREEN, and it must have
    APP_NO_LOADING_STATE      an element marked data-state="loading"
    APP_NO_EMPTY_STATE        an element marked data-state="empty"
    APP_NO_ERROR_STATE        an element marked data-state="error"
    APP_ERROR_WITHOUT_ACTION  ...which holds, in the page itself, a sentence (two words at least, outside the button
                              or link: its label is the action) and a button or link
  and every data read must
    APP_FETCH_UNHANDLED       be caught: .catch() (or a second .then argument) on its chain, inside try { } catch, or
                              inside a named function whose call is caught (MAX_CALL_DEPTH levels)
    APP_STATUS_UNCHECKED      check the response (.ok or .status) before its data is used
  and no script writes an error's own text into the page
    APP_RAW_ERROR_SHOWN       textContent / innerText / innerHTML / alert / append ... given err.stack, err.message,
                              String(err), `${err}` or err itself (err: a caught error), or a response's statusText
Server, every Python file that is not a test (read with ast, never executed):
    APP_TRACEBACK_TO_CLIENT   a response written in a broad handler (bare except, except Exception / BaseException, a
                              Flask or FastAPI handler of Exception or 500) carries the exception's own text, or any
                              response carries a formatted traceback
    APP_DEBUG_ON              the server runs in debug mode (debug=True, use_debugger=True, app.debug = True, a DEBUG
                              config of True, cgitb.enable())
    APP_SERVER_ERROR_NOT_JSON a server error is answered with an HTML error page (send_error or abort with a 5xx code)

The marker (data-state) is the contract the generator is told (REQUIREMENT, carried into the spec by carry_rule) and
the one a browser check of each state can use. That browser check (warehouse 130.1, "a browser check shows each of
them") is NOT built here: this gate proves the states are in the code, not that a browser shows each one. Not seen: a
request through XMLHttpRequest or a library; a script served from a Python string (said as an unresolved script, never
passed in silence); a server that is not Python.

A new gate enters at warn (gate.CALIBRATING, the owner's rule of 2026-11-16): its findings go to the log and to the
evidence of every app build, and it blocks only after calibration. Each finding is written for the repair model: what
is missing, where, and what to write.
"""
from __future__ import annotations

import ast
import functools
import logging
import re
from dataclasses import replace

GATE = 'APP_STATES'
ACCEPTANCE_PREFIX = 'gate-APP_STATES-'
REQUIREMENT = 'APP-STATES'
STATES = ('loading', 'empty', 'error')
CODES = ('APP_NO_LOADING_STATE', 'APP_NO_EMPTY_STATE', 'APP_NO_ERROR_STATE', 'APP_ERROR_WITHOUT_ACTION',
         'APP_FETCH_UNHANDLED', 'APP_STATUS_UNCHECKED', 'APP_RAW_ERROR_SHOWN', 'APP_TRACEBACK_TO_CLIENT',
         'APP_DEBUG_ON', 'APP_SERVER_ERROR_NOT_JSON')
STATE_CODE = {'loading': 'APP_NO_LOADING_STATE', 'empty': 'APP_NO_EMPTY_STATE', 'error': 'APP_NO_ERROR_STATE'}
WRITE_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')
MAX_FILE_CHARS = 400_000
MAX_FINDINGS = 40
MAX_CHAIN_LINKS = 12
MAX_CALL_DEPTH = 2
MAX_CALL_SITES = 40           # call sites of one function looked at, per level
MAX_ELEMENT_CHARS = 6000
_LOG = logging.getLogger(__name__)

RULE = ('Every screen that loads data from the server shows three states, each an element of the page marked with '
        'data-state: data-state="loading" while the request runs; data-state="empty" when the answer has no records '
        '(a sentence that says there is nothing here yet and what to do); data-state="error" when the request fails or '
        'the response is not ok (a sentence in the page\'s language that says what failed and what to do, and a button '
        'that runs the request again), written in the page itself. Catch every request, check response.ok before using '
        'the data, and never show an exception\'s text, a stack trace or the raw server answer. The server logs every '
        'exception and answers every error with JSON {"error": "<a sentence for the user>"}; it never sends a traceback '
        'and never runs in debug mode.')

_FIX = {
    'APP_NO_LOADING_STATE': 'Add an element marked data-state="loading" (a short line in the page\'s language) that is '
                            'shown from the moment the request starts until the answer arrives, then hidden.',
    'APP_NO_EMPTY_STATE': 'Add an element marked data-state="empty" with a sentence in the page\'s language that says '
                          'there is nothing here yet and what to do next (for example a button that opens the add '
                          'form); show it when the answer has no records and hide it otherwise.',
    'APP_NO_ERROR_STATE': 'Add an element marked data-state="error" with a sentence in the page\'s language that says '
                          'what failed and what to do, and a <button> that runs the request again; show it when the '
                          'request throws or the response is not ok.',
    'APP_ERROR_WITHOUT_ACTION': 'Write inside the element marked data-state="error", in the page itself, a sentence that '
                                'says what failed and what to do, and a <button> (or a link) that does it, for example '
                                '"we could not load the list. Check the connection and try again." with a button that '
                                'repeats the request.',
    'APP_FETCH_UNHANDLED': 'Catch the failure: put the request in try { ... } catch (err) { ... } (or add .catch(...)), '
                           'show the data-state="error" element in the catch, and log err with console.error -- never '
                           'show it.',
    'APP_STATUS_UNCHECKED': 'Check the response before using it: if (!response.ok) show the data-state="error" element '
                            'and stop; only an ok response is data.',
    'APP_RAW_ERROR_SHOWN': 'Never write an error\'s own text, its stack or the raw server answer into the page: show the '
                           'sentence of the data-state="error" element, and log the error with console.error.',
    'APP_TRACEBACK_TO_CLIENT': 'Log the exception on the server (logging.exception(...)) and answer with status 500, '
                               'Content-Type application/json and {"error": "<a sentence for the customer: what failed '
                               'and what to do>"}; never put the exception\'s text or a traceback in the response.',
    'APP_DEBUG_ON': 'Turn debug mode off: in debug mode a server error shows the customer a stack trace.',
    'APP_SERVER_ERROR_NOT_JSON': 'Answer a server error with status 500, Content-Type application/json and {"error": '
                                 '"<a sentence for the customer: what failed and what to do>"}, not with an HTML error '
                                 'page.',
}
if set(_FIX) != set(CODES):                          # a code with no instruction for the repair model stops the import
    raise RuntimeError(f'APP_STATES codes without a fix: {sorted(set(CODES) ^ set(_FIX))}')


# ---------------------------------------------------------------------------------------------------------- the JS scan

_REGEX_PRECEDERS = set('(,=:[!&|?{};+-*%<>~^')
_REGEX_KEYWORDS = ('return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'yield',
                   'await', 'instanceof')
_PAIRS = {'(': ')', '[': ']', '{': '}'}


def scan_js(src: str) -> tuple[str, str]:
    """(code, masked), each the same length as `src` so positions agree: comments are blanked in both; in `masked` the
    contents of string, template and regular-expression literals are blanked too (a template's ${...} stays code).
    One pass, no backtracking. Newlines are kept, so line numbers agree."""
    n = len(src)
    code, masked = list(src), list(src)
    tmpl: list[int] = []        # for each open ${...}: the brace depth outside it
    braces, prev, word, i = 0, '', '', 0

    def blank(a: int, b: int, both: bool) -> None:
        for k in range(a, min(b, n)):
            if src[k] != '\n':
                masked[k] = ' '
                if both:
                    code[k] = ' '

    def template_text(start: int) -> int:
        """Blank template text from `start`; returns the index of the closing ` or of the $ of ${ (or n)."""
        j = start
        while j < n:
            if src[j] == '\\':
                j += 2
                continue
            if src[j] == '`' or (src[j] == '$' and j + 1 < n and src[j + 1] == '{'):
                break
            j += 1
        blank(start, j, False)
        return min(j, n)

    while i < n:
        c = src[i]
        if c == '/' and src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            blank(i, j, True)
            i = j
            continue
        if c == '/' and src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            blank(i, j, True)
            i = j
            continue
        if c in '\'"':
            j = i + 1
            while j < n and src[j] != c and src[j] != '\n':
                j += 2 if src[j] == '\\' else 1
            blank(i + 1, j, False)
            i, prev, word = j + 1, c, ''
            continue
        if c == '`' or (c == '}' and tmpl and braces == tmpl[-1] + 1):
            if c == '}':                                    # the end of a ${...}: back into the template text
                tmpl.pop()
                braces -= 1
            j = template_text(i + 1)
            if j < n and src[j] == '$':
                tmpl.append(braces)
                braces += 1
                i, prev, word = j + 2, '{', ''
                continue
            i, prev, word = j + 1, '`', ''
            continue
        if c == '/' and (prev == '' or prev in _REGEX_PRECEDERS or word in _REGEX_KEYWORDS):
            j, in_class = i + 1, False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '[':
                    in_class = True
                elif src[j] == ']':
                    in_class = False
                elif src[j] == '/' and not in_class:
                    break
                j += 1
            blank(i + 1, j, False)
            i, prev, word = j + 1, '/', ''
            continue
        if c.isalnum() or c in '_$':
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in '_$'):
                j += 1
            word, prev, i = src[i:j], 'a', j
            continue
        if not c.isspace():
            if c == '{':
                braces += 1
            elif c == '}':
                braces -= 1
            prev, word = c, ''
        i += 1
    return ''.join(code), ''.join(masked)


@functools.lru_cache(maxsize=8)
def _bracket_pairs(masked: str) -> dict[int, int]:
    """{open index: close index} of every bracket of the masked view, one linear pass (one stack per kind). A
    scan that matched each bracket by walking forward was quadratic: 2,000 nested functions took 9 seconds."""
    pairs: dict[int, int] = {}
    stacks: dict[str, list[int]] = {o: [] for o in _PAIRS}
    closers = {c: o for o, c in _PAIRS.items()}
    for j, ch in enumerate(masked):
        if ch in stacks:
            stacks[ch].append(j)
        elif ch in closers and stacks[closers[ch]]:
            pairs[stacks[closers[ch]].pop()] = j
    return pairs


def match(masked: str, i: int) -> int:
    """The index of the bracket that closes the one at `i` (in the masked view), or -1."""
    return _bracket_pairs(masked).get(i, -1)


def _top_commas(masked: str, a: int, b: int) -> list[int]:
    """Positions of the commas at depth 0 between a and b (the arguments of a call)."""
    out, depth = [], 0
    for j in range(a, b):
        ch = masked[j]
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            out.append(j)
    return out


def _line(text: str, pos: int) -> int:
    return text.count('\n', 0, pos) + 1


_FETCH = re.compile(r'(?<![\w$.])(?:(?:window|globalThis|self)\s*\.\s*)?fetch\s*\(')
_ASSET = re.compile(r'\.(?:css|m?js|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|mp3|wav|ogg)(?:[?#]|$)',
                    re.I)
_METHOD = re.compile(r'\bmethod\s*:\s*([\'"`])\s*([A-Za-z]+)\s*\1')
_METHOD_KEY = re.compile(r'\bmethod\b\s*[:,}]')
_LITERAL = re.compile(r'^([\'"`])(.*?)\1', re.S)
_LINK = re.compile(r'\s*\.\s*(then|catch|finally)\s*\(')
_TRY = re.compile(r'(?<![\w$])try\s*\{')
_CATCH_AFTER = re.compile(r'\s*catch\b')
_KEYWORDS = {'if', 'for', 'while', 'switch', 'catch', 'function', 'with', 'return', 'typeof', 'new', 'await', 'else'}
_FUNCS = (
    re.compile(r'(?<![\w$])(?:async\s+)?function\s*\*?\s*([\w$]+)\s*\('),
    re.compile(r'(?<![\w$.])(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s+)?(?:function\b[^(]*\(|\(|([\w$]+)\s*=>)'),
    re.compile(r'(?<![\w$.])(?:async\s+)?([\w$]+)\s*\((?=[^()]*\)\s*\{)'),
)
_STATUS = re.compile(r'\.\s*(?:ok|status)\b')


def _functions(masked: str) -> list[tuple[str, int, int, int]]:
    """(name, header start, body open, body close) of every named function the scan can see (bounded by the text)."""
    out = []
    for k, pattern in enumerate(_FUNCS):
        for m in pattern.finditer(masked):
            name = m.group(1)
            if name in _KEYWORDS:
                continue
            j = m.end()
            if masked[j - 1] == '(':                       # the parameter list, then the body
                close = match(masked, j - 1)
                if close < 0:
                    continue
                j = close + 1
            rest = masked[j:j + 200]
            arrow = re.match(r'\s*=>\s*\{', rest) if k == 1 else None
            body = re.match(r'\s*\{', rest) if arrow is None else arrow
            if body is None:
                continue
            open_ = j + body.end() - 1
            close = match(masked, open_)
            if close > open_:
                out.append((name, m.start(), open_, close))
    return out


def _innermost(funcs, pos: int):
    inside = [f for f in funcs if f[2] < pos < f[3]]
    return max(inside, key=lambda f: f[2]) if inside else None


def _chain(masked: str, close: int) -> tuple[int, bool]:
    """(end of the .then/.catch/.finally chain after a call that closes at `close`, is a rejection handled on it?)"""
    i, caught = close + 1, False
    for _ in range(MAX_CHAIN_LINKS):
        m = _LINK.match(masked, i)
        if not m:
            break
        end = match(masked, m.end() - 1)
        if end < 0:
            break
        if m.group(1) == 'catch' or (m.group(1) == 'then' and _top_commas(masked, m.end(), end)):
            caught = True
        i = end + 1
    return i, caught


def _tries(masked: str) -> list[tuple[int, int]]:
    """(open, close) of every try block that has a catch."""
    out = []
    for m in _TRY.finditer(masked):
        open_ = m.end() - 1
        close = match(masked, open_)
        if close > 0 and _CATCH_AFTER.match(masked, close + 1):
            out.append((open_, close))
    return out


def _caught(masked: str, pos: int, close: int, funcs, tries, depth: int = 0) -> bool:
    if _chain(masked, close)[1] or any(o < pos < c for o, c in tries):
        return True
    if depth >= MAX_CALL_DEPTH:
        return False
    f = _innermost(funcs, pos)
    if f is None:
        return False
    name = f[0]
    headers = [(h, o) for n, h, o, _ in funcs if n == name]  # a definition of the name is not a call of it
    sites = (c for c in re.finditer(r'(?<![\w$.])' + re.escape(name) + r'\s*\(', masked)
             if not any(h <= c.start() < o for h, o in headers))
    for _, call in zip(range(MAX_CALL_SITES), sites):
        cclose = match(masked, call.end() - 1)
        if cclose > 0 and _caught(masked, call.start(), cclose, funcs, tries, depth + 1):
            return True
    return False


def _checked(masked: str, pos: int, close: int, funcs) -> bool:
    end, _ = _chain(masked, close)
    if _STATUS.search(masked, pos, end):
        return True
    f = _innermost(funcs, pos)
    return bool(_STATUS.search(masked, pos, f[3] if f else min(len(masked), pos + 3000)))


def _route(first: str) -> str:
    first = ' '.join(first.split())
    m = _LITERAL.match(first)
    if m is None:
        return first[:80] or '?'
    return m.group(2)[:80] + ('…' if m.end() < len(first) else '')


def reads(text: str, where: str) -> tuple[list[dict], str, str]:
    """(the data reads of one script, its code view, its masked view)."""
    code, masked = scan_js(text[:MAX_FILE_CHARS])
    funcs, tries = _functions(masked), _tries(masked)
    out = []
    for m in _FETCH.finditer(masked):
        open_ = m.end() - 1
        close = match(masked, open_)
        if close < 0:
            continue
        commas = _top_commas(masked, open_ + 1, close)
        first = code[open_ + 1:commas[0] if commas else close].strip()
        route = _route(first)
        if _ASSET.search(route.rstrip('…')):
            continue
        options = code[commas[0] + 1:close] if commas else ''
        lit = _METHOD.search(options)
        method = lit.group(2).upper() if lit else ('?' if _METHOD_KEY.search(options) else 'GET')
        if method in WRITE_METHODS:
            continue
        out.append({'route': route, 'method': method, 'where': f'{where}:{_line(text, m.start())}',
                    'caught': _caught(masked, m.start(), close, funcs, tries),
                    'status_checked': _checked(masked, m.start(), close, funcs)})
    return out, code, masked


_SINK = re.compile(r'\.\s*(?:textContent|innerText|innerHTML|outerHTML)\s*\+?=(?!=)|(?<![\w$.])alert\s*\(|'
                   r'\.\s*(?:insertAdjacentHTML|append|prepend|replaceChildren|replaceWith)\s*\(|'
                   r'(?<![\w$])document\s*\.\s*write(?:ln)?\s*\(')
_CATCH_BLOCK = re.compile(r'(?<![\w$.])catch\s*\(\s*([\w$]+)\s*\)\s*\{')
_CATCH_CALL = re.compile(r'\.\s*catch\s*\(')
_CATCH_PARAM = re.compile(r'\s*(?:async\s+)?(?:function\s*[\w$]*\s*)?\(?\s*([\w$]+)')
_RAW_ALWAYS = re.compile(r'\.\s*(?:stack|statusText)\b')


def _catch_scopes(masked: str) -> list[tuple[str, int, int]]:
    """(the caught error's name, start, end) of every catch block and every .catch(...) callback."""
    out = []
    for m in _CATCH_BLOCK.finditer(masked):
        close = match(masked, m.end() - 1)
        if close > 0:
            out.append((m.group(1), m.end() - 1, close))
    for m in _CATCH_CALL.finditer(masked):
        close = match(masked, m.end() - 1)
        param = _CATCH_PARAM.match(masked, m.end(), close) if close > 0 else None
        if param and param.group(1) not in _KEYWORDS:
            out.append((param.group(1), m.end() - 1, close))
    return out


def _raw_name(var: str):
    """The caught error itself, its message, stack or toString() -- not another property (err.name is not its text)."""
    return re.compile(r'(?<![\w$.])' + re.escape(var) + r'(?:\s*\.\s*(?:message|stack|toString)\b|(?![\w$])(?!\s*[.(\[]))')


def raw_errors(text: str, code: str, masked: str, where: str) -> list[dict]:
    """Every place a script writes an error's own text into the page (APP_RAW_ERROR_SHOWN): a stack or a statusText
    anywhere, or the caught error inside its own catch block or .catch callback."""
    scopes = [(_raw_name(v), a, b) for v, a, b in _catch_scopes(masked)]
    out = []
    for m in _SINK.finditer(masked):
        if masked[m.end() - 1] == '(':
            close = match(masked, m.end() - 1)
            a, b = m.end(), (close if close > 0 else min(len(masked), m.end() + 600))
        else:
            a, depth, b = m.end(), 0, m.end()
            while b < len(masked) and b - a < 600:
                ch = masked[b]
                if ch in '([{':
                    depth += 1
                elif ch in ')]}':
                    depth -= 1
                    if depth < 0:
                        break
                elif ch in ';\n' and depth == 0:
                    break
                b += 1
        value = masked[a:b] + ' '
        if _RAW_ALWAYS.search(value) or any(p.search(value) for p, lo, hi in scopes if lo < m.start() < hi):
            out.append({'where': f'{where}:{_line(text, m.start())}', 'snippet': ' '.join(code[m.start():b].split())[:120]})
    return out


# ------------------------------------------------------------------------------------------------------- the page scan

_SCRIPT = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.S | re.I)
_COMMENT = re.compile(r'<!--.*?-->', re.S)
_SRC = re.compile(r'\bsrc\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
_TYPE = re.compile(r'\btype\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
_JS_TYPES = ('', 'text/javascript', 'application/javascript', 'module', 'text/babel')
# on an element (a start tag), never a CSS selector or a querySelector string that only looks for one
_MARK = re.compile(r'<[a-zA-Z][\w-]*\b[^<>]*?\bdata-state\s*=\s*\\?["\']?(loading|empty|error)\b', re.I)
_MARK_JS = re.compile(r'(?:dataset\s*\.\s*state\s*=\s*|setAttribute\s*\(\s*[\'"]data-state[\'"]\s*,\s*)'
                      r'[\'"`](loading|empty|error)[\'"`]', re.I)
_ERROR_EL = re.compile(r'<([a-zA-Z][\w-]*)\b[^>]*\bdata-state\s*=\s*\\?["\']?error\b[^>]*>', re.I)
_ACTION = re.compile(r'<(?:button|a)\b|role\s*=\s*\\?["\']button', re.I)
_ACTION_EL = re.compile(r'<(button|a)\b[^>]*>.*?</\1\s*>', re.S | re.I)
_WORD = re.compile(r'[^\W\d_]{2,}')
_TAG = re.compile(r'<[^>]*>|\$\{[^}]*\}')
_VOID = {'input', 'img', 'br', 'hr', 'meta', 'link', 'source', 'area', 'col', 'embed', 'wbr'}


def _attr(pattern, attrs: str) -> str | None:
    m = pattern.search(attrs)
    return next((g for g in m.groups() if g is not None), '') if m else None


def resolve_script(src: str, repository: dict) -> str | None:
    """The repository path a page's <script src> names, or None (unresolved). Never a guess between two files."""
    s = src.split('?')[0].split('#')[0].strip()
    p = re.sub(r'^(?:\./|/)+', '', s)
    for c in (p, f'static/{p}', f'public/{p}', p.split('/', 1)[1] if '/' in p else None):
        if c and isinstance(repository.get(c), str):
            return c
    base = p.rsplit('/', 1)[-1]
    same = [k for k, v in repository.items() if isinstance(v, str) and k.rsplit('/', 1)[-1] == base
            and k.endswith(('.js', '.mjs'))]
    return same[0] if len(same) == 1 else None


def _inner(markup: str, start: int, tag: str) -> str:
    """The markup inside an element whose start tag ends at `start` (bounded; nested tags of the same name counted)."""
    if tag.lower() in _VOID:
        return ''
    depth, pos = 1, start
    for m in re.finditer(r'<(/?)' + re.escape(tag) + r'\b[^>]*>', markup[start:start + MAX_ELEMENT_CHARS], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return markup[start:start + m.start()]
        pos = start + m.end()
    return markup[start:max(pos, start + MAX_ELEMENT_CHARS)]


def _error_elements(markup: str, scripts: list[tuple[str, str, str, str]]) -> list[str]:
    """The markup inside every element marked data-state="error": in the page, and in a script's string literals."""
    out = [_inner(markup, m.end(), m.group(1)) for m in _ERROR_EL.finditer(markup)]
    for _, _, code, masked in scripts:
        for m in _ERROR_EL.finditer(code):
            if masked[m.start()] != ' ':
                continue                                    # not inside a string literal
            # the literal ends where the masked view shows code again (its closing quote)
            end = m.end()
            while end < len(masked) and masked[end] == ' ' and end - m.end() < MAX_ELEMENT_CHARS:
                end += 1
            out.append(_inner(code[:end], m.end(), m.group(1)))
    return out


def _sentence_and_action(inner: str) -> tuple[bool, bool]:
    """(a sentence of two words at least OUTSIDE the button or link -- its label is the action, not the sentence,
    is there a button or link)."""
    told = _TAG.sub(' ', _ACTION_EL.sub(' ', inner))
    return len(_WORD.findall(told)) >= 2, bool(_ACTION.search(inner))


def page_parts(path: str, html: str, repository: dict) -> tuple[str, list[tuple[str, str]], list[str], list[str]]:
    """(markup without scripts and comments, [(where, script text)], [loaded script paths], [unresolved srcs])."""
    html = _COMMENT.sub(lambda m: '\n' * m.group().count('\n'), html[:MAX_FILE_CHARS])
    scripts, loaded, unresolved = [], [], []
    for m in _SCRIPT.finditer(html):
        attrs, body = m.group(1), m.group(2)
        kind = (_attr(_TYPE, attrs) or '').strip().lower()
        if kind not in _JS_TYPES:
            continue                                        # JSON-LD, a template, an import map: not a script
        src = _attr(_SRC, attrs)
        if src is not None:
            if re.match(r'^(?:[a-z][\w+.-]*:)?//|^data:', src.strip(), re.I):
                continue                                    # a library from a CDN: not the product's own code
            resolved = resolve_script(src, repository)
            if resolved is None:
                unresolved.append(f'{path}: {src}')
            else:
                loaded.append(resolved)
                scripts.append((resolved, repository[resolved]))
        if body.strip():
            line = _line(html, m.start(2))
            scripts.append((f'{path} (script at line {line})', '\n' * (line - 1) + body))
    markup = _SCRIPT.sub(' ', html)
    return markup, scripts, loaded, unresolved


def screen(name: str, markup: str, scripts: list[tuple[str, str]]) -> tuple[dict, list[dict]]:
    """One page: its data reads, its states and its findings."""
    scanned, found_reads, raws, marks = [], [], [], set()
    marks.update(m.group(1).lower() for m in _MARK.finditer(markup))
    for where, text in scripts:
        rs, code, masked = reads(text, where)
        scanned.append((where, text, code, masked))
        found_reads += rs
        raws += raw_errors(text, code, masked, where)
        marks.update(m.group(1).lower() for m in _MARK.finditer(code))
        marks.update(m.group(1).lower() for m in _MARK_JS.finditer(code))
    findings = [_finding('APP_RAW_ERROR_SHOWN', r['where'], f"{r['where']} writes the error's own text into the page "
                                                             f"({r['snippet']})") for r in raws]
    info = {'page': name, 'reads': found_reads[:20], 'states': {s: s in marks for s in STATES}}
    if not found_reads:
        return info, findings
    routes = ', '.join(sorted({r['route'] for r in found_reads}))[:200]
    for state in STATES:
        if state not in marks:
            why = {'loading': 'shows nothing while it loads', 'empty': 'shows nothing when the answer has no records',
                   'error': 'shows nothing when the request fails'}[state]
            findings.append(_finding(STATE_CODE[state], name, f'{name} loads {routes} and {why}'))
    if 'error' in marks:
        pairs = [_sentence_and_action(inner) for inner in _error_elements(markup, scanned)]
        info.update(error_sentence=any(s for s, _ in pairs), error_action=any(a for _, a in pairs))
        if not any(s and a for s, a in pairs):
            s_, a_ = info['error_sentence'], info['error_action']
            why = (f'the error state of {name} is not an element of the page: no element marked data-state="error" '
                   'holds a sentence and a button or link' if not pairs else
                   f'the error element of {name} has no sentence and no button or link' if not (s_ or a_) else
                   f'the error element of {name} has no sentence' if not s_ else
                   f'the error element of {name} has no button or link' if not a_ else
                   f'no error element of {name} holds both a sentence and a button or link')
            findings.append(_finding('APP_ERROR_WITHOUT_ACTION', name, why))
    for r in found_reads:
        if not r['caught']:
            findings.append(_finding('APP_FETCH_UNHANDLED', r['where'],
                                     f"the request to {r['route']} ({r['where']}) is not caught: when it fails, the "
                                     'screen stays as it was and the customer is told nothing'))
        if not r['status_checked']:
            findings.append(_finding('APP_STATUS_UNCHECKED', r['where'],
                                     f"the answer of {r['route']} ({r['where']}) is used without checking response.ok: "
                                     'a server error is shown as if it were data'))
    return info, findings


# ------------------------------------------------------------------------------------------------------ the server scan

_BROAD = ('Exception', 'BaseException')
_TB = {'format_exc', 'format_exception', 'format_tb', 'format_stack', 'format_exception_only', 'extract_tb',
       'extract_stack'}
_RESPONSE_CALL = re.compile(r'send|write|respond|reply|json|response|abort|error|fail|httpexception', re.I)
_LOG_OWNER = re.compile(r'^(?:_?log(?:ger|ging)?s?|_?LOG(?:GER)?|stderr|stdout|warnings)$', re.I)
_RAW_ATTRS = ('args', 'message', 'msg', 'strerror', '__traceback__', '__str__', '__repr__', 'with_traceback')
_HARMLESS_CALLS = ('isinstance', 'issubclass', 'type', 'getattr', 'hasattr', 'id', 'len')
_DEBUG_CALLEES = ('run', 'run_simple', 'Flask', 'FastAPI', 'Starlette', 'Quart', 'Sanic', 'Application', 'serve')
_HANDLER_DECORATORS = ('errorhandler', 'exception_handler')
_HANDLER_REGISTRARS = ('register_error_handler', 'add_exception_handler')


def _callee(call: ast.Call) -> tuple[str, list[str]]:
    """(the called name, the names of the object chain it is called on)."""
    f, owners = call.func, []
    name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ''
    v = f.value if isinstance(f, ast.Attribute) else None
    for _ in range(8):
        if isinstance(v, ast.Attribute):
            owners.append(v.attr)
            v = v.value
        elif isinstance(v, ast.Name):
            owners.append(v.id)
            break
        elif isinstance(v, ast.Call):
            v = v.func
        else:
            break
    return name, owners


_EXCEPTION_CLASS = re.compile(r'[A-Z]\w*(?:Error|Exception|Warning)')


def _is_response(call: ast.Call) -> bool:
    name, owners = _callee(call)
    if not name or name == 'print' or name.lower().startswith('log') or any(_LOG_OWNER.match(o) for o in owners):
        return False
    if _EXCEPTION_CLASS.fullmatch(name) and name != 'HTTPException':
        return False                                        # raising another exception is not a response
    return bool(_RESPONSE_CALL.search(name))


def _is_broad(node) -> bool:
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in _BROAD
    if isinstance(node, ast.Attribute):
        return node.attr in _BROAD
    if isinstance(node, ast.Tuple):
        return any(_is_broad(e) for e in node.elts)
    if isinstance(node, ast.Constant):
        return node.value == 500
    return False


def _traceback_call(node) -> bool:
    return (isinstance(node, ast.Call) and
            ((isinstance(node.func, ast.Attribute) and node.func.attr in _TB) or
             (isinstance(node.func, ast.Name) and node.func.id in _TB)))


def _carries(node, var: str | None, tainted: set[str], parents: dict) -> bool:
    """Does this expression carry a traceback, the caught exception's own text, or a name built from them?"""
    for n in ast.walk(node):
        if _traceback_call(n):
            return True
        if not isinstance(n, ast.Name):
            continue
        if n.id in tainted:
            return True
        if var is None or n.id != var:
            continue
        p = parents.get(n)
        if isinstance(p, ast.Attribute):
            if p.attr in _RAW_ATTRS:
                return True
            continue
        if isinstance(p, ast.Call) and p.func is not n and _callee(p)[0] in _HARMLESS_CALLS:
            continue
        if isinstance(p, (ast.Compare, ast.BoolOp)) or (isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.Not)):
            continue
        return True
    return False


def _handler_findings(body: list, var: str | None, label: str, path: str, parents: dict) -> list[dict]:
    """Responses written in one broad handler that carry the exception's text (one pass, names tainted in order)."""
    out, tainted = [], set()
    nodes = sorted((n for stmt in body for n in ast.walk(stmt) if hasattr(n, 'lineno')),
                   key=lambda n: (n.lineno, getattr(n, 'col_offset', 0)))
    for n in nodes:
        if isinstance(n, ast.Assign) and _carries(n.value, var, tainted, parents):
            tainted |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        sink = (isinstance(n, ast.Call) and _is_response(n)) or (isinstance(n, ast.Return) and n.value is not None)
        if sink and _carries(n.value if isinstance(n, ast.Return) else n, var, tainted, parents):
            where = f'{path}:{n.lineno}'
            out.append(_finding('APP_TRACEBACK_TO_CLIENT', where,
                                f"{where} sends the exception's own text or a traceback to the client (in {label})"))
    return out


def server_findings(path: str, source: str) -> tuple[list[dict], str | None]:
    """(findings, None) for one Python file, or ([], the reason it could not be read)."""
    try:
        tree = ast.parse(source[:MAX_FILE_CHARS])
    except SyntaxError as exc:
        return [], f'{path}: not parsed ({exc.msg}, line {exc.lineno})'
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out, handlers = [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler) and _is_broad(n.type):
            handlers.append((n.body, n.name, f'except {ast.unparse(n.type) if n.type is not None else ""}'.strip()))
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in n.decorator_list:
                if (isinstance(d, ast.Call) and _callee(d)[0] in _HANDLER_DECORATORS and d.args
                        and _is_broad(d.args[0]) and n.args.args):
                    handlers.append((n.body, n.args.args[-1].arg, f'the error handler {n.name}'))
        elif isinstance(n, ast.Call):
            name, owners = _callee(n)
            if (name in _HANDLER_REGISTRARS and len(n.args) >= 2 and _is_broad(n.args[0])
                    and isinstance(n.args[1], ast.Name) and n.args[1].id in functions):
                f = functions[n.args[1].id]
                if f.args.args:
                    handlers.append((f.body, f.args.args[-1].arg, f'the error handler {f.name}'))
            where = f'{path}:{n.lineno}'
            if _is_response(n) and any(_traceback_call(x) for x in ast.walk(n)):
                out.append(_finding('APP_TRACEBACK_TO_CLIENT', where, f'{where} sends a formatted traceback to the client'))
            debug = [k for k in n.keywords if k.arg in ('debug', 'use_debugger', 'DEBUG')
                     and isinstance(k.value, ast.Constant) and k.value.value is True]
            if (debug and (name in _DEBUG_CALLEES or debug[0].arg != 'debug' or name == 'update')) or \
                    (name == 'enable' and owners[:1] == ['cgitb']):
                out.append(_finding('APP_DEBUG_ON', where, f'{where} runs the server in debug mode '
                                                           f'({ast.unparse(n)[:100]})'))
            if (name in ('send_error', 'abort') and n.args and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, int) and n.args[0].value >= 500):
                out.append(_finding('APP_SERVER_ERROR_NOT_JSON', where, f'{where} answers a server error with an HTML '
                                                                        f'error page ({ast.unparse(n)[:100]})'))
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and n.value.value is True:
            for t in n.targets:
                if ((isinstance(t, ast.Attribute) and t.attr == 'debug') or
                        (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == 'DEBUG')):
                    where = f'{path}:{n.lineno}'
                    out.append(_finding('APP_DEBUG_ON', where, f'{where} runs the server in debug mode '
                                                               f'({ast.unparse(n)[:100]})'))
    for body, var, label in handlers:
        out += _handler_findings(body, var, label, path, parents)
    seen, unique = set(), []
    for f in out:                                           # a formatted traceback in a handler is said once
        key = (f['code'], f['where'])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique, None


# ------------------------------------------------------------------------------------------------------------ the check

def _finding(code: str, where: str, why: str) -> dict:
    if code not in CODES:
        raise ValueError(f'unknown APP_STATES code {code!r}')
    return {'code': code, 'where': where, 'why': why, 'fix': _FIX[code]}


def check(repository: dict, rendered=None) -> dict:
    """{'status': 'pass'|'fail'|'NOT_RUN', 'screens': [...], 'findings': [...], ...} for one generated repository.
    `rendered`: the preview smoke's {'/': html} of this round, when it passed (skill_units.gate.served_copy)."""
    from .repair_contracts import _TEST_FILE
    from .skill_units.gate import pages, served_copy
    found = served_copy(pages(repository), rendered)
    servers = [(p, t) for p, t in sorted(repository.items())
               if isinstance(t, str) and p.endswith('.py') and not _TEST_FILE.search(p)]
    if not found and not servers:
        return {'status': 'NOT_RUN', 'reason': 'no HTML page and no Python server in the generated repository',
                'screens': [], 'findings': [], 'findings_total': 0}
    screens, findings, loaded_all, unresolved, unparsed = [], [], set(), [], []
    parts = [(path, *page_parts(path, html, repository)) for path, html in found]
    for path, markup, scripts, loaded, missing in parts:
        loaded_all.update(loaded)
        unresolved += missing
        info, fs = screen(path, markup, scripts)
        screens.append(info)
        findings += fs
    # a script file no page loads by name (an import, a module, a router) is judged against every page's markup
    orphans = [(p, t) for p, t in sorted(repository.items())
               if isinstance(t, str) and p.endswith(('.js', '.mjs')) and p not in loaded_all and not _TEST_FILE.search(p)
               and _FETCH.search(t)]
    if orphans:
        info, fs = screen(' + '.join(p for p, _ in orphans)[:200], '\n'.join(m for _, m, _, _, _ in parts), orphans)
        screens.append(info)
        findings += fs
    for path, source in servers:
        fs, reason = server_findings(path, source)
        findings += fs
        if reason:
            unparsed.append(reason)
    data_screens = [s for s in screens if s['reads']]
    out = {'screens': screens[:20], 'data_screens': len(data_screens), 'server_files': [p for p, _ in servers][:20],
           'unresolved_scripts': unresolved[:20], 'unparsed': unparsed[:20],
           'findings': findings[:MAX_FINDINGS], 'findings_total': len(findings)}
    if findings:
        return {'status': 'fail', **out}
    if not found:                                           # the server was read; no screen was
        return {'status': 'NOT_RUN', 'reason': 'no HTML page in the generated repository: the screens were not '
                                               'checked (the server was, and passed)', **out}
    if not data_screens and unresolved:
        return {'status': 'NOT_RUN', 'reason': 'no data screen found, and scripts the pages load are not files of the '
                                               'repository: ' + '; '.join(unresolved)[:300], **out}
    return {'status': 'pass', **out}


class AppStatesExecutor:
    """warn: findings are recorded (last_check, the log, the build evidence) and the build goes on. block: every code
    found fails the round, one acceptance failure per code, written for the repair model."""

    def __init__(self, inner, mode: str):
        self._inner, self.mode, self.last_check = inner, mode, None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        from .autonomous_core import AcceptanceFailure
        report = self._inner.execute(repository=repository, spec=spec)
        rendered = getattr(self._inner, 'last_pages', None) if report.passed else None
        result = check(repository, rendered if isinstance(rendered, dict) else None)
        self.last_check = {**result, 'mode': self.mode}
        if result['status'] == 'NOT_RUN':
            _LOG.warning('GATE_NOT_RUN gate=%s %s', GATE, result['reason'])
            return report
        _LOG.info('APP_STATES mode=%s status=%s data_screens=%s findings=%s', self.mode, result['status'],
                  result['data_screens'], [(f['code'], f['where']) for f in result['findings']][:12])
        if result['status'] == 'pass' or self.mode != 'block':
            return report
        by_code: dict[str, list[dict]] = {}
        for f in result['findings']:
            by_code.setdefault(f['code'], []).append(f)
        problems = tuple(AcceptanceFailure(
            ACCEPTANCE_PREFIX + code,
            f"{code}: {'; '.join(f['why'] for f in fs[:3])}{f' (and {len(fs) - 3} more)' if len(fs) > 3 else ''}. "
            f"{_FIX[code]}")
            for code, fs in by_code.items())
        return replace(report, passed=False, failures=tuple(report.failures) + problems)


def applies(prompt: str) -> tuple[bool, str]:
    """(is this build an app, the reason): the route's own test -- an approved content-only site is not an app."""
    from .product_architect import content_only_approved
    return (False, 'content_only_site') if content_only_approved(prompt) else (True, 'not_content_only')


def install(engine, *, prompt: str) -> str:
    """Install APP_STATES on an app build. Returns the gate mode, or 'not_applicable' on a content-only site. The
    decision, its reason and the mode are kept on the engine for the evidence and said in the log on every build."""
    from .skill_units import gate as G
    core = getattr(engine, 'core', engine)
    mode = G.mode(GATE)                                     # an unknown value raises on every build, app or not
    ok, why = applies(prompt)
    core.app_states_decision = {'applies': ok, 'why': why}
    if not ok:
        _LOG.info('GATE_NOT_APPLICABLE gate=%s reason=%s', GATE, why)
        return 'not_applicable'
    modes = dict(getattr(core, 'gate_modes', None) or {})
    modes[GATE] = mode
    core.gate_modes = modes
    if mode == 'off':
        _LOG.warning('GATE_OFF gate=%s (OMNI_GATE_%s): this app build is NOT checked by %s', GATE, GATE, GATE)
        return mode
    _LOG.info('GATE_ON gate=%s mode=%s reason=%s', GATE, mode, why)
    core.executor = core.app_states_check = AppStatesExecutor(core.executor, mode)
    return mode


def with_rule(spec):
    """The spec with the APP-STATES requirement in it, added once. Deterministic, no model."""
    from .product_spec import ProductSpec
    data = spec.to_dict()
    if any(r['id'] == REQUIREMENT for r in data['requirements']):
        return spec
    data['requirements'].append({'id': REQUIREMENT, 'text': RULE, 'kind': 'quality', 'mandatory': False})
    return ProductSpec.from_dict(data)


class AppStatesArchitect:
    """Wraps the engine's architect: every spec of an app build tells the generator the three states and the error
    contract before it writes (a check the generator learns about only by failing it costs a repair round)."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def create_spec(self, prompt, *args, **kwargs):
        return with_rule(self._inner.create_spec(prompt, *args, **kwargs))


def carry_rule(engine) -> bool:
    """On an installed app build, give the generator the rule through the spec. False (and said) otherwise."""
    core = getattr(engine, 'core', engine)
    decision = getattr(core, 'app_states_decision', None)
    if not (isinstance(decision, dict) and decision.get('applies')) or not isinstance(
            getattr(core, 'app_states_check', None), AppStatesExecutor):
        core.app_states_rule_carried = False
        return False
    carried = False
    for holder in (core, engine):
        architect = getattr(holder, 'architect', None)
        if architect is not None and not isinstance(architect, AppStatesArchitect):
            holder.architect = AppStatesArchitect(architect)
        carried = carried or isinstance(getattr(holder, 'architect', None), AppStatesArchitect)
    core.app_states_rule_carried = carried
    if carried:
        _LOG.info('APP_STATES_RULE carried=True')
    else:
        _LOG.warning('APP_STATES_RULE_NOT_CARRIED: the engine has no architect; the generator is not told the states')
    return carried


def report(engine) -> dict:
    """For the build evidence ('app_states'): the decision with its reason, the mode, and the last check."""
    core = getattr(engine, 'core', engine)
    decision = getattr(core, 'app_states_decision', None)
    decision = decision if isinstance(decision, dict) else {}
    modes = getattr(core, 'gate_modes', None)
    checker = getattr(core, 'app_states_check', None)
    carried = getattr(core, 'app_states_rule_carried', None)
    return {'gate': GATE, 'applies': decision.get('applies'), 'why': decision.get('why'),
            'mode': modes.get(GATE) if isinstance(modes, dict) else None,
            'rule_carried': carried if isinstance(carried, bool) else None,
            'last': checker.last_check if isinstance(checker, AppStatesExecutor) else None}
