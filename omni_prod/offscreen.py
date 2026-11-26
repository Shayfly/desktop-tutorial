"""An element parked far off-screen on the side the page scrolls to (bld_cb2d1b90a90f430c98603d14f8afa1a8, 2026-11-24).

The owner's build failed the layout check in every round with "page width 11439px > viewport 1440px" and, on the phone,
"page width 10389px > viewport 1560px" plus "no meta viewport". Those three numbers are exactly what Chromium gives for
one element at `position:absolute; left:-9999px` on a right-to-left page WITH a meta viewport (measured 2026-11-26 with
the platform's visual QA settings): 1440 + 9999, 390 + 9999, and a phone zoomed out to 4 x 390. The idiom hides an
element harmlessly on a left-to-right page, where the left side does not scroll; on a right-to-left page the page
scrolls to the left, so it grows by 9999px. Measured in the same run: left / margin-left on an RTL page and right /
margin-right on an LTR page grow the page; text-indent grows it when the element's own direction is LTR (an English
label on a Hebrew page); a fixed element, one inside an overflow:hidden box, a 0x0 box and the clip rule below do not.

Three parts, all deterministic (no model):
  * scan()     -- the static check (consistency_gate 'offscreen'): on a dir=rtl page no left / margin-left /
                  text-indent of -999px or beyond, on a left-to-right page no right of -999px or beyond (a rule that
                  is position:fixed does not scroll the page and is not reported);
  * rewrite()  -- the automatic repair, run as a repository transform after generation and after every repair (like
                  page_locale), for the hiding idiom itself: a position:absolute rule moved off-screen by left /
                  margin-left (RTL) or right (LTR) loses that declaration, and its elements get the platform's ONE
                  visually-hidden rule below, scoped to :not(:focus):not(:focus-within) so a skip link still shows when
                  focused. Anything else -- an inline style, a selector this does not read, text-indent, a margin that
                  may stretch a visible band, a Python file that would not compile -- is left exactly as written, and
                  the consistency gate blocks it with file:line and the fix;
  * VISUALLY_HIDDEN -- the same rule, in the generator's guidance (skills_runtime ACCESSIBILITY).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

HIDE = ('position:absolute!important;width:1px!important;height:1px!important;padding:0!important;'
        'margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;clip-path:inset(50%)!important;'
        'white-space:nowrap!important;border:0!important')
# The platform's one visually-hidden rule: hidden from the eye, read by screen readers, shown again when focused.
VISUALLY_HIDDEN = '.visually-hidden:not(:focus):not(:focus-within){' + HIDE + '}'
FOCUS_SCOPE = ':not(:focus):not(:focus-within)'
LIMIT_PX = -999                      # this far or further off-screen is the hiding idiom, not a layout offset
PROPS = {'rtl': ('left', 'margin-left', 'text-indent'), 'ltr': ('right',)}
REWRITTEN = {'rtl': ('left', 'margin-left'), 'ltr': ('right',)}

_DECL = re.compile(r'(?<![\w-])(left|margin-left|text-indent|right)\s*:\s*(-\d+(?:\.\d+)?)px(\s*!important)?\s*;?', re.I)
_COMMENT = re.compile(r'/\*.*?\*/', re.S)
_HTML_TAG = re.compile(r'<html\b([^>]*)>', re.I)
_BODY_TAG = re.compile(r'<body\b([^>]*)>', re.I)
_DIR = re.compile(r'''\bdir\s*=\s*['"]?\s*(rtl|ltr)\b''', re.I)
_POSITION = re.compile(r'(?<![\w-])position\s*:\s*(absolute|fixed)\b', re.I)
_TEST = re.compile(r'(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec)\.[jt]sx?$')
_SELECTOR = re.compile(r'^[\w\s.#:>+~*\[\]="\'^$|-]+(,[\w\s.#:>+~*\[\]="\'^$|-]+)*$')
_PAGE_SUFFIXES = ('.html', '.htm')
_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.jsx', '.ts', '.tsx')
MAX_REWRITES_PER_FILE = 50


@dataclass(frozen=True)
class Offscreen:
    path: str
    line: int
    prop: str
    value: float
    direction: str

    def message(self) -> str:
        page, side = ('right-to-left', 'left') if self.direction == 'rtl' else ('left-to-right', 'right')
        return (f'on a {page} page "{self.prop}: {self.value:g}px" moves an element {abs(self.value):g}px to the '
                f'{side}, the side the page scrolls to: the page becomes about {abs(self.value):g}px wider and a phone '
                f'shows it zoomed out')


FIX = ('to hide it, use the platform\'s visually-hidden rule (never off-screen, and a focused skip link still shows): '
       + VISUALLY_HIDDEN + ' -- to stretch a band to the edge, use a full-width wrapper, not a negative offset')


def _blank_comments(text: str) -> str:
    return _COMMENT.sub(lambda m: ' ' * len(m.group(0)), text)


def page_direction(text: str) -> str | None:
    """'rtl' or 'ltr' for a file that holds an <html> page (its <html> dir, else its <body> dir, else ltr); None when
    the file holds no page."""
    m = _HTML_TAG.search(text)
    if m is None:
        return None
    d = _DIR.search(m.group(1))
    if d is None:
        body = _BODY_TAG.search(text)
        d = _DIR.search(body.group(1)) if body else None
    return d.group(1).lower() if d else 'ltr'


def _targets(repo: dict):
    """(path, text, directions) for every file whose CSS a page uses: a page file with its own direction; a .css file
    or a file with a <style> block (a partial) with the directions of the repository's pages."""
    pages = {}
    for path, text in repo.items():
        if isinstance(text, str) and not _TEST.search(path) and path.lower().endswith(_PAGE_SUFFIXES + _CODE_SUFFIXES):
            d = page_direction(text)
            if d is not None:
                pages[path] = d
    all_dirs = set(pages.values())
    for path, text in sorted(repo.items()):
        if not isinstance(text, str) or _TEST.search(path):
            continue
        if path in pages:
            yield path, text, {pages[path]}
        elif all_dirs and (path.lower().endswith('.css') or
                           (path.lower().endswith(_PAGE_SUFFIXES + _CODE_SUFFIXES) and '<style' in text.lower())):
            yield path, text, all_dirs


