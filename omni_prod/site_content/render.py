"""The platform renders the content document with the section library, deterministically, and writes the repository.

`to_library(doc, sheet, ...)` turns the model's copy plus the fact sheet into the library's content: every fact slot
(phone, WhatsApp, e-mail, address, hours, the hero panel's facts, reviews, prices, images, the footer year) comes from
the sheet in the customer's own spans; the model's strings are copy. `render` refuses a design contract whose
fingerprint is not the one the route locked, and a stored document whose binds (brief, canon, contract, renderer) do
not match the build -- stale content never survives a brief change. `repository` writes the files: public/index.html,
content/site.json (the document with its binds), content/facts.json (what the fixed test asserts), a fixed stdlib
GET-only app.py (POST 405, no writes), a fixed tests/test_site.py and a platform-written .omni/project.json that covers
every acceptance id of the spec. app.py, tests/test_site.py and .omni/project.json are the same bytes in every round.

Fonts (warehouse 126): the route locks a pair from the font-pair library (omni_prod/typography) into the contract --
a display face for the headings and a body face -- in place of the Design line's one font (slice 1 used the body
font for the headings).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .. import section_library as L
from .. import typography as T
from ..g_apple import contract as C
from . import colour_roles
from . import legal as LEGAL

HERE = Path(__file__).resolve().parent
_LIBRARY_FILES = ('__init__.py', 'library.css', 'directions.json')
_TYPOGRAPHY_FILES = ('__init__.py', 'scripts.json', 'font_pairs.json')     # warehouse 126/129: the page's fonts
_REF = re.compile(r'@price:\d{1,3}')
_TIME = re.compile(r'\d{1,2}:\d{2}')
PAGE = 'public/index.html'
SITE_JSON = 'content/site.json'
FACTS_JSON = 'content/facts.json'
PLATFORM_FILES = ('app.py', 'tests/test_site.py', '.omni/project.json', 'README.md', FACTS_JSON)


class SiteRenderDefect(RuntimeError):
    """The platform's own render is wrong (a contract or bind mismatch, a library error, a gate finding outside the
    model's copy). failure_code 'site_render_defect'; never repaired by the model."""


def renderer_version() -> str:
    h = hashlib.sha256()
    for name in _LIBRARY_FILES:
        h.update((Path(L.__file__).resolve().parent / name).read_bytes())
    for name in _TYPOGRAPHY_FILES:
        h.update((Path(T.__file__).resolve().parent / name).read_bytes())
    h.update((HERE / 'render.py').read_bytes())
    h.update((HERE / 'legal.py').read_bytes())                   # warehouse 127: the legal page's text
    return h.hexdigest()[:16]


RENDERER_VERSION = renderer_version()


# ---- the render contract -------------------------------------------------------------------------------------------
_DESIGN_LINE = re.compile(r'Design: style (?P<style>[\w-]+); (?P<colours>[^\n]*?); font (?P<font>[^;()\n]{1,200}?) \(')


def render_contract(prompt: str, palette: dict, fonts: dict | None = None,
                    variants: dict | None = None) -> tuple[dict, str]:
    """(contract, source). The brief's own contract when its Design line locks one (source 'brief': the G-APPLE gate
    holds the same object). A brief whose customer stated fewer than four colours locks none (the gate says NOT_RUN):
    the page then takes the roles of the colours the customer stated (colour_roles.roles) and completes the palette
    from the business category's catalogue palette: a stated pair fills primary and accent (a near-black or near-white
    one is the page), a description word ("כהה", "dark", "בהיר", "light") picks the palette's dark or light variant, and
    a colour answer in which nothing is known leaves the category's palette (source 'brief-primary+category' when the
    customer stated a colour, 'category+dark', 'category+light' or 'category' when only words). A Design line that is
    not there at all raises ContractError. `fonts` is the route's font pair (warehouse 126, typography.contract_fonts),
    locked into either contract. `variants` is the palette's declared dark and light variants (warehouse 125,
    vertical_palettes.variants_for); a description word without them raises."""
    try:
        return C.build(prompt, fonts), 'brief'
    except C.ContractError as first:
        block = (prompt or '').rsplit('--- Approved project brief', 1)
        m = _DESIGN_LINE.search(block[1] if len(block) == 2 else '')
        if not m:
            raise C.ContractError(f'{first}; and there is no Design line to complete') from first
        r = colour_roles.roles(m['colours'], palette, variants)
        line = (f"\n--- Approved project brief\nDesign: style {m['style']}; primary colour {r['primary']}; palette "
                f"{r['primary']}, {r['accent']}, {r['background']}, {r['ink']} (primary, accent, background, text: "
                f"{r['basis']}); font {m['font']} (load it from Google Fonts with a system fallback)")
        return C.build(line, fonts), r['source']


