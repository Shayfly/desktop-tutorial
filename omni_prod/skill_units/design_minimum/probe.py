"""skill.design.minimum -- static: a business site meets a professional minimum (the owner, 2026-11-19, on the law-firm
site bld_b0eb47a5: "רמה נמוכה ... אני רוצה מקצועיות"). It judges only a business page -- one with a contact action
(tel:, WhatsApp, mailto: or #contact); an app screen or a game is not judged.

Fails when the page has: not exactly one <h1>; fewer than 4 <section> blocks; no visual at all; or the main contact
action only once. A visual is a picture, not an icon (visual plan S0, 2026-11-27: the gate counted the phone, WhatsApp
and menu icons of a page with no picture as its visual -- Claude's bug in the gate's definition): an <img> or <picture>
or <video> whose declared size is not an icon's, a CSS background-image / url(), or an <svg> that is not inside a
control (<a>, <button>, <summary>) and not icon-sized."""
import re
from html.parser import HTMLParser

_CONTACT = re.compile(r'href\s*=\s*["\'](?:tel:|https?://(?:wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)|whatsapp:|'
                      r'mailto:|#contact\b|#צור-קשר)', re.I)
MIN_SECTIONS = 4
ICON_MAX_PX = 48                       # a declared width or height up to this is an icon, not a picture
CONTROLS = ('a', 'button', 'summary')
_BACKGROUND_URL = re.compile(r'background(?:-image)?\s*:[^;"]*url\(', re.I)


def _px(value):
    m = re.fullmatch(r'\s*(\d+(?:\.\d+)?)(?:px)?\s*', value or '')
    return float(m.group(1)) if m else None


def _is_icon_sized(attrs):
    sizes = [_px(attrs.get(k)) for k in ('width', 'height')]
    return any(v is not None and v <= ICON_MAX_PX for v in sizes)


class _Visuals(HTMLParser):
    """Counts the pictures: what a visitor sees as an image, not a glyph inside a button or a link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = {c: 0 for c in CONTROLS}
        self.pictures = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in CONTROLS:
            self.depth[tag] += 1
        elif tag in ('picture', 'video'):
            self.pictures += 1
        elif tag == 'img' and not _is_icon_sized(a):
            self.pictures += 1
        elif tag == 'svg' and not any(self.depth.values()) and not _is_icon_sized(a):
            self.pictures += 1

    def handle_startendtag(self, tag, attrs):
        if tag not in CONTROLS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in CONTROLS and self.depth[tag]:
            self.depth[tag] -= 1


def has_visual(html):
    parser = _Visuals()
    parser.feed(html)
    parser.close()
    return bool(parser.pictures or _BACKGROUND_URL.search(html))


def probe(html):
    html = html or ''
    contact = len(_CONTACT.findall(html))
    if not contact:
        return {'status': 'pass'}                      # not a business page: not judged
    findings = []
    h1 = len(re.findall(r'<h1\b', html, re.I))
    if h1 != 1:
        findings.append({'where': f'{h1} <h1>', 'why': 'a page has exactly one main heading'})
    sections = len(re.findall(r'<section\b', html, re.I))
    if sections < MIN_SECTIONS:
        findings.append({'where': f'{sections} <section>',
                         'why': f'at least {MIN_SECTIONS} content sections; this page is one bare block'})
    if not has_visual(html):
        findings.append({'where': 'the page', 'why': 'no image or visual anywhere (an icon is not one): a hero visual is expected'})
    if contact < 2:
        findings.append({'where': 'the contact action', 'why': 'it appears once: repeat it at the end of the page'})
    return {'status': 'fail', 'code': 'DESIGN_TOO_BASIC', 'findings': findings} if findings else {'status': 'pass'}
