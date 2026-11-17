"""G-APPLE, part 2: the page's CSS and markup against the design contract and the refusal list. Deterministic.

Every rule answers yes or no and names where. Nothing here judges taste; the two reviewers do (reviewers.py).

Contract (the owner: "zero raw hex, zero px outside the scale, zero third weight"):
  RAW_COLOUR        a hex / rgb() / hsl() colour outside the contract's :root block
  PX_OFF_SCALE      a px value in a size or spacing property that is not on the type scale, the 8-grid or a hairline
  THIRD_WEIGHT      a font-weight other than the contract's two
  RADIUS_OFF        a border-radius other than the contract's radius (0 and a 50% circle are not corners)
  CONTRACT_MISSING  the page does not carry the contract's :root block as given
  FOCUS_VISIBLE_MISSING / STATE_MISSING   a control style with no :focus-visible; a button with no :hover or :active

Refusal list (binary):
  HERO_GRADIENT_STROKE, THREE_ICON_CARDS, CAROUSEL, SHADOW_EVERYWHERE, RADIUS_24_EVERYWHERE, CENTER_EVERYWHERE,
  SECOND_ACCENT (a colour token the contract does not define, used as a colour), BUTTON_STYLES (more than two),
  EMOJI_ICON, LOREM
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from . import contract as C

MAX_PER_CODE = 5
_STYLE = re.compile(r'<style\b[^>]*>(.*?)</style\s*>', re.S | re.I)
_COMMENT = re.compile(r'/\*.*?\*/', re.S)
_RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')
_COLOUR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\([^)]*\)')
_PX = re.compile(r'(?<![\w.-])(\d+(?:\.\d+)?)px\b')
_SIZED = re.compile(r'^(font-size|line-height|letter-spacing|margin(-[a-z-]+)?|padding(-[a-z-]+)?|gap|row-gap|column-gap|'
                    r'inset(-[a-z-]+)?|top|right|bottom|left|border-radius|border(-[a-z-]+)?-radius)$')
_WEIGHT_WORDS = {'normal': 400, 'bold': 700}
_EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿⭐⬆✅❌]')
_LOREM = re.compile(r'lorem ipsum|dolor sit amet', re.I)
_CAROUSEL = re.compile(r'carousel|swiper|slick|\bslider\b|scroll-snap-type', re.I)
_BUTTONISH = re.compile(r'(^|[\s,>+~(])(button|\.btn[\w-]*|\.button[\w-]*|\.cta[\w-]*|a\.[\w-]*(btn|button|cta)[\w-]*|input\[type=.?submit.?\])')
_HEROISH = re.compile(r'hero|masthead|banner|\bheader\b', re.I)


def _declarations(body: str) -> list[tuple[str, str]]:
    out = []
    for part in body.split(';'):
        if ':' in part:
            name, value = part.split(':', 1)
            out.append((name.strip().lower(), value.strip()))
    return out


def rules_of(html: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """[(selector, [(property, value)])] of every rule in the page's <style> blocks, at-rule wrappers removed."""
    css = _COMMENT.sub('', '\n'.join(_STYLE.findall(html or '')))
    css = re.sub(r'@(media|supports|container|layer)[^{]*\{', '', css)       # the inner rules are read; the wrapper is not
    css = re.sub(r'@(import|charset|font-face)[^;{]*(;|\{[^{}]*\})', '', css)
    return [(sel.strip(), _declarations(body)) for sel, body in _RULE.findall(css)]