# ---- the document as the library's content --------------------------------------------------------------------------
def _sub(text: str, sheet) -> str:
    """A copy string with each @price:N replaced by the customer's own price span."""
    def one(m):
        price = sheet.price(m.group(0))
        if price is None:
            raise SiteRenderDefect(f'{m.group(0)} reached the renderer without a price in the sheet')
        return price['span']
    return _REF.sub(one, text)


def shown(text: str, sheet) -> str:
    """A copy string as the page will show it, before the render: each @price:N the sheet holds becomes what _sub
    writes in its place (the customer's own span), so the validator measures a field on the text the section library
    measures (site_content/validate.py). A reference the sheet does not hold stays as written: the validator reports
    it (REF_UNKNOWN) and the renderer never receives it."""
    return _REF.sub(lambda m: _sub(m.group(0), sheet) if sheet.price(m.group(0)) is not None else m.group(0), text)


def _head(s: dict, key: str, sheet, outline_titles: dict) -> dict:
    out = {'title': _sub(s['title'], sheet)}
    eyebrow = outline_titles.get(key) or s.get('eyebrow')
    if eyebrow:
        out['eyebrow'] = _sub(eyebrow, sheet)
    if s.get('lead'):
        out['lead'] = _sub(s['lead'], sheet)
    return out


