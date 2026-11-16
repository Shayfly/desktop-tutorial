"""The source of every asset a build's files load: fonts, images, audio, video, embedded players (the owner,
2026-11-16; plan G5 / A7).

"Checks the source of every asset: font, image, audio. Blocks on an unknown right -- it does not assume."

Two parts, both deterministic and static (no browser, no model, no network):

- `inventory(text, path)`: every asset reference one served file carries.
- `judge(asset)`: the known source of one reference, or None with the reason. A source is known only when
  omni_prod/rights_sources.json lists it with its basis.

The files are read AS WRITTEN: the platform's own assets appear as their 148ai-asset:// placeholders (the engine's
transform replaces them with the verified bytes before the sandbox runs; the gate reads the files with them put
back). So raster bytes left in a file as written -- a data: URI, or a long base64 literal -- are bytes the platform
did not supply.

What is read (an independent review on 2026-11-16 found each of these missing in the first version):
- HTML with a real parser (html.parser): a '>' inside an attribute, a comment opener inside <style> or <script>, and
  entities do not hide a reference. Every attribute that LOADS something: src, srcset, poster, data, background,
  imagesrcset, lazy-loading data-* attributes, <link> (stylesheet, preload, icon), og/twitter image and media meta,
  SVG <image>/<use>/<feImage>, <object>/<embed>, and <iframe> on another host.
- CSS, in <style>, style="" and .css files: @import in every form, @font-face, url() quoted or not, CSS escapes, and
  any quoted address (the string arguments of image-set() and cross-fade()).
- Scripts, in <script>, on* handlers and .js files: an address with a font / image / audio / video extension always;
  and, when the script puts media on the page at all (it sets a src, builds an <img>, creates an Audio...), EVERY
  absolute address literal in it that is not plainly a link target -- extension or not. A photo service address has
  no extension.
- JSON-LD: the image and media properties.
- An SVG data: URI is decoded and read like a page: a photograph wrapped in an SVG is still a photograph.
- Python and template files: the pages inside them, and an address constant when the page takes addresses from
  variables or the code fetches over the network.
- A relative path is the build's own: the generated repository is text only, so what it serves is text it wrote, a
  platform placeholder, or embedded bytes -- and embedded bytes are judged on their own.

What a static reading cannot see (said, not assumed): an address a script BUILDS at run time from pieces; what an
external script loads; a font only NAMED in font-family (a system font, not loaded); whether a drawing copies a
protected mark. The real request list of the page in a browser is a different check and is not built.
"""
from __future__ import annotations

import base64
import io
import json
import re
import tokenize
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

DATA = Path(__file__).with_name('rights_sources.json')
KINDS = ('font', 'image', 'media', 'embed')
ENTRY_KEYS = ('kinds', 'match', 'right', 'basis', 'read_on', 'legal_review')
MATCH_KEYS = ('hosts', 'path_prefix', 'marker_prefix', 'authored', 'own')
_LABEL = {'font': 'a font', 'image': 'an image', 'media': 'audio or video', 'embed': 'an embedded frame'}
MAX_ASSETS = 500                      # one file is bounded; past this the file is NOT fully read, and that blocks
MAX_SVG_DEPTH = 2                     # an SVG data: URI inside an SVG data: URI inside ... is read this deep, no deeper
MIN_BLOB = 1024                       # a base64 literal this long in a served file is embedded bytes

FONT_EXT = ('.woff2', '.woff', '.ttf', '.otf', '.eot')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.bmp', '.ico', '.svg')
MEDIA_EXT = ('.mp3', '.wav', '.ogg', '.oga', '.m4a', '.aac', '.flac', '.opus', '.mp4', '.webm', '.mov', '.m4v', '.ogv')
# the files of a build that a browser loads or a server serves (the same set the asset-marker gate reads)
SERVED_EXT = ('.html', '.htm', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.py', '.jinja',
              '.j2', '.css', '.json', '.svg', '.webmanifest')
