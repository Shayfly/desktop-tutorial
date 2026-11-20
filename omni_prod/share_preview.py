"""A shared link shows a preview, by construction (the owner's builds, 2026-11-19).

SHARE (og:title, og:description) failed on all five production builds that carry gate evidence, and on the owner's
law-firm build after #467 put the rule in the spec: telling the model is not enough. Like the RTL rule (page_locale),
the platform writes it: after generation and after every repair, a served page that has a <title> but no og:title gets
one from that title, and one with no og:description gets it from its meta description, or else from its first
paragraph. Nothing is invented: a page with no title, or no description and no paragraph, is left to the SHARE gate.

A page in a Python file (a template string) is changed only if the file still compiles afterwards; otherwise it is
left exactly as written. Tests are never touched (the same pattern as the gates' served files)."""
from __future__ import annotations

import html
import re

from .skill_units import tags

_TITLE = re.compile(r'<title\b[^>]*>(.*?)</title\s*>', re.I | re.S)
_P = re.compile(r'<p\b[^>]*>(.*?)</p\s*>', re.I | re.S)
_TAG = re.compile(r'<[^>]+>')
_TEST_FILE = re.compile(r'(?:^|/)(?:tests?/|test_[^/]*\.py$)|\.test\.[a-z]+$', re.I)
DESCRIPTION_MAX = 160


def _text(fragment: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(_TAG.sub(' ', fragment))).strip()


def _metas(page: str) -> dict:
    out = {}
    for _, t, a in tags(page):
        if t == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            out.setdefault(key, (a.get('content') or '').strip())
    return out


def _short(text: str) -> str:
    if len(text) <= DESCRIPTION_MAX:
        return text
    cut = text[:DESCRIPTION_MAX - 1].rsplit(' ', 1)[0]
    return cut + '…'


def share_tags(page: str) -> str:
    """The og tags this page lacks, as HTML ('' when it has them or there is nothing true to write)."""
    m = _TITLE.search(page)
    if not m:
        return ''
    metas = _metas(page)
    add = []
    title = _text(m.group(1))
    if title and not metas.get('og:title'):
        add.append(f'<meta property="og:title" content="{html.escape(title, quote=True)}">')
    if not metas.get('og:description'):
        desc = metas.get('description') or ''
        if not desc:
            p = next((t for t in (_text(x) for x in _P.findall(page)) if t), '')
            desc = _short(p)
        if desc:
            add.append(f'<meta property="og:description" content="{html.escape(desc, quote=True)}">')
    if add and not metas.get('og:type'):
        add.append('<meta property="og:type" content="website">')
    return ''.join(add)


def ensure_share(repo: dict) -> dict:
    out = dict(repo)
    for path, text in repo.items():
        if not isinstance(text, str) or _TEST_FILE.search(path):
            continue
        is_html = path.lower().endswith(('.html', '.htm'))
        if not (is_html or path.endswith('.py')):
            continue
        m = _TITLE.search(text)
        if not m:
            continue
        add = share_tags(text)
        if not add:
            continue
        new = text[:m.end()] + add + text[m.end():]
        if not is_html:
            try:
                compile(new, path, 'exec')
            except SyntaxError:
                continue                                  # the template string cannot take it: left as written
        out[path] = new
    return out


class _Chained:
    """Runs the transform already installed (logo, images, RTL), then the share rule; keeps its attributes."""

    def __init__(self, inner):
        self._inner = inner

    def __call__(self, repo):
        return ensure_share(self._inner(repo) if self._inner is not None else repo)

    def __getattr__(self, name):
        if self._inner is None:
            raise AttributeError(name)
        return getattr(self._inner, name)


def install(engine) -> None:
    core = getattr(engine, 'core', engine)
    core.repository_transform = _Chained(getattr(core, 'repository_transform', None))