def to_library(doc: dict, sheet, *, direction: str, year: str, outline_titles: dict,
               order: list[str] | None = None, legal: bool = False) -> dict:
    """The section library's content dict: the model's copy, the sheet's facts. `legal`: the site has a legal page
    (warehouse 127), and the footer links to it."""
    sec = doc['sections']
    name = sheet.name or doc['name']
    c: dict = {'name': name, 'title': f"{name} – {_sub(doc['tagline'], sheet)}",
               'description': _sub(doc['description'], sheet), 'tagline': _sub(doc['tagline'], sheet), 'year': year,
               'direction': direction, 'phone': sheet.phone}
    if legal:
        c['legal_href'] = LEGAL.HREF
    for key in ('whatsapp', 'email', 'address'):
        if getattr(sheet, key):
            c[key] = getattr(sheet, key)
    if sheet.hours:
        c['hours'] = ' · '.join(sheet.hours)
    if doc.get('layout'):
        c['layout'] = dict(doc['layout'])
    h = sec['hero']
    hero = {k: _sub(h[k], sheet) for k in ('eyebrow', 'title', 'lead', 'cta', 'note', 'panel_label') if h.get(k)}
    if h.get('panel_figure'):
        hero['panel_figure'] = h['panel_figure']['value']
        hero['panel_caption'] = _sub(h['panel_figure']['caption'], sheet)
    facts = []
    if sheet.hours:
        facts.append(('שעות', ' · '.join(sheet.hours)))
    if sheet.address:
        facts.append(('כתובת', sheet.address))
    facts.append(('טלפון', sheet.phone, L.tel(sheet.phone)))
    hero['panel_facts'] = facts
    if sheet.images.get('hero'):
        hero['image'] = dict(sheet.images['hero'])
    c['hero'] = hero
    if 'stats' in sec:
        c['stats'] = [(i['value'], _sub(i['label'], sheet)) for i in sec['stats']['items']]
        if sec['stats'].get('label'):
            c['stats_label'] = _sub(sec['stats']['label'], sheet)
    if 'services' in sec:
        s = sec['services']
        c['services'] = {**_head(s, 'services', sheet, outline_titles),
                         'items': [(_sub(i['title'], sheet), _sub(i['desc'], sheet)) for i in s['items']]}
    if 'about' in sec:
        s = sec['about']
        about = {**_head(s, 'about', sheet, outline_titles), 'paragraphs': [_sub(p, sheet) for p in s['paragraphs']]}
        if s.get('facts'):
            about['facts'] = [(_sub(f['label'], sheet), _sub(f['value'], sheet)) for f in s['facts']]
        if sheet.images.get('story'):
            about['image'] = dict(sheet.images['story'])
        c['about'] = about
    if 'process' in sec:
        s = sec['process']
        c['process'] = {**_head(s, 'process', sheet, outline_titles),
                        'steps': [(_sub(i['title'], sheet), _sub(i['desc'], sheet)) for i in s['steps']]}
    if 'faq' in sec:
        s = sec['faq']
        c['faq'] = {**_head(s, 'faq', sheet, outline_titles),
                    'items': [(_sub(i['q'], sheet), _sub(i['a'], sheet)) for i in s['items']]}
    if 'cta' in sec:
        c['cta'] = {'title': _sub(sec['cta']['title'], sheet),
                    **({'text': _sub(sec['cta']['text'], sheet)} if sec['cta'].get('text') else {})}
    if 'testimonials' in sec:
        s = sec['testimonials']
        items = []
        for ref in s['items']:
            r = sheet.review(ref)
            if r is None:
                raise SiteRenderDefect(f'{ref} reached the renderer without a review in the sheet')
            items.append({'text': r['text'], 'name': r['author']})
        c['testimonials'] = {**_head(s, 'testimonials', sheet, outline_titles), 'items': items}
    if 'pricelist' in sec:
        s = sec['pricelist']
        groups = []
        for g in s['groups']:
            items = []
            for i in g['items']:
                price = sheet.price(i['price'])
                if price is None:
                    raise SiteRenderDefect(f"{i['price']} reached the renderer without a price in the sheet")
                items.append({'name': _sub(i['name'], sheet), 'price': price['span'],
                              **({'desc': _sub(i['desc'], sheet)} if i.get('desc') else {})})
            groups.append({'title': _sub(g['title'], sheet), 'items': items})
        c['pricelist'] = {**_head(s, 'pricelist', sheet, outline_titles), 'groups': groups}
    if 'contact' in sec:
        s = sec['contact']
        contact = _head(s, 'contact', sheet, outline_titles)
        if s.get('topics') and sheet.whatsapp:
            contact['topics'] = [_sub(t, sheet) for t in s['topics']]
        c['contact'] = contact
    keys = list(order) if order is not None else [k for k, _ in L.ORDER]       # the menu follows the page
    c['nav'] = [(k, outline_titles.get(k) or _sub(sec[k]['nav'], sheet)) for k in keys if k in sec and k in _NAV]
    return c


_NAV = ('services', 'pricelist', 'about', 'process', 'testimonials', 'faq', 'contact')


def binds(sheet, contract: dict, year: str) -> dict:
    return {'brief': sheet.prompt_sha256, 'canon': sheet.canon_hash, 'contract': contract['fingerprint'],
            'renderer': RENDERER_VERSION, 'year': year}


def render(doc: dict, sheet, contract: dict, *, expect_fp: str, direction: str, year: str, outline_titles: dict,
           order: list[str] | None, windows, legal: bool = False) -> tuple[str, list[str]]:
    """(html, skipped). The contract must be the one the route locked; `windows` are the route's approved windows
    (Route.windows: the library renders them); `legal`: the business has a domain, so the footer links to the legal
    page. Anything the library refuses is a platform defect, raised as SiteRenderDefect -- never filled in."""
    if contract.get('fingerprint') != expect_fp:
        raise SiteRenderDefect(f"design contract {contract.get('fingerprint')} is not the route's {expect_fp}")
    content = to_library(doc, sheet, direction=direction, year=year, outline_titles=outline_titles, order=order,
                         legal=legal)
    try:
        return L.page(content, contract, order=order, windows=windows)
    except (KeyError, ValueError, TypeError) as exc:
        raise SiteRenderDefect(f'the section library refused the content: {type(exc).__name__}: {exc}') from exc