class _Cards(HTMLParser):
    """Finds a parent whose direct children are exactly three elements, each opening with an icon (svg, img, i, or an
    emoji) before its heading: the three-icon-card row."""
    VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'use'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.rows: list[str] = []
        self.emoji_icons: list[str] = []

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': [], 'first': None, 'text': ''}
        if self.stack:
            parent = self.stack[-1]
            parent['children'].append(node)
            if parent['first'] is None and not parent['text'].strip():
                parent['first'] = tag
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack and self.stack[-1]['tag'] == tag:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack:
            node = self.stack[-1]
            if node['first'] is None and not node['text'].strip() and _EMOJI.match(data.strip()[:2] or ' '):
                node['first'] = 'emoji'
            node['text'] += data

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                node = self.stack[i]
                del self.stack[i:]
                self._closed(node)
                return

    def _closed(self, node):
        kids = [k for k in node['children'] if k['tag'] not in ('script', 'style')]
        if (len(kids) == 3 and len({k['tag'] for k in kids}) == 1 and kids[0]['tag'] in ('div', 'article', 'li', 'section')
                and all(k['first'] in ('svg', 'img', 'i', 'emoji', 'span') and self._has_heading(k) for k in kids)):
            self.rows.append(f"<{node['tag']} class=\"{node['attrs'].get('class', '')}\">")
        text = node['text'].strip()
        if node['tag'] in ('button', 'a', 'li', 'h1', 'h2', 'h3', 'h4', 'span', 'i', 'div') and text and \
                len(text) <= 3 and _EMOJI.search(text):
            self.emoji_icons.append(f"<{node['tag']}>{text}")

    @staticmethod
    def _has_heading(node) -> bool:
        todo = list(node['children'])
        for _ in range(200):                                   # bounded walk of one card
            if not todo:
                return False
            n = todo.pop()
            if n['tag'] in ('h2', 'h3', 'h4', 'h5', 'strong'):
                return True
            todo.extend(n['children'])
        return False