def _rule_around(text: str, start: int, end: int):
    """(selector_start, head, close, doubled) of the CSS rule whose body holds text[start:end] -- head is where its
    opening brace starts, close where its closing brace starts -- or None when the declaration is not inside a rule
    this can read (an inline style attribute, markup in between, a selector continued from an earlier line)."""
    opening = text.rfind('{', 0, start)
    if opening < 0 or text.rfind('}', 0, start) > opening or '<' in text[opening:start] or '>' in text[opening:start]:
        return None
    doubled = opening > 0 and text[opening - 1] == '{'          # a Python format string: braces are written twice
    close = text.find('}', end)
    if close < 0 or '<' in text[end:close] or '{' in text[end:close]:
        return None
    if doubled and text[close + 1:close + 2] != '}':
        return None
    head = opening - 1 if doubled else opening
    cut = max(text.rfind(c, 0, head) for c in '}{>"\'\n')
    if cut >= 0 and text[cut] == '\n' and text[:cut].rstrip().endswith(','):
        return None
    return cut + 1, head, close, doubled


def _offending(text: str, directions: set):
    """(match, prop, value, direction, rule) of every declaration that moves something 999px or more to the side the
    page scrolls to. rule is _rule_around()'s answer (None outside a readable rule)."""
    clean = _blank_comments(text)
    for m in _DECL.finditer(clean):
        prop, value = m.group(1).lower(), float(m.group(2))
        if value > LIMIT_PX:
            continue
        d = next((d for d in sorted(directions) if prop in PROPS[d]), None)
        if d is None:
            continue
        rule = _rule_around(clean, m.start(), m.end())
        body = clean[rule[1]:rule[2]] if rule else ''
        if any(p.group(1).lower() == 'fixed' for p in _POSITION.finditer(body)):
            continue                                            # a fixed box does not scroll the page (measured)
        yield m, prop, value, d, rule