_PAGE_EXT = ('.html', '.htm', '.vue', '.svelte', '.svg', '.py', '.jinja', '.j2')
_SCRIPT_EXT = ('.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx')
# identifiers that look like addresses and are never fetched (XML namespaces, the schema.org vocabulary)
IDENTIFIER_HOSTS = ('www.w3.org', 'schema.org')


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
        if entry['match'].get('path_prefix') and not entry['match'].get('hosts'):
            raise RightsSourceError(f'source {sid!r}: path_prefix narrows hosts and needs them')
    return data


_CACHE: dict | None = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = check(json.loads(DATA.read_text(encoding='utf-8')))
    return _CACHE


# ---- reading addresses ------------------------------------------------------------------------------------------

_TEMPLATE = re.compile(r'\$\{|\{\{|\{%|<%|\{[A-Za-z_][\w.\[\]\'"]*\}|%\(|%s')
_ABSOLUTE = re.compile(r'(?:https?:)?//[^\s"\'`<>\\)]+', re.I)
_DATA_URI = re.compile(r'data:[a-z0-9.+/-]*(?:;[a-z0-9=.+-]+)*,[^\s"\'`<>)]*', re.I)
_BLOB = re.compile(r'[A-Za-z0-9+/]{%d,}={0,2}' % MIN_BLOB)
_EXTS = '|'.join(e[1:] for e in FONT_EXT + IMAGE_EXT + MEDIA_EXT)
_QUOTED_FILE = re.compile(r'(["\'`])((?:(?!\1)[^\s<>()\\,])+\.(?:' + _EXTS + r')(?:\?(?:(?!\1)[^\s<>\\])*)?)\1', re.I)
# a script or code that puts media on the page at all: then every address literal in it is a possible source
_MEDIA_SINK = re.compile(
    r'\.src\b|\bsrc\s*[:=]|srcset|poster|backgroundImage|background(?:-image)?\s*:|\.background\b'
    r'|<\s*(?:img|image|video|audio|source|picture|iframe|embed|object|link)\b|new\s+Image\b|new\s+(?:window\.)?Audio\b'
    r'|new\s+FontFace\b|new\s+Howl\b|createElement(?:NS)?\s*\([^)]*["\'`](?:img|image|video|audio|source|picture|iframe|embed|object|link)["\'`]'
    r'|urlopen|urlretrieve|requests\.(?:get|post)|httpx\.|fetch\s*\(|XMLHttpRequest', re.I)
# plainly a link target, not a load: the address follows href / action / window.open / location
_LINK_CONTEXT = re.compile(r'(?:\bhref|\baction|\bformaction|\bcite|\bping|\bxmlns(?::\w+)?|window\.open\s*\(|\bopen\s*\('
                           r'|location(?:\.href)?|location\.(?:assign|replace)\s*\()\s*[=:]?\s*\(?\s*["\'`]?\s*$', re.I)
_MEDIA_CONTEXT = re.compile(r'audio|sound|music|video|track|howl|mp3|clip', re.I)
_FONT_CONTEXT = re.compile(r'font', re.I)
_JS_COMMENT = re.compile(r'("(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`)|/\*.*?\*/|(?<![:\\"\'`/])//[^\n]*', re.S)
_NEW_AUDIO = re.compile(r'\bnew\s+(?:window\.)?Audio\s*\(\s*([^)\s][^)]*)\)', re.I)
_CSS_COMMENT = re.compile(r'/\*.*?\*/', re.S)
_CSS_ESCAPE = re.compile(r'\\([0-9a-fA-F]{1,6})\s?|\\([^\n0-9a-fA-F])')
_CSS_URL = re.compile(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^)\s"\']*))\s*\)', re.I)
_CSS_IMPORT = re.compile(r'@import\s*(?:url\(\s*)?(?:"([^"]+)"|\'([^\']+)\'|([^"\')\s;]+))', re.I)
_FONT_FACE = re.compile(r'@font-face\s*\{([^}]*)\}', re.I | re.S)
_CSS_QUOTED = re.compile(r'(["\'])((?:https?:)?//(?:(?!\1)[^\s\\])+)\1', re.I)


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
    if not re.match(r'https?://', ref, re.I):
        return ''
    try:
        return (urlsplit(ref).hostname or '').lower()
    except ValueError:
        return ''


