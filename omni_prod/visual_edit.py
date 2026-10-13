"""Visual edit: from a selected element (or a marked screenshot region) to a
focused change through the EXISTING modification pipeline.

Founder directive 2026-10-11, task 3. No new build engine:
  selection (preview inspector, postMessage) --> locate() in the stored version
  --> UNIQUE: compose a targeted instruction --> POST .../modifications
      (classifier -> candidate -> verification -> accept/reject -> version)
  --> AMBIGUOUS / NOT_FOUND: ask the person; never change a guessed element.

locate() is deterministic and free: it searches the exact stored repository of
the version shown in the preview for the element's strongest anchors (id, test
id, name/aria-label/placeholder, visible text, class list).
"""
from __future__ import annotations

import html
import re

ATTR_KEYS = ('name', 'type', 'href', 'src', 'placeholder', 'aria-label', 'data-testid', 'role', 'title', 'alt', 'for')
SOURCE_EXT = ('.html', '.htm', '.jinja', '.jinja2', '.j2', '.jsx', '.tsx', '.js', '.ts', '.vue', '.svelte', '.py', '.mjs')
SKIP_DIRS = ('node_modules/', '.omni/', 'dist/', 'build/', '.git/', 'vendor/', 'static/vendor/')
MAX_FILE = 400_000
MAX_CANDIDATES = 6


class SelectionInvalid(ValueError):
    pass


def _s(v, n) -> str:
    return ' '.join(str(v or '').split())[:n]


def clean_selection(raw) -> dict:
    """The inspector runs inside the generated app (untrusted page): accept only
    a small, typed description and bound every field."""
    if not isinstance(raw, dict):
        raise SelectionInvalid('selection must be an object')
    tag = str(raw.get('tag') or '').lower()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', tag):
        raise SelectionInvalid('selection.tag is invalid')
    el_id = _s(raw.get('id'), 120)
    if el_id and not re.fullmatch(r'[A-Za-z_][\w:.-]{0,119}', el_id):
        el_id = ''
    classes = [c for c in (raw.get('classes') or [])[:8] if isinstance(c, str) and re.fullmatch(r'[A-Za-z_-][\w-]{0,60}', c)]
    attrs = {}
    for k, v in (raw.get('attrs') or {}).items() if isinstance(raw.get('attrs'), dict) else ():
        if k in ATTR_KEYS and isinstance(v, str) and v.strip():
            attrs[k] = _s(v, 200)
    rect = raw.get('rect') if isinstance(raw.get('rect'), dict) else {}
    try:
        rect = {k: round(float(rect.get(k, 0)), 1) for k in ('x', 'y', 'w', 'h')}
    except (TypeError, ValueError):
        rect = {}
    return {'tag': tag, 'id': el_id, 'classes': classes, 'attrs': attrs, 'text': _s(raw.get('text'), 160),
            'path': _s(raw.get('path'), 300), 'html': str(raw.get('html') or '')[:400], 'rect': rect,
            'page': _s(raw.get('page'), 200)}


def _source_files(repository: dict) -> list[tuple[str, list[str]]]:
    out = []
    for path, content in sorted(repository.items()):
        p = path.lower()
        if not p.endswith(SOURCE_EXT) or any(p.startswith(d) or f'/{d}' in p for d in SKIP_DIRS):
            continue
        if not isinstance(content, str) or len(content) > MAX_FILE:
            continue
        if p.endswith(('.min.js', '.bundle.js')):
            continue
        out.append((path, content.splitlines()))
    return out


def _find(files, pattern: re.Pattern, cols: dict | None = None) -> set[tuple[str, int]]:
    hits = set()
    for path, lines in files:
        for i, line in enumerate(lines, 1):
            m = pattern.search(line)
            if m:
                hits.add((path, i))
                if cols is not None:
                    cols.setdefault((path, i), m.start())
    return hits


_OPEN_TAG = re.compile(r'<\s*([A-Za-z][\w-]*)')


def _enclosing_tag(lines: list[str], line_no: int, col: int) -> str | None:
    """The last opening tag before the anchor (same line first, then up to two lines above)."""
    before = lines[line_no - 1][:col]
    for text in [before] + [lines[i] for i in range(line_no - 2, max(-1, line_no - 4), -1)]:
        tags = _OPEN_TAG.findall(text)
        if tags:
            return tags[-1].lower()
    return None


def _anchors(sel: dict) -> list[tuple[str, re.Pattern]]:
    q = re.escape
    out = []
    if sel['id']:
        out.append(('id', re.compile(r'''\bid\s*=\s*\{?\s*["'`]''' + q(sel['id']) + r'''["'`]''')))
    for key in ('data-testid', 'name', 'aria-label', 'placeholder', 'for', 'title', 'alt'):
        v = sel['attrs'].get(key)
        if v:
            out.append((key, re.compile(r'''\b''' + q(key) + r'''\s*=\s*\{?\s*["'`]''' + q(v) + r'''["'`]''')))
    text = sel['text']
    if 2 <= len(text) <= 120:
        variants = {text, html.escape(text, quote=False)}
        out.append(('text', re.compile('|'.join(q(v) for v in sorted(variants)))))
    href = sel['attrs'].get('href')
    if href and len(href) < 150:
        out.append(('href', re.compile(r'''\bhref\s*=\s*["'`]''' + q(href) + r'''["'`]''')))
    if sel['classes']:
        cls = sel['classes'][:4]
        out.append(('classes', re.compile(r'class(Name)?\s*=\s*\{?\s*["\'`][^"\'`]*' +
                                          ''.join(f'(?=[^"\'`]*\\b{q(c)}\\b)' for c in cls))))
    return out