def scan(repo: dict) -> list[Offscreen]:
    out = []
    for path, text, directions in _targets(repo):
        for m, prop, value, d, _ in _offending(text, directions):
            out.append(Offscreen(path, text.count('\n', 0, m.start()) + 1, prop, value, d))
    return out


def _rewrite_one(text: str, hit) -> str | None:
    m, prop, value, d, rule = hit
    if rule is None or prop not in REWRITTEN[d]:
        return None
    sel_start, head, close, doubled = rule
    clean = _blank_comments(text)
    if not any(p.group(1).lower() == 'absolute' for p in _POSITION.finditer(clean[head:close])):
        return None                                             # not the hiding idiom: a band, an offset -- the gate
    selector = ' '.join(clean[sel_start:head].split())
    if not selector or '(' in selector or '@' in selector or not _SELECTOR.match(selector):
        return None
    o, c = ('{{', '}}') if doubled else ('{', '}')
    scoped = ','.join(s.strip() + FOCUS_SCOPE for s in selector.split(','))
    end_of_rule = close + (2 if doubled else 1)
    return text[:m.start()] + text[m.end():end_of_rule] + f'{scoped}{o}{HIDE}{c}' + text[end_of_rule:]


def rewrite(repo: dict) -> tuple[dict, list[str]]:
    """(repository, ['path:line prop value', ...] rewritten). Each hiding-idiom declaration is removed and its rule's
    elements get the visually-hidden rule; a Python file must still compile, else it is left exactly as written."""
    out, done = dict(repo), []
    for path, text, directions in list(_targets(repo)):
        new, changed = text, []
        while True:
            hit = next((h for h in _offending(new, directions) if _rewrite_one(new, h) is not None), None)
            if hit is None:
                break
            if len(changed) >= MAX_REWRITES_PER_FILE:
                raise RuntimeError(f'offscreen.rewrite: more than {MAX_REWRITES_PER_FILE} rewrites in {path}')
            changed.append(f'{path}:{new.count(chr(10), 0, hit[0].start()) + 1} {hit[1]} {hit[2]:g}px')
            new = _rewrite_one(new, hit)
        if not changed:
            continue
        if path.endswith('.py'):
            try:
                compile(new, path, 'exec')
            except SyntaxError:
                continue
        out[path] = new
        done.extend(changed)
    return out, done


class _Chained:
    """Runs the transform already installed (logo, images, RTL, share tags), then this rule; keeps its attributes."""

    def __init__(self, inner):
        self._inner = inner
        self.rewritten: list[str] = []

    def __call__(self, repo):
        repo, done = rewrite(self._inner(repo) if self._inner is not None else repo)
        if done:                                    # a platform edit of generated code is said, never silent
            import logging
            logging.getLogger(__name__).info('OFFSCREEN_REWRITTEN %s', '; '.join(done)[:600])
        self.rewritten.extend(done)
        return repo

    def __getattr__(self, name):
        if name.startswith('__') or self._inner is None:
            raise AttributeError(name)
        return getattr(self._inner, name)


def install(engine) -> list[str]:
    """Chain the rewrite onto the engine's repository transform. Returns the list the transform appends every rewrite
    to ('path:line prop value'), also kept on the engine as offscreen_rewrites for the build's evidence."""
    core = getattr(engine, 'core', engine)
    transform = _Chained(getattr(core, 'repository_transform', None))
    core.repository_transform = transform
    core.offscreen_rewrites = transform.rewritten
    return transform.rewritten