def check(html: str, contract: dict) -> list[dict]:
    """[{code, where, why}] -- at most MAX_PER_CODE per code, and the number left out is said."""
    found: list[dict] = []

    def add(code, where, why):
        found.append({'code': code, 'where': str(where)[:120], 'why': str(why)[:200]})
    rules = rules_of(html)
    allowed_px = set(C.TYPE_PX) | set(C.SPACE_PX) | set(C.HAIRLINE_PX) | {C.RADIUS_PX}
    token_names = set(contract['tokens'])
    root_ok = False
    weights, radii, shadows, centred, aligned = set(), set(), 0, 0, 0
    button_looks: set[tuple] = set()
    pseudo = {'hover': False, 'focus-visible': False, 'active': False}
    button_pseudo = {'hover': False, 'active': False}
    gradient_hero = stroke = False
    for selector, decls in rules:
        is_root = selector.replace(' ', '') in (':root', 'html', ':root,html')
        if is_root and all(contract['tokens'].get(k) == v for k, v in decls if k in token_names) and \
                token_names <= {k for k, _ in decls}:
            root_ok = True
        buttonish = bool(_BUTTONISH.search(selector))
        for state in pseudo:
            if ':' + state in selector:
                pseudo[state] = True
                if buttonish and state in button_pseudo:
                    button_pseudo[state] = True
        look = []
        for prop, value in decls:
            if prop.startswith('--'):
                if not is_root:
                    add('SECOND_ACCENT', selector, f'a custom property defined outside the contract: {prop}')
                elif prop not in token_names and _COLOUR.search(value):
                    add('SECOND_ACCENT', selector, f'a colour token the contract does not define: {prop}: {value}')
                continue
            for m in _COLOUR.finditer(value):
                add('RAW_COLOUR', f'{selector} {{ {prop} }}', f'{m.group(0)}: use a var(--color-...) token')
            for m in re.finditer(r'var\((--[\w-]+)', value):
                if m.group(1) not in token_names:
                    add('SECOND_ACCENT', f'{selector} {{ {prop} }}', f'{m.group(1)} is not in the contract')
            if _SIZED.match(prop):
                for m in _PX.finditer(value):
                    px = float(m.group(1))
                    if px not in allowed_px:
                        add('PX_OFF_SCALE', f'{selector} {{ {prop}: {value} }}', f'{m.group(0)} is not on the scale')
            if prop == 'font-weight':
                w = _WEIGHT_WORDS.get(value.lower(), value)
                resolved = contract['tokens'].get(re.sub(r'var\((--[\w-]+)\)', r'\1', str(w)), w)
                weights.add(str(resolved))
            if prop.endswith('radius'):
                for part in value.replace('/', ' ').split():
                    part = contract['tokens'].get(re.sub(r'var\((--[\w-]+)\)', r'\1', part), part)
                    if part not in ('0', '0px', '50%', f'{C.RADIUS_PX}px'):
                        radii.add(part)
            if prop == 'box-shadow' and value.lower() != 'none':
                shadows += 1
                if selector.strip() in ('*', 'body *', 'div', 'section'):
                    add('SHADOW_EVERYWHERE', selector, 'a shadow on every element')
            if prop == 'text-align':
                aligned += 1
                if value.lower() == 'center':
                    centred += 1
                    if selector.strip() in ('body', 'html', '*', 'main'):
                        add('CENTER_EVERYWHERE', selector, 'the whole page is centred')
            if prop in ('background', 'background-image') and 'gradient(' in value and _HEROISH.search(selector):
                gradient_hero = True
            if 'text-stroke' in prop:
                stroke = True
            if buttonish and prop in ('background', 'background-color', 'border', 'border-color', 'color') and \
                    ':' not in selector.split(',')[0].split()[-1]:
                look.append((prop.replace('-color', ''), value))
        if buttonish and look:
            button_looks.add(tuple(sorted(look)))
    if not root_ok:
        add('CONTRACT_MISSING', ':root', f"the page does not carry design contract {contract['fingerprint']} as given")
    extra = sorted(w for w in weights if w not in {str(x) for x in C.WEIGHTS})
    if extra:
        add('THIRD_WEIGHT', 'font-weight', f'weights outside the contract: {", ".join(extra)}')
    if radii:
        add('RADIUS_OFF', 'border-radius', f'corners outside the contract: {", ".join(sorted(radii))}')
        if any(r.startswith('24') for r in radii) and len(rules) and sum(
                1 for _, d in rules for p, v in d if p.endswith('radius') and v.startswith('24')) >= 4:
            add('RADIUS_24_EVERYWHERE', 'border-radius', '24px corners on everything')
    if shadows >= 5:
        add('SHADOW_EVERYWHERE', 'box-shadow', f'{shadows} rules cast a shadow')
    if aligned >= 4 and centred / aligned > 0.6:
        add('CENTER_EVERYWHERE', 'text-align', f'{centred} of {aligned} alignment rules centre the text')
    if gradient_hero and stroke:
        add('HERO_GRADIENT_STROKE', 'hero', 'a gradient hero with outlined text')
    if len(button_looks) > 2:
        add('BUTTON_STYLES', 'buttons', f'{len(button_looks)} button styles; at most two (primary and secondary)')
    if not pseudo['focus-visible']:
        add('FOCUS_VISIBLE_MISSING', 'controls', 'no :focus-visible style: a keyboard user cannot see where they are')
    if any(_BUTTONISH.search(sel) for sel, _ in rules):
        for state, seen in button_pseudo.items():
            if not seen:
                add('STATE_MISSING', 'buttons', f'no :{state} style for a button')
    body = re.sub(r'(?s)<(script|style)\b.*?</\1\s*>', ' ', html or '')
    if _LOREM.search(body):
        add('LOREM', 'page text', 'placeholder text (lorem ipsum)')
    if _CAROUSEL.search(html or ''):
        add('CAROUSEL', 'page', 'a carousel or slider')
    cards = _Cards()
    try:
        cards.feed(body)
        cards.close()
    except Exception as exc:                                   # a page the parser cannot read is said, not skipped
        add('UNREADABLE', 'markup', f'{type(exc).__name__}: {exc}')
    for row in cards.rows[:3]:
        add('THREE_ICON_CARDS', row, 'a row of three icon cards')
    for icon in cards.emoji_icons[:5]:
        add('EMOJI_ICON', icon, 'an emoji used as an icon')
    # every code is kept; a code that fires many times keeps its first MAX_PER_CODE and says how many more there are
    kept, counts = [], {}
    for f in found:
        counts[f['code']] = counts.get(f['code'], 0) + 1
        if counts[f['code']] <= MAX_PER_CODE:
            kept.append(f)
    for code, n in counts.items():
        if n > MAX_PER_CODE:
            kept.append({'code': code, 'where': '', 'why': f'and {n - MAX_PER_CODE} more of {code}'})
    return kept
