"""The source of every asset on a page: fonts, images, audio and video (the owner, 2026-11-16; plan G5 / A7).

"Checks the source of every asset: font, image, audio. Blocks on an unknown right -- it does not assume."

Two parts, both deterministic and static (no browser, no model, no network):

- `inventory(html)`: every asset reference a page carries -- tags, CSS url(), @font-face, external stylesheets, and
  any address ending in a font / image / audio / video extension anywhere in the page, scripts included.
- `judge(asset)`: the known source of one reference, or None with the reason. A source is known only when
  omni_prod/rights_sources.json lists it with its basis. Nothing else is known: an address on another host, a file
  the build cannot contain, bytes the platform did not supply.

The page is read AS WRITTEN: the platform's own assets appear as their 148ai-asset:// placeholders (the engine's
transform replaces them with the verified bytes before the sandbox runs; the gate reads the page with them put back).
So a raster data: URI on the page as written is bytes the platform did not supply.

What this does not read (said, not assumed): a font NAMED in font-family without being loaded (a system font, not
distributed by the page); an address built at run time by a script; what an external script loads; whether a drawing
copies a protected mark.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

DATA = Path(__file__).with_name('rights_sources.json')
KINDS = ('font', 'image', 'media')
ENTRY_KEYS = ('kinds', 'match', 'right', 'basis', 'read_on', 'legal_review')
MATCH_KEYS = ('hosts', 'marker_prefix', 'authored')
_LABEL = {'font': 'a font', 'image': 'an image', 'media': 'audio or video'}
MAX_ASSETS = 500                      # a page is bounded; past this the inventory stops and says so

FONT_EXT = ('.woff2', '.woff', '.ttf', '.otf', '.eot')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.bmp', '.ico', '.svg')
MEDIA_EXT = ('.mp3', '.wav', '.ogg', '.oga', '.m4a', '.aac', '.flac', '.opus', '.mp4', '.webm', '.mov', '.m4v', '.ogv')
# a player embedded from another site plays media whose right the page cannot show
MEDIA_EMBED_HOSTS = ('youtube.com', 'youtube-nocookie.com', 'youtu.be', 'vimeo.com', 'soundcloud.com', 'spotify.com')


class RightsSourceError(ValueError):
    """The registry is not usable. Raised loudly: a broken registry must never read as 'everything is unknown'."""


def check(data: dict) -> dict:
    """Every entry has every field, a kind this module knows, and a match this module can read. Otherwise raise."""
    sources = data.get('sources') if isinstance(data, dict) else None
    if not isinstance(sources, dict) or not sources:
        raise RightsSourceError('rights_sources.json has no sources')
    for sid, entry in sources.items():
        missing = [k for k in ENTRY_KEYS if not entry.get(k)]
        if missing:
            raise RightsSourceError(f'source {sid!r} lacks {missing}: a source without its basis is not known')
        bad = [k for k in entry['kinds'] if k not in KINDS]
        if bad:
            raise RightsSourceError(f'source {sid!r}: unknown kind {bad}; one of {KINDS}')
        unknown = [k for k in entry['match'] if k not in MATCH_KEYS]
        if unknown or not any(entry['match'].get(k) for k in MATCH_KEYS):
            raise RightsSourceError(f'source {sid!r}: match must use {MATCH_KEYS}, got {sorted(entry["match"])}')
    return data


_CACHE: dict | None = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = check(json.loads(DATA.read_text(encoding='utf-8')))
    return _CACHE


# ---- the inventory ----------------------------------------------------------------------------------------------

_TAG = re.compile(r'<([a-zA-Z][\w-]*)\b([^>]*)>', re.S)
_ATTR = re.compile(r'([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'>]+)))?')
_COMMENT = re.compile(r'<!--.*?-->', re.S)
_CSS_URL = re.compile(r'url\(\s*(["\']?)([^"\')]+)\1\s*\)', re.I)
_FONT_FACE = re.compile(r'@font-face\s*\{([^}]*)\}', re.I | re.S)
_IMPORT = re.compile(r'@import\s+(?:url\(\s*)?["\']?([^"\')\s;]+)', re.I)
_EXTS = '|'.join(e[1:] for e in FONT_EXT + IMAGE_EXT + MEDIA_EXT)
# an address ending in a known extension, anywhere: absolute, protocol-relative or a quoted relative path
_ANYWHERE = re.compile(r'(?:(?:https?:)?//[^\s"\'<>()`\\]+|(?<=["\'`(])[^\s"\'<>()`\\]+)\.(?:' + _EXTS + r')(?:\?[^\s"\'<>()`\\]*)?'
                       r'(?=["\'`)\s]|$)', re.I)
_NEW_AUDIO = re.compile(r'\bnew\s+Audio\s*\(\s*(["\'`]?)([^"\'`)]*)\1', re.I)
_DYNAMIC = re.compile(r'\$\{|\{\{|\{%|<%')


def _attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in _ATTR.finditer(raw or ''):
        out[m.group(1).lower()] = next((g for g in m.groups()[1:] if g is not None), '')
    return out


def _kind_by_ext(ref: str) -> str | None:
    path = ref.split('?', 1)[0].split('#', 1)[0].lower()
    if path.startswith('data:'):
        mime = path[5:].split(';', 1)[0].split(',', 1)[0]
        if mime.startswith('image/'):
            return 'image'
        if mime.startswith(('audio/', 'video/')):
            return 'media'
        if mime.startswith('font/') or 'font' in mime:
            return 'font'
        return None
    if path.endswith(FONT_EXT):
        return 'font'
    if path.endswith(IMAGE_EXT):
        return 'image'
    if path.endswith(MEDIA_EXT):
        return 'media'
    return None


def _host(ref: str) -> str:
    if ref.startswith('//'):
        ref = 'https:' + ref
    return (urlsplit(ref).hostname or '').lower() if re.match(r'https?://', ref, re.I) else ''


def inventory(html: str) -> list[dict]:
    """[{kind, ref, where}] for every asset reference of the page, in page order, each (kind, ref) once.
    `kind` is font / image / media; `where` says how the page uses it. Bounded at MAX_ASSETS."""
    page = _COMMENT.sub(' ', html or '')
    found: dict[tuple[str, str], dict] = {}

    def add(kind, ref, where):
        ref = (ref or '').strip()
        if not ref or ref.startswith(('#', 'javascript:', 'blob:', 'about:', 'mailto:', 'tel:')) or _DYNAMIC.search(ref):
            return
        if len(found) < MAX_ASSETS:
            found.setdefault((kind, ref), {'kind': kind, 'ref': ref, 'where': where})

    in_media = False
    for m in _TAG.finditer(page):
        tag, a = m.group(1).lower(), _attrs(m.group(2))
        rel = a.get('rel', '').lower().split()
        if tag == 'picture':
            in_media = False
        if tag == 'img' or (tag == 'input' and a.get('type', '').lower() == 'image'):
            add('image', a.get('src'), f'<{tag} src>')
            for part in a.get('srcset', '').split(','):
                add('image', part.strip().split(' ')[0], f'<{tag} srcset>')
        elif tag == 'image':                                               # inside an inline SVG
            add('image', a.get('href') or a.get('xlink:href'), '<image href>')
        elif tag in ('audio', 'video'):
            in_media = True
            add('media', a.get('src'), f'<{tag} src>')
            add('image', a.get('poster'), '<video poster>')
        elif tag == 'source':
            for part in a.get('srcset', '').split(','):
                add('image', part.strip().split(' ')[0], '<source srcset>')
            src = a.get('src')
            if src:
                add(_kind_by_ext(src) or ('media' if in_media else 'image'), src, '<source src>')
        elif tag in ('embed', 'object'):
            ref = a.get('src') or a.get('data')
            if ref and _kind_by_ext(ref):
                add(_kind_by_ext(ref), ref, f'<{tag}>')
        elif tag == 'iframe':
            host = _host(a.get('src', ''))
            if any(host == h or host.endswith('.' + h) for h in MEDIA_EMBED_HOSTS):
                add('media', a.get('src'), '<iframe> player')
        elif tag == 'link':
            href = a.get('href', '')
            if 'stylesheet' in rel and _host(href):
                add('font', href, 'external stylesheet (it can load fonts)')
            elif 'preload' in rel and a.get('as', '').lower() in ('font', 'image', 'audio', 'video'):
                add({'font': 'font', 'image': 'image'}.get(a['as'].lower(), 'media'), href, '<link rel=preload>')
            elif any(r in rel for r in ('icon', 'apple-touch-icon', 'mask-icon')):
                add('image', href, '<link rel=icon>')
        elif tag == 'meta' and a.get('property', a.get('name', '')).lower() in ('og:image', 'twitter:image'):
            add('image', a.get('content'), '<meta og:image>')
    for body in _FONT_FACE.findall(page):
        for _, ref in _CSS_URL.findall(body):
            add('font', ref, '@font-face src')
    for ref in _IMPORT.findall(page):
        if _host(ref):
            add('font', ref, '@import stylesheet (it can load fonts)')
    for _, ref in _CSS_URL.findall(page):
        kind = _kind_by_ext(ref)
        if kind != 'font' and ('font', ref.strip()) not in found:           # a font url() was read with its @font-face
            add(kind or 'image', ref, 'CSS url()')
    for _, ref in _NEW_AUDIO.findall(page):
        add('media', ref or 'new Audio(...)', 'new Audio()')
    for m in _ANYWHERE.finditer(page):
        ref = m.group(0)
        kind = _kind_by_ext(ref)
        if kind and not any(r == ref for (_, r) in found):
            add(kind, ref, 'an address in the page')
    return list(found.values())


# ---- the judgement ----------------------------------------------------------------------------------------------

def shown(ref: str) -> str:
    """The reference as a finding shows it: never a page of base64."""
    if ref.startswith('data:'):
        return ref.split(',', 1)[0][:60] + f',… ({len(ref)} characters)'
    return ref if len(ref) <= 160 else ref[:157] + '...'


def judge(asset: dict) -> tuple[str | None, str]:
    """(source id, its right) when the source is known; (None, why it is not) otherwise."""
    kind, ref = asset['kind'], asset['ref']
    low = ref.lower()
    sources = load()['sources']
    for sid, entry in sources.items():
        if kind not in entry['kinds']:
            continue
        match = entry['match']
        if any(ref.startswith(p) for p in match.get('marker_prefix', ())):
            return sid, entry['right']
        host = _host(ref)
        if host and host in match.get('hosts', ()):
            return sid, entry['right']
        if 'svg' in match.get('authored', ()) and (
                low.startswith('data:image/svg+xml') or
                (not host and not low.startswith(('data:', '148ai-asset:')) and low.split('?', 1)[0].endswith('.svg'))):
            return sid, entry['right']
    if low.startswith('148ai-asset:'):
        return None, 'a 148ai-asset:// address of a kind the platform does not supply'
    if low.startswith('data:'):
        return None, 'bytes embedded in the page that the platform did not supply'
    host = _host(ref)
    if host:
        return None, f'{host} is not a known source for {_LABEL[kind]}'
    return None, 'a file the build cannot contain (the generated repository is text only)'


def unknown(html: str, kind: str) -> list[dict]:
    """The findings of one kind: every asset of that kind whose source is not known."""
    if kind not in KINDS:
        raise ValueError(f'unknown asset kind {kind!r}; one of {KINDS}')
    out = []
    for asset in inventory(html):
        if asset['kind'] != kind:
            continue
        source, why = judge(asset)
        if source is None:
            out.append({'where': f"{asset['where']}: {shown(asset['ref'])}", 'why': why})
    return out


def ledger(html: str) -> list[dict]:
    """Every asset of the page with its source (or None) -- what A7 writes into the build evidence."""
    out = []
    for asset in inventory(html):
        source, note = judge(asset)
        out.append({'kind': asset['kind'], 'ref': shown(asset['ref']), 'where': asset['where'], 'source': source,
                    'note': note})
    return out