def _literal_part(ref: str) -> tuple[str, bool]:
    """(the part of an address before its first run-time piece, whether it had one)."""
    m = _TEMPLATE.search(ref)
    return (ref[:m.start()], True) if m else (ref, False)


def _strip_js_comments(code: str) -> str:
    return _JS_COMMENT.sub(lambda m: m.group(1) or ' ', code or '')


def _strip_py_comments(source: str) -> str:
    try:
        return tokenize.untokenize(t for t in tokenize.generate_tokens(io.StringIO(source).readline)
                                   if t.type != tokenize.COMMENT)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source                       # not readable as Python: read it whole, never skip it


def _css_unescape(css: str) -> str:
    def char(m):
        if m.group(1):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return ''
        return m.group(2)
    return _CSS_ESCAPE.sub(char, css)


def _svg_text(uri: str) -> str | None:
    """The SVG a data: URI carries, or None when it does not decode to SVG text."""
    head, _, payload = uri.partition(',')
    try:
        if ';base64' in head.lower():
            text = base64.b64decode(payload + '=' * (-len(payload) % 4), validate=False).decode('utf-8')
        else:
            text = unquote(payload)
    except (ValueError, UnicodeDecodeError):
        return None
    return text if '<svg' in text.lower() else None


class _Inventory:
    """Collects [{kind, ref, where}] for one file. Each reference once; bounded at MAX_ASSETS."""

    def __init__(self, depth: int = 0):
        self.found: dict[str, dict] = {}
        self.accounted: set[str] = set()         # addresses seen in an attribute: judged there, or a link, never twice
        self.dynamic_load = False                # an element takes its address from a variable
        self.overflow = False
        self.depth = depth

    # -- adding
    def add(self, kind: str | None, ref: str | None, where: str) -> None:
        ref = (ref or '').strip()
        if not ref or ref.startswith(('#', 'javascript:', 'blob:', 'about:', 'mailto:', 'tel:', 'sms:')):
            return
        low = ref.lower()
        if low.startswith('data:'):
            head, comma, payload = ref.partition(',')
            if not comma or not payload.strip():
                return                                              # an empty data: URI carries nothing
            if low.startswith('data:image/svg+xml'):
                self._svg(ref, where)
                return
            kind = _kind_by_ext(ref) or kind or 'image'
        else:
            literal, templated = _literal_part(ref)
            if templated and not re.match(r'(?:https?:)?//', literal, re.I):
                self.dynamic_load = True                            # the whole address comes from a variable
                return
            kind = kind or _kind_by_ext(literal) or 'image'
        if ref in self.found:
            return
        if len(self.found) >= MAX_ASSETS:
            self.overflow = True
            return
        self.found[ref] = {'kind': kind, 'ref': ref, 'where': where}

    def _svg(self, uri: str, where: str) -> None:
        text = _svg_text(uri)
        if text is None or self.depth >= MAX_SVG_DEPTH:
            why = 'does not decode to SVG text' if text is None else 'is nested too deep to read'
            if uri not in self.found and len(self.found) < MAX_ASSETS:
                self.found[uri] = {'kind': 'image', 'ref': uri, 'where': where, 'unreadable': f'an SVG data: URI that {why}'}
            return
        inner = _Inventory(self.depth + 1)
        inner.page(text)
        for asset in inner.found.values():
            self.add(asset['kind'], asset['ref'], asset['where'] + ' inside an SVG data: URI')
            if asset['ref'] in self.found and asset.get('unreadable'):
                self.found[asset['ref']]['unreadable'] = asset['unreadable']
        if uri not in self.found and len(self.found) < MAX_ASSETS:
            self.found[uri] = {'kind': 'image', 'ref': uri, 'where': where, 'svg': True}

    def account(self, text: str) -> None:
        for m in _ABSOLUTE.finditer(text or ''):
            self.accounted.add(m.group(0).rstrip('.,;'))

    # -- CSS
    def css(self, css: str, where: str) -> None:
        css = _css_unescape(_CSS_COMMENT.sub(' ', css or ''))
        for m in _CSS_IMPORT.finditer(css):
            ref = next(g for g in m.groups() if g)
            self.accounted.add(ref)
            if _host(_literal_part(ref)[0]) or ref.startswith('//'):
                self.add('font', ref, '@import stylesheet (it can load fonts)')
        for body in _FONT_FACE.findall(css):
            for m in _CSS_URL.finditer(body):
                self.add('font', next((g for g in m.groups() if g), ''), '@font-face src')
        for m in _CSS_URL.finditer(css):
            ref = next((g for g in m.groups() if g), '')
            if ref not in self.accounted:
                self.add(None, ref, 'CSS url()')
        for m in _CSS_QUOTED.finditer(css):
            if m.group(2) not in self.accounted:
                self.add(None, m.group(2), f'an address in {where}')
        for m in _DATA_URI.finditer(css):
            self.add(None, m.group(0), f'a data: URI in {where}')

    # -- scripts and code
    def code(self, code: str, where: str, *, judge_all: bool | None = None) -> None:
        code = code or ''
        if judge_all is None:
            judge_all = bool(_MEDIA_SINK.search(code))
        for m in _NEW_AUDIO.finditer(code):
            arg = m.group(1).strip()
            literal = re.match(r'(["\'`])(.*?)\1', arg)
            if literal:
                self.add('media', literal.group(2), 'new Audio()')
                continue
            ref = f'new Audio({arg[:60]})'
            if ref not in self.found and len(self.found) < MAX_ASSETS:
                self.found[ref] = {'kind': 'media', 'ref': ref, 'where': 'new Audio()',
                                   'unreadable': 'audio played by script from an address a static reading cannot see'}
        for m in _DATA_URI.finditer(code):
            self.add(None, m.group(0), f'a data: URI in {where}')
        for m in _QUOTED_FILE.finditer(code):
            if m.group(2) not in self.accounted and not _LINK_CONTEXT.search(code[max(0, m.start() - 60):m.start() + 1]):
                self.add(None, m.group(2), f'an address in {where}')
        for m in _ABSOLUTE.finditer(code):
            ref = m.group(0).rstrip('.,;')
            if ref.startswith('//') and (m.start() == 0 or code[m.start() - 1] not in '"\'`(='):
                continue                                             # a // that is not the start of an address
            literal = _literal_part(ref)[0]
            if ref in self.accounted or _host(literal) in IDENTIFIER_HOSTS:
                continue
            before = code[max(0, m.start() - 60):m.start()]
            if _LINK_CONTEXT.search(before):
                continue
            kind = _kind_by_ext(literal)
            if kind is None and not judge_all:
                continue
            if kind is None:
                kind = 'media' if _MEDIA_CONTEXT.search(before) else 'font' if _FONT_CONTEXT.search(before) else 'image'
            self.add(kind, ref, f'an address in {where} that puts media on the page' if judge_all else f'an address in {where}')
        self.blobs(code, where)

    def blobs(self, text: str, where: str) -> None:
        """A long base64 literal is bytes embedded in the file. As written, the platform's own bytes are placeholders,
        so what is left is bytes the platform did not supply."""
        for m in _BLOB.finditer(text or ''):
            blob = m.group(0)
            if 'data:' in text[max(0, m.start() - 80):m.start()]:
                continue                                             # read as its data: URI
            ref = f'base64:{blob[:24]}'
            if ref not in self.found and len(self.found) < MAX_ASSETS:
                self.found[ref] = {'kind': 'image', 'ref': ref, 'where': f'a base64 literal of {len(blob)} characters in {where}',
                                   'unreadable': 'bytes embedded in the file that the platform did not supply'}

    def json_ld(self, text: str) -> None:
        try:
            data = json.loads(text)
        except ValueError:
            self.code(text, 'a JSON-LD block', judge_all=False)
            return
        image_keys = ('image', 'logo', 'photo', 'thumbnailurl', 'thumbnail', 'primaryimageofpage', 'screenshot')
        media_keys = ('audio', 'video', 'contenturl', 'embedurl')

        def values(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, list):
                for item in node[:50]:
                    yield from values(item)
            elif isinstance(node, dict):
                for key in ('url', 'contentUrl', '@id'):
                    if isinstance(node.get(key), str):
                        yield node[key]

        def walk(node, depth=0):
            if depth > 12:
                return
            if isinstance(node, dict):
                for key, value in node.items():
                    low = str(key).lower()
                    if low in image_keys or low in media_keys:
                        for ref in values(value):
                            self.add('image' if low in image_keys else 'media', ref, f'JSON-LD "{key}"')
                    elif isinstance(value, (dict, list)):
                        walk(value, depth + 1)
                    elif isinstance(value, str):
                        self.account(value)
            elif isinstance(node, list):
                for item in node[:200]:
                    walk(item, depth + 1)
        walk(data)

    # -- HTML
    def page(self, text: str) -> None:
        walker = _Walker(self)
        try:
            walker.feed(text or '')
            walker.close()
        except Exception:                      # the parser must never turn an odd file into a silent pass
            self.code(text or '', 'a file that could not be read as HTML', judge_all=True)
        walker.flush()

    def tag(self, tag: str, a: dict[str, str]) -> None:
        for name, value in a.items():
            if not name.startswith(('on', 'data-')) and name != 'style':     # those are read as code, CSS, lazy loads
                self.account(value)
        rel = a.get('rel', '').lower().split()
        if tag in ('img', 'input') and (tag == 'img' or a.get('type', '').lower() == 'image'):
            self.add('image', a.get('src'), f'<{tag} src>')
            self.srcset(a.get('srcset'), f'<{tag} srcset>')
        elif tag in ('image', 'feimage', 'use'):
            ref = a.get('href') or a.get('xlink:href') or ''
            if tag != 'use' or not ref.startswith('#'):
                self.add('image', ref, f'<{tag} href>')
        elif tag in ('audio', 'video'):
            self.add('media', a.get('src'), f'<{tag} src>')
            self.add('image', a.get('poster'), '<video poster>')
        elif tag == 'track':
            self.add('media', a.get('src'), '<track src>')
        elif tag == 'source':
            self.srcset(a.get('srcset'), '<source srcset>')
            src = a.get('src')
            if src:
                self.add(_kind_by_ext(src) or ('image' if a.get('type', '').lower().startswith('image/') else 'media'),
                         src, '<source src>')
        elif tag in ('embed', 'object'):
            ref = a.get('src') or a.get('data')
            mime = a.get('type', '').lower()
            kind = ('image' if mime.startswith('image/') else 'font' if 'font' in mime else
                    'media' if mime.startswith(('audio/', 'video/')) else _kind_by_ext(ref or ''))
            if ref and (kind or _host(_literal_part(ref)[0])):
                self.add(kind or 'embed', ref, f'<{tag}>')
        elif tag in ('iframe', 'frame'):
            ref = a.get('src', '')
            if _host(_literal_part(ref)[0]) or ref.startswith('//') or _TEMPLATE.search(ref):
                self.add('embed', ref, f'<{tag}> on another site')
        elif tag == 'link':
            href = a.get('href', '')
            as_ = a.get('as', '').lower()
            self.srcset(a.get('imagesrcset'), '<link imagesrcset>')
            if 'stylesheet' in rel or (('preload' in rel or 'prefetch' in rel) and as_ == 'style'):
                if _host(_literal_part(href)[0]) or href.startswith('//'):
                    self.add('font', href, 'external stylesheet (it can load fonts)')
            elif ('preload' in rel or 'prefetch' in rel) and as_ in ('font', 'image', 'audio', 'video'):
                self.add({'font': 'font', 'image': 'image'}.get(as_, 'media'), href, '<link rel=preload>')
            elif any(r in rel for r in ('icon', 'apple-touch-icon', 'apple-touch-icon-precomposed', 'mask-icon')):
                self.add('image', href, '<link rel=icon>')
        elif tag == 'meta':
            name = (a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            if name in ('og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image', 'twitter:image:src',
                        'msapplication-tileimage', 'image', 'thumbnailurl'):
                self.add('image', a.get('content'), f'<meta {name}>')
            elif name in ('og:audio', 'og:audio:url', 'og:audio:secure_url', 'og:video', 'og:video:url',
                          'og:video:secure_url', 'twitter:player', 'twitter:player:stream'):
                self.add('media', a.get('content'), f'<meta {name}>')
        if a.get('background') and tag in ('body', 'table', 'td', 'th', 'tr', 'div'):
            self.add('image', a['background'], f'<{tag} background>')
        if a.get('style'):
            self.css(a['style'], 'a style attribute')
        for name, value in a.items():
            if name.startswith('on') and value:
                self.code(value, f'an {name} handler')
            elif name.startswith('data-') and value and name not in ('data-148-window', 'data-148-close'):
                if name.endswith('srcset'):
                    self.srcset(value, f'<{tag} {name}>')
                elif _DATA_URI.match(value) or _kind_by_ext(_literal_part(value)[0]) or (
                        re.match(r'(?:https?:)?//', value, re.I) and re.search(r'src|image|img|bg|background|poster|photo|thumb|lazy|original', name)):
                    self.add(None, value, f'<{tag} {name}> (loaded by script)')

    def srcset(self, value: str | None, where: str) -> None:
        for part in re.split(r',\s+|,(?=\s*(?:https?:)?//)', value or ''):
            self.add('image', part.strip().split(' ')[0], where)

    # -- one file
    def file(self, text: str, path: str | None) -> None:
        low = (path or 'page.html').lower()
        if low.endswith('.css'):
            self.css(text, 'a stylesheet')
        elif low.endswith(_SCRIPT_EXT):
            self.code(_strip_js_comments(text), 'a script file')
        elif low.endswith(('.json', '.webmanifest')):
            self.code(text, 'a data file', judge_all=False)
        elif low.endswith(('.py', '.jinja', '.j2')):
            source = _strip_py_comments(text) if low.endswith('.py') else text
            self.page(source)
            self.constants(source)
            for m in _DATA_URI.finditer(source):
                self.add(None, m.group(0), 'a data: URI in the code')
            self.blobs(source, 'the code')
        else:
            self.page(text)

    def constants(self, source: str) -> None:
        """Address constants of a Python file: a string that is nothing but an address. Judged when the page takes
        addresses from variables, or the code fetches over the network; a page that names every address itself
        gives them no way onto the page."""
        fetches = bool(re.search(r'urlopen|urlretrieve|requests\.(?:get|post)|httpx\.', source))
        if not (self.dynamic_load or fetches):
            return
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return
        for tok in tokens:
            if tok.type != tokenize.STRING:
                continue
            m = re.fullmatch(r'[rbuRBU]{0,2}(["\'])((?:https?:)?//[^\s"\'<>\\]+)\1', tok.string)
            if not m or m.group(2) in self.accounted or _host(m.group(2)) in IDENTIFIER_HOSTS:
                continue
            self.add(None, m.group(2), 'an address constant in code whose page takes addresses from variables'
                     if self.dynamic_load else 'an address constant in code that fetches over the network')


class _Walker(HTMLParser):
    def __init__(self, inventory: _Inventory):
        super().__init__(convert_charrefs=True)
        self.inv = inventory
        self.raw: tuple[str, dict] | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {str(k).lower(): (v or '') for k, v in attrs}
        self.inv.tag(tag, a)
        if tag in ('script', 'style'):
            self.flush()
            self.raw, self.buffer = (tag, a), []

    def handle_startendtag(self, tag, attrs):
        self.inv.tag(tag, {str(k).lower(): (v or '') for k, v in attrs})

    def handle_endtag(self, tag):
        if self.raw and tag == self.raw[0]:
            self.flush()

    def handle_data(self, data):
        if self.raw:
            self.buffer.append(data)

    def flush(self):
        if not self.raw:
            return
        (tag, a), text = self.raw, ''.join(self.buffer)
        self.raw, self.buffer = None, []
        if tag == 'style':
            self.inv.css(text, 'a <style> block')
        elif 'ld+json' in a.get('type', '').lower():
            self.inv.json_ld(text)
        elif 'json' in a.get('type', '').lower() or a.get('type', '').lower() in ('text/template', 'text/x-template'):
            self.inv.code(text, 'a data block', judge_all=False)
        else:
            self.inv.code(_strip_js_comments(text), 'a script')


def inventory(text: str, path: str | None = None) -> list[dict]:
    """[{kind, ref, where}] for every asset reference of one served file, each reference once. `path` says what the
    file is (its extension); without it the text is read as a page. Bounded at MAX_ASSETS: past the bound the
    list ends with an entry that says the file was not fully read."""
    inv = _Inventory()
    inv.file(text or '', path)
    out = list(inv.found.values())
    if inv.overflow:
        out.append({'kind': 'image', 'ref': f'more than {MAX_ASSETS} asset references', 'where': 'the whole file',
                    'unreadable': f'the file has more than {MAX_ASSETS} asset references and was not fully read',
                    'every_kind': True})
    return out


# ---- the judgement ----------------------------------------------------------------------------------------------

def shown(ref: str) -> str:
    """The reference as a finding shows it: never a page of base64."""
    if ref.startswith('data:'):
        return ref.split(',', 1)[0][:60] + f',… ({len(ref)} characters)'
    return ref if len(ref) <= 160 else ref[:157] + '...'


def _matches(entry: dict, kind: str, ref: str) -> bool:
    if kind not in entry['kinds']:
        return False
    match = entry['match']
    for prefix in match.get('marker_prefix', ()):
        # exactly a placeholder the platform writes: "<prefix><number>" or the whole name -- never merely its start
        if (re.fullmatch(re.escape(prefix) + r'\d{1,3}', ref) if prefix.endswith('/') else ref == prefix):
            return True
    low = ref.lower()
    literal = _literal_part(ref)[0]
    host = _host(literal)
    if host and host in match.get('hosts', ()):
        prefixes = match.get('path_prefix')
        if not prefixes:
            return True
        try:
            path = urlsplit(literal if not literal.startswith('//') else 'https:' + literal).path
        except ValueError:
            return False
        return any(path.startswith(p) for p in prefixes)
    relative = not host and not re.match(r'(?:https?:)?//', ref, re.I) and not low.startswith(('data:', '148ai-asset:', 'base64:'))
    if 'svg' in match.get('authored', ()) and relative and low.split('?', 1)[0].split('#', 1)[0].endswith('.svg'):
        return True
    return bool(match.get('own')) and relative


def judge(asset: dict) -> tuple[str | None, str]:
    """(source id, its right) when the source is known; (None, why it is not) otherwise."""
    kind, ref = asset['kind'], asset['ref']
    if asset.get('unreadable'):
        return None, asset['unreadable']
    sources = load()['sources']
    if asset.get('svg'):                         # a decoded SVG data: URI; what it carries was read on its own
        return 'authored_svg', sources['authored_svg']['right']
    for sid, entry in sources.items():
        if _matches(entry, kind, ref):
            return sid, entry['right']
    low = ref.lower()
    if low.startswith('148ai-asset:'):
        return None, 'a 148ai-asset:// address of a kind the platform does not supply'
    if low.startswith('data:'):
        return None, 'bytes embedded in the file that the platform did not supply'
    literal, templated = _literal_part(ref)
    host = _host(literal)
    if host and not (templated and not re.match(r'(?:https?:)?//[^/]+/', literal, re.I)):
        return None, f'{host} is not a known source for {_LABEL[kind]}'
    if re.match(r'(?:https?:)?//', ref, re.I):
        return None, 'an address on another site whose host is built at run time: its source cannot be shown'
    return None, f'no known source for {_LABEL[kind]}'


def unknown(text: str, kinds, path: str | None = None) -> list[dict]:
    """The findings of one unit: every asset of these kinds, in this file, whose source is not known."""
    kinds = (kinds,) if isinstance(kinds, str) else tuple(kinds)
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        raise ValueError(f'unknown asset kind {bad}; one of {KINDS}')
    out = []
    for asset in inventory(text, path):
        if asset['kind'] not in kinds and not asset.get('every_kind'):
            continue
        source, why = judge(asset)
        if source is None:
            out.append({'where': f"{asset['where']}: {shown(asset['ref'])}", 'why': why})
    return out


def ledger(text: str, path: str | None = None) -> list[dict]:
    """Every asset of one file with its source (or None) -- what A7 writes into the build evidence."""
    out = []
    for asset in inventory(text, path):
        source, note = judge(asset)
        out.append({'kind': asset['kind'], 'ref': shown(asset['ref']), 'where': asset['where'], 'source': source,
                    'note': note})
    return out