def legal_files(doc: dict, sheet, contract: dict, html: str, *, domain: dict | None, direction: str, year: str,
                outline_titles: dict, order: list[str] | None) -> dict[str, str]:
    """The legal page and its data ({} without a domain), from the rendered home page: what the site collects is read
    from it. The same facts as the home page, so a repair round that re-renders the home page re-writes these too."""
    if domain is None:
        return {}
    content = to_library(doc, sheet, direction=direction, year=year, outline_titles=outline_titles, order=order,
                         legal=True)
    try:
        return LEGAL.files(domain, content, html, contract)
    except (KeyError, ValueError, TypeError) as exc:
        raise SiteRenderDefect(f'the legal page was refused: {type(exc).__name__}: {exc}') from exc


def check_binds(stored: dict, expected: dict) -> None:
    if stored != expected:
        diff = sorted(k for k in set(stored) | set(expected) if stored.get(k) != expected.get(k))
        raise SiteRenderDefect(f'content/site.json is bound to another build ({", ".join(diff)} differ): stale content '
                               'is never rendered')


# ---- the repository ---------------------------------------------------------------------------------------------------
APP_PY = '''"""The site's server (written by 148AI, the same in every build): the standard library only. GET / and
/index.html serve public/index.html, and /legal.html serves public/legal.html when the build has one; every other
path is 404; every method that would send data is 405. Nothing a visitor sends is read or stored; the server writes
nothing. Each request is logged to stderr."""
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = {"/": "index.html", "/index.html": "index.html", "/legal.html": "legal.html"}


class Handler(BaseHTTPRequestHandler):
    server_version = "148ai-site/1"

    def _page(self, body):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        page = os.path.join(ROOT, "public", PAGES.get(path, "-"))
        if path not in PAGES or not os.path.isfile(page):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "9")
            self.end_headers()
            if body:
                self.wfile.write(b"not found")
            return
        with open(page, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if body:
            self.wfile.write(data)

    def do_GET(self):
        self._page(True)

    def do_HEAD(self):
        self._page(False)

    def _refuse(self):
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\\n" % (self.address_string(), fmt % args))


def make_server(port):
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


if __name__ == "__main__":
    make_server(int(os.environ.get("PORT", "8000"))).serve_forever()
'''

TEST_SITE = '''"""The site's tests (written by 148AI, the same in every build): they read content/facts.json -- the facts the
customer gave, the customer's section names in order, the design contract's token -- and check the page the server
serves. Nothing here is written by a model."""
import html
import json
import os
import re
import threading
import unittest
import urllib.error
import urllib.request

import app

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = json.load(open(os.path.join(ROOT, "content", "facts.json"), encoding="utf-8"))


def visible(page):
    page = re.sub(r"(?s)<(script|style)\\b.*?</\\1>", " ", page)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", page)).split())


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.make_server(0)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        with urllib.request.urlopen(cls.base + "/", timeout=10) as r:
            cls.status, cls.ctype, cls.page = r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8")
        # what a visitor reads: the body only (the head's JSON-LD and meta tags repeat the facts), scripts removed
        cls.text = visible(cls.page.split("</head>", 1)[-1])
        main = re.search(r"(?s)<main\\b.*?</main>", cls.page)
        cls.main = visible(main.group(0)) if main else ""

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_the_home_page_is_served_right_to_left_and_responsive(self):
        self.assertEqual(self.status, 200)
        self.assertIn("text/html", self.ctype)
        self.assertIn('<html lang="he" dir="rtl">', self.page)
        self.assertIn('name="viewport"', self.page)

    def test_every_fact_the_customer_gave_is_shown_as_written(self):
        missing = [s for s in FACTS["spans"] if " ".join(s.split()) not in self.text]
        self.assertEqual(missing, [])

    def test_the_customers_sections_are_in_the_customers_order(self):
        # read inside <main>: the header menu lists every name in order whatever the sections' order is
        at = [self.main.find(name) for name in FACTS["order"]]
        self.assertNotIn(-1, at)
        self.assertEqual(at, sorted(at))

    def test_the_page_carries_the_design_contract(self):
        if FACTS["contract_token"]:
            self.assertIn(FACTS["contract_token"], self.page)

    def test_the_legal_page_is_served_when_the_build_has_one_and_the_home_page_links_to_it(self):
        has = os.path.isfile(os.path.join(ROOT, "public", "legal.html"))
        linked = 'href="legal.html"' in self.page
        self.assertEqual(has, linked)
        try:
            with urllib.request.urlopen(self.base + "/legal.html", timeout=10) as r:
                legal = r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as caught:
            legal = caught.code, ""
        if has:
            self.assertEqual(legal[0], 200)
            self.assertIn("זה לא ייעוץ משפטי", visible(legal[1]))
        else:
            self.assertEqual(legal[0], 404)

    def test_nothing_a_visitor_sends_is_accepted(self):
        for method in ("POST", "PUT", "DELETE"):
            req = urllib.request.Request(self.base + "/", data=b"x=1", method=method)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(caught.exception.code, 405)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + "/api/records", timeout=10)
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
'''