def _near(a: tuple[str, int], hits: set[tuple[str, int]], span: int = 3) -> bool:
    return any(f == a[0] and abs(l - a[1]) <= span for f, l in hits)


def locate(repository: dict, selection: dict) -> dict:
    """{'status': UNIQUE|AMBIGUOUS|NOT_FOUND, 'candidates': [...], 'anchor': str}"""
    sel = clean_selection(selection)
    files = _source_files(repository)
    cols: dict = {}
    by_anchor = [(name, _find(files, pat, cols)) for name, pat in _anchors(sel)]
    by_anchor = [(n, h) for n, h in by_anchor if h]
    if not by_anchor:
        return {'status': 'NOT_FOUND', 'candidates': [], 'anchor': None, 'selection': sel}
    # Strongest anchor first; narrow its hits with every other anchor that
    # points at the same place (same file, within 3 lines).
    first_name, hits = by_anchor[0]
    used = [first_name]
    for name, other in by_anchor[1:]:
        if len(hits) <= 1:
            break
        narrowed = {h for h in hits if _near(h, other)}
        if narrowed:
            hits, used = narrowed, used + [name]
    lines_of = dict(files)

    def tagged(h):
        f, l = h
        return _enclosing_tag(lines_of[f], l, cols.get(h, len(lines_of[f][l - 1]))) == sel['tag']
    if len(hits) > 1:
        with_tag = {h for h in hits if tagged(h)}
        if with_tag and len(with_tag) < len(hits):
            hits, used = with_tag, used + ['tag']
    cands = []
    for f, l in sorted(hits)[:MAX_CANDIDATES]:
        lines = lines_of[f]
        lo, hi = max(1, l - 2), min(len(lines), l + 2)
        cands.append({'file': f, 'line': l, 'snippet': '\n'.join(lines[lo - 1:hi])[:600], 'tag_match': tagged((f, l)),
                      'context': _context(lines, l), 'page': f.rsplit('/', 1)[-1].rsplit('.', 1)[0]})
    status = 'UNIQUE' if len(hits) == 1 else 'AMBIGUOUS'
    return {'status': status, 'candidates': cands, 'anchor': '+'.join(used), 'total': len(hits), 'selection': sel}


_HEADING = re.compile(r'<(h[1-6]|legend|label|title)\b[^>]*>(.*?)</\1\s*>', re.I | re.S)
_TAGS = re.compile(r'<[^>]+>')


def _context(lines: list[str], line_no: int) -> str:
    """The nearest heading above the element, in words a customer recognises."""
    text = '\n'.join(lines[max(0, line_no - 40):line_no])
    found = [m for m in _HEADING.finditer(text)]
    for m in reversed(found):
        words = ' '.join(html.unescape(_TAGS.sub(' ', m.group(2))).split())
        if 1 < len(words) <= 80:
            return words
    return ''


def choose(located: dict, chosen: dict | None) -> dict:
    """The candidate a change may target: the unique one, or the one the person
    picked from the listed candidates. Anything else is refused (no guessing)."""
    cands = located.get('candidates') or []
    if chosen:
        for c in cands:
            if c['file'] == chosen.get('file') and int(c['line']) == int(chosen.get('line', -1)):
                return c
        raise SelectionInvalid('the chosen element is not one of the located candidates')
    if located.get('status') == 'UNIQUE' and len(cands) == 1:
        return cands[0]
    raise SelectionInvalid('the selection does not identify one element; pick a candidate or describe it')


def describe(sel: dict) -> str:
    bits = [f'<{sel["tag"]}']
    if sel['id']:
        bits.append(f'id="{sel["id"]}"')
    if sel['classes']:
        bits.append(f'class="{" ".join(sel["classes"])}"')
    for k in ('name', 'aria-label', 'placeholder', 'type'):
        if sel['attrs'].get(k):
            bits.append(f'{k}="{sel["attrs"][k]}"')
    out = ' '.join(bits) + '>'
    if sel['text']:
        out += f' "{sel["text"]}"'
    return out


def compose_followup(instruction: str, *, target: dict | None, selection: dict | None,
                     attachments: list[dict] | None = None, region: dict | None = None) -> str:
    """The instruction the existing modification classifier/engine receives:
    the person's words first, then the exact location, then a scope rule."""
    instruction = (instruction or '').strip()
    parts = [instruction]
    if target and selection:
        parts.append('\n[Visual edit target — change only this element unless the instruction says otherwise]\n'
                     f'File: {target["file"]} (around line {target["line"]})\n'
                     f'Element: {describe(selection)}\n'
                     f'Current source:\n{target["snippet"]}\n'
                     + (f'Page: {selection["page"]}\n' if selection.get('page') else '')
                     + 'Keep every other part of the product unchanged.')
    if attachments:
        lines = []
        for a in attachments:
            regions = (a.get('annotation') or {}).get('regions') or []
            note = (a.get('annotation') or {}).get('note')
            lines.append(f'- {a["kind"]} {a["id"]} ({a["width"]}x{a["height"]})'
                         + (f'; marked regions (px): {regions}' if regions else '')
                         + (f'; note: {note}' if note else ''))
        parts.append('\n[Attached images — not analyzed automatically (no vision budget enabled); '
                     'rely on the text and the marked regions]\n' + '\n'.join(lines))
    if region and not target:
        parts.append(f'\n[Marked area on the preview screenshot: {region}]')
    return '\n'.join(parts)[:12000]