README = '''# {name}

אתר תדמית שנבנה ב-148AI מתוך מסמך תוכן מאומת (`content/site.json`) וספריית הסקשנים של הפלטפורמה.

- `public/index.html` -- העמוד, כפי שהשרת מגיש אותו.
- `app.py` -- שרת בספרייה הסטנדרטית בלבד: GET בלבד, שום דבר לא נשמר.
- `tests/test_site.py` -- בדיקות שהעובדות שנתתם מופיעות בעמוד כפי שכתבתם אותן.
'''


def facts_json(sheet, spec_ids: list[str], contract: dict, order_names: list[str]) -> str:
    token = f"--color-primary: {contract['tokens']['--color-primary']}"
    return json.dumps({'spans': sheet.spans(), 'order': order_names, 'contract_token': token,
                       'acceptance_ids': spec_ids}, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def project_json(sheet, spec_ids: list[str], contract: dict) -> str:
    """The build and verification contract: one verify entry (the fixed tests) covering every acceptance id, and a
    behaviour plan of the three kinds a content-only site has (data_read, responsive, api_smoke)."""
    # each fact as the library writes it in a text node (L.e: "250 ₪" keeps its shekel sign with a no-break space);
    # a time range is wrapped in <bdi> on the page, so it is asserted by the fixed tests on the visible text instead
    literal = [L.e(s) for s in sheet.spans() if not _TIME.search(s)]
    token = f"--color-primary: {contract['tokens']['--color-primary']}"
    steps = [
        {'id': 'S1', 'kind': 'data_read', 'acceptance_ids': spec_ids, 'method': 'GET', 'path': '/',
         'expect_status': 200, 'expect_text_contains': literal + [token]},
        {'id': 'S2', 'kind': 'responsive', 'acceptance_ids': spec_ids, 'method': 'GET', 'path': '/',
         'expect_status': 200, 'expect_text_contains': ['name="viewport"', 'width=device-width']},
        {'id': 'S3', 'kind': 'api_smoke', 'acceptance_ids': spec_ids, 'method': 'GET', 'path': '/',
         'expect_status': 200},
    ]
    data = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
            'health_path': '/', 'build': [['python', '-m', 'compileall', '-q', '.']],
            'verify': [{'name': 'site tests', 'argv': ['python', '-m', 'pytest', '-q', 'tests'],
                        'acceptance_ids': spec_ids}],
            'site_route': 'section_library/1',
            'web_saas_acceptance': {'product_family': 'managed_web_saas_v1',
                                    'required_kinds': ['data_read', 'responsive', 'api_smoke'],
                                    'personas': [{'id': 'visitor', 'steps': steps}]}}
    return json.dumps(data, ensure_ascii=False, indent=1) + '\n'


def site_json(doc: dict, bound: dict) -> str:
    return json.dumps({'document': doc, 'binds': bound}, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def repository(doc: dict, sheet, html: str, *, spec, contract: dict, bound: dict, order_names: list[str],
               legal: dict[str, str] | None = None) -> dict:
    """The build's files. `legal`: the legal page and its data (legal_files), written beside the home page."""
    ids = [a.id for a in spec.acceptance]
    name = sheet.name or doc['name']
    return {'app.py': APP_PY, PAGE: html, SITE_JSON: site_json(doc, bound),
            FACTS_JSON: facts_json(sheet, ids, contract, order_names), 'tests/test_site.py': TEST_SITE,
            '.omni/project.json': project_json(sheet, ids, contract), 'README.md': README.format(name=name),
            **(legal or {})}
