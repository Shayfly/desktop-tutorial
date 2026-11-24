"""The section library renders the cookie banner itself (the owner, DECISIONS.md question 14 (b), 2026-11-22).

Before: any approved window sent a content site to the old path (site_content.decide: 'approved_windows: ...'), because
the library rendered none of window_catalog's eight windows -- and the cookie banner is offered to every site. Now the
library renders the cookie banner deterministically (no model), so a content site whose customer approved only it takes
the new engine; every other approved window still goes legacy, named in the reason.

The base prompt is the owner's law-firm brief, a production row read read-only (tests/fixtures/
site_content_bld_b0eb47a5.json, fingerprint asserted in test_site_content_render.py), with the approval lines the
discovery writes into the brief (window_catalog.prompt_lines, then rejected_lines for the windows not approved).
Every page here is rendered on the route's own path:
decide() -> Route -> render.render(..., windows=route.windows), the call the content generator makes.

Where the banner sits: IN THE PAGE FLOW, above the header, never fixed. Measured before choosing (2026-11-22, local
Chromium, 390x844 phone): a bar fixed to the bottom covered the hero panel's phone link of this very brief (y 818-838),
and the production visual check (visual_qa 'overlap', enforced) reported two overlaps -- the build would have failed.
In the flow the banner cannot cover the main call to action or the phone action bar (fixed at the bottom), whatever the
content; the Chromium tests below measure it, and the real chain builds the brief ready in round 0."""
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import section_library as L
from omni_prod import site_content as SC
from omni_prod import skill_units as U
from omni_prod import window_catalog as W
from omni_prod.g_apple import static
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from omni_prod.skill_units.gate import WORKER_GATES
from omni_prod.skill_units.gate import check as gate_check
from omni_prod.skills_runtime import _invented_contact
from tests.test_site_content_engine import CHROMIUM

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
OWNER = {'user_id': 'usr_owner_test'}
CUT = 45_000
URL = 'http://site.test/'


# The owner's brief rejected all eight windows; its last line is the one discovery writes for that. A brief that
# approves some is written the way discovery.requirements_text writes it: the approved windows' spec, then the
# rejected rest.
REJECTED_ALL = W.rejected_lines(list(W.CATALOG))[0]
if PROMPT.count(REJECTED_ALL) != 1:
    raise AssertionError('the fixture no longer carries the line that rejects every window')


def approving(*windows) -> str:
    """The owner's brief as discovery writes it when the customer approved these windows and rejected the rest."""
    lines = W.prompt_lines(list(windows)) + W.rejected_lines([w for w in W.CATALOG if w not in windows])
    return PROMPT.replace(REJECTED_ALL, '\n'.join(lines))


COOKIE = approving('cookie_banner')


def decide(prompt: str):
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
        return SC.decide(prompt, OWNER, year='2026')


def page_of(route) -> str:
    """The page as the content generator renders it (agents.ContentSiteGenerator._render), from the route's fields."""
    return R.render(FIXTURE['scripted_content'], Fx.fact_sheet(route.prompt), route.contract,
                    expect_fp=route.contract_fp, direction=route.direction, year=route.year,
                    outline_titles=route.outline_titles, order=route.order, windows=route.windows)[0]


def banner_markup(html: str) -> str:
    m = re.search(r'<div class="cookie-banner"[^>]*>.*?</div></div>', html, re.S)
    if not m:
        raise AssertionError('no cookie banner on the page')
    return m.group(0)


def banner_script(html: str) -> str:
    m = re.search(r'<div class="cookie-banner".*?</div></div><script>(.*?)</script>', html, re.S)
    if not m:
        raise AssertionError('no script right after the cookie banner')
    return m.group(1)


def css_px(value: str) -> float:
    m = re.fullmatch(r'(\d+(?:\.\d+)?)(px|rem)', value.strip())
    if not m:
        raise AssertionError(f'a size this test cannot read: {value!r}')
    return float(m.group(1)) * (16 if m.group(2) == 'rem' else 1)


class TheRoute(unittest.TestCase):
    def test_a_content_site_that_approved_only_the_cookie_banner_takes_the_library(self):
        route = decide(COOKIE)
        self.assertEqual((route.route, route.reason, route.windows), ('section_library', 'all preconditions hold',
                                                                      ('cookie_banner',)))
        self.assertEqual(route.to_dict()['windows'], ['cookie_banner'])          # in the build evidence
        self.assertEqual(decide(PROMPT).windows, ())

    def test_every_other_approved_window_still_goes_legacy_by_name(self):
        for other in [w for w in W.CATALOG if w != 'cookie_banner']:
            with self.subTest(other):
                self.assertEqual(decide(approving(other)).reason, f'approved_windows: {other}')
                self.assertEqual(decide(approving('cookie_banner', other)).reason, f'approved_windows: {other}')
        route = decide(approving('cookie_banner', 'question_widget', 'promo_bar'))
        self.assertEqual((route.route, route.reason), ('legacy', 'approved_windows: question_widget, promo_bar'))

    def test_the_library_renders_exactly_the_cookie_banner_and_refuses_any_other_window(self):
        self.assertEqual(L.RENDERED_WINDOWS, frozenset({'cookie_banner'}))
        self.assertLessEqual(L.RENDERED_WINDOWS, set(W.CATALOG))
        route = decide(PROMPT)
        for windows in (['question_widget'], ['cookie_banner', 'cookie_banner'], ['popunder']):
            with self.subTest(windows):
                with self.assertRaises(R.SiteRenderDefect):       # never dropped silently, never rendered half
                    R.render(FIXTURE['scripted_content'], Fx.fact_sheet(PROMPT), route.contract,
                             expect_fp=route.contract_fp, direction=route.direction, year=route.year,
                             outline_titles=route.outline_titles, order=route.order, windows=windows)


class TheBannerOnThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.route = decide(COOKIE)
        cls.html = page_of(cls.route)
        cls.plain = page_of(decide(PROMPT))

    def test_the_window_probe_finds_no_failure(self):
        result = W.probe(self.html, ['cookie_banner'])
        self.assertEqual(result['failures'], [])
        self.assertIn('cookie_banner: close button', result['checked'])
        self.assertIn('page: dir=rtl', result['checked'])

    def test_every_control_answers_closes_and_is_named(self):
        root = W.window_roots(self.html)
        self.assertEqual([(wid, a.get('role'), a.get('aria-label')) for _, wid, a in root],
                         [('cookie_banner', 'region', 'הודעת עוגיות')])
        buttons = [W._attrs(raw) for raw in re.findall(r'<button\b([^>]*)>', banner_markup(self.html))]
        self.assertEqual([b.get(W.CLOSE_ATTR) for b in buttons], ['accept', 'necessary', 'necessary'])
        names = re.findall(r'<button\b[^>]*>([^<]*)<', banner_markup(self.html))
        self.assertEqual(names[:2], ['אישור', 'רק הכרחי'])
        self.assertEqual(buttons[2].get('aria-label'), 'סגירת ההודעה')
        self.assertTrue(all(b.get('type') == 'button' for b in buttons))

    def test_every_control_is_at_least_44_css_px(self):
        """The catalogue's rule (every button at least 44x44 CSS px), read from the page's own CSS: the rules that
        reach each of the banner's buttons by its classes (alone, or under the banner's root class)."""
        rules = [(' '.join(s.split()), decls) for sel, decls in static.rules_of(self.html) for s in sel.split(',')]
        for raw in re.findall(r'<button\b([^>]*)>', banner_markup(self.html)):
            classes = set(W._attrs(raw).get('class', '').split())
            size = {'min-width': 0.0, 'min-height': 0.0}
            for sel, decls in rules:
                *ancestors, last = sel.split(' ')
                if re.fullmatch(r'(\.[\w-]+)+', last) and set(last[1:].split('.')) <= classes \
                        and all(a == '.cookie-banner' for a in ancestors):
                    for prop, value in decls:
                        if prop in size:
                            size[prop] = max(size[prop], css_px(value))
            with self.subTest(sorted(classes)):
                self.assertGreaterEqual(size['min-width'], 44)
                self.assertGreaterEqual(size['min-height'], 44)

    def test_it_is_hidden_until_its_script_shows_it_and_the_answer_is_kept_for_the_visit(self):
        root = [a for _, wid, a in W.window_roots(self.html) if wid == 'cookie_banner'][0]
        self.assertIn('hidden', root)                          # no script, no banner: nothing a visitor cannot close
        js = banner_script(self.html)
        self.assertRegex(js, r'try\{[^{}]*sessionStorage\.getItem\(k\)')        # read inside try: a refused storage
        self.assertRegex(js, r'try\{[^{}]*sessionStorage\.setItem\(k,')         # written inside try: never throws
        self.assertIn('if(!a)b.hidden=false', js)
        self.assertNotIn(W.CLOSE_ATTR, js)            # only the controls themselves satisfy the probe's close rule

    def test_it_sits_in_the_page_flow_above_the_header_never_over_the_phone_bar(self):
        """The banner is the first thing in the page after the skip link, and nothing positions it: it takes its own
        room at the top of the document. The phone action bar is fixed to the bottom of the screen. So the banner
        can never be drawn over the bar or over the main call to action, whatever the content."""
        self.assertRegex(self.html, r'<body[^>]*><a class="skip" href="#main">[^<]*</a><div class="cookie-banner"')
        self.assertLess(self.html.index('data-148-window="cookie_banner"'), self.html.index('<header'))
        positioning = re.compile(r'^(position|inset(-[a-z-]+)?|top|bottom|left|right|transform|translate|float|'
                                 r'margin(-block)?(-start|-end)?)$')
        on_root = [(sel, prop, value) for sel, decls in static.rules_of(self.html) for s in sel.split(',')
                   for prop, value in decls
                   if re.search(r'(\.cookie-banner|#cookie-banner|\[data-148-window[^\]]*\])$', s.strip())
                   and positioning.match(prop)]
        self.assertEqual(on_root, [])
        bar = {p: v for sel, decls in static.rules_of(self.html) if sel.strip() == '.mobile-bar' for p, v in decls}
        self.assertEqual((bar.get('position'), bar.get('bottom')), ('fixed', '0'))

    def test_without_the_approval_the_page_has_no_window(self):
        self.assertEqual(W.window_roots(self.plain), [])
        for trace in ('cookie-banner', L.COOKIE_KEY, 'sessionStorage', W.CLOSE_ATTR):
            self.assertNotIn(trace, self.plain)                   # no markup, no style, no script
        self.assertEqual([f['code'] for f in W.probe(self.plain, ['cookie_banner'])['failures']], ['WINDOW_MISSING'])

    def test_the_page_still_passes_every_gate_that_judges_a_page(self):
        self.assertEqual(static.check(self.html, self.route.contract), [])
        units = [d for d in os.listdir(os.path.dirname(U.__file__))
                 if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_')]
        self.assertEqual({u: r for u in units if (r := U.run(u, self.html)).get('status') != 'pass'}, {})
        self.assertEqual({g: f for g in WORKER_GATES if (f := gate_check(g, {R.PAGE: self.html})['failures'])}, {})
        self.assertEqual(_invented_contact({R.PAGE: self.html}, {'request': COOKIE}), [])
        self.assertLess(len(self.html), CUT)


def _context(browser, width=390, height=844, mobile=True, **extra):
    ctx = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=mobile, has_touch=mobile,
                              device_scale_factor=1, locale='he-IL', **extra)
    return ctx


@unittest.skipUnless(CHROMIUM, 'the banner is measured in a local Chromium (playwright)')
class InChromium(unittest.TestCase):
    """Served over http (sessionStorage needs an origin); the Google Fonts link is removed (offline)."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.html = re.sub(r'<link[^>]+fonts\.g[^>]+>', '', page_of(decide(COOKIE)))
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def open(self, ctx):
        ctx.route(URL, lambda r: r.fulfill(body=self.html, content_type='text/html; charset=utf-8'))
        pg = ctx.new_page()
        pg.goto(URL, wait_until='load')
        return pg

    @staticmethod
    def shown(pg) -> bool:
        return pg.evaluate('!document.getElementById("cookie-banner").hidden')

    def test_the_production_visual_check_finds_nothing_it_enforces_with_the_banner_open(self):
        from omni_prod import visual_qa as VQ
        audit_js = re.search(r'AUDIT = r"""(.*?)"""', VQ.SCRIPT, re.S).group(1)      # the sandbox script's own audit
        found, open_ = {}, {}
        for name, v in VQ.VIEWPORTS.items():
            ctx = _context(self.browser, v['width'], v['height'], v['mobile'])
            try:
                pg = self.open(ctx)
                pg.wait_for_timeout(1200)                     # the production audit's settle time
                open_[name] = self.shown(pg)
                found[name] = [f"{f['kind']} {f['at']} {f['detail']}" for f in pg.evaluate(audit_js, v['mobile'])
                               ['findings'] if f['kind'] in VQ.DEFAULT_ENFORCED]
            finally:
                ctx.close()
        self.assertEqual(open_, {'desktop': True, 'mobile': True})
        self.assertEqual(found, {'desktop': [], 'mobile': []})

    def test_on_a_phone_it_takes_at_most_a_quarter_and_never_covers_the_bar_or_the_main_action(self):
        ctx = _context(self.browser, reduced_motion='reduce')      # the bar's slide is instant: measured, not mid-way
        try:
            pg = self.open(ctx)
            first = pg.evaluate('''() => {
                const b = document.getElementById('cookie-banner'), r = b.getBoundingClientRect();
                const cta = document.querySelector('#top .actions .btn-primary').getBoundingClientRect();
                return {position: getComputedStyle(b).position, height: r.height, quarter: innerHeight / 4,
                        cta_covered: cta.top < r.bottom && cta.bottom > r.top, cta_on_screen: cta.bottom <= innerHeight,
                        controls: [...b.querySelectorAll('button')].map(x => {
                            const q = x.getBoundingClientRect(); return [q.width >= 44, q.height >= 44]; })}; }''')
            self.assertEqual(first['position'], 'static')
            self.assertLessEqual(first['height'], first['quarter'])
            self.assertEqual((first['cta_covered'], first['cta_on_screen']), (False, True))
            self.assertEqual(first['controls'], [[True, True]] * 3)
            total = pg.evaluate('document.documentElement.scrollHeight')
            steps, bar_seen, over = 0, 0, []
            for y in range(0, total, 400):                     # bounded by the page's own height
                steps += 1
                pg.evaluate(f'window.scrollTo({{top: {y}, behavior: "instant"}})')
                pg.wait_for_timeout(150)                      # the bar's IntersectionObserver answers
                o = pg.evaluate('''() => { const r = document.getElementById('cookie-banner').getBoundingClientRect();
                    const bar = document.querySelector('.mobile-bar'), s = getComputedStyle(bar);
                    const q = bar.getBoundingClientRect();
                    const cta = document.querySelector('#top .actions .btn-primary').getBoundingClientRect();
                    const hit = (a, b) => a.top < b.bottom && a.bottom > b.top && a.left < b.right && a.right > b.left;
                    const shown = s.display !== 'none' && s.visibility !== 'hidden';
                    return {bar: shown, over_bar: shown && hit(r, q), over_cta: hit(r, cta)}; }''')
                bar_seen += o['bar']
                if o['over_bar'] or o['over_cta']:
                    over.append((y, o))
            self.assertTrue(self.shown(pg))                   # still unanswered: the whole walk had the banner open
        finally:
            ctx.close()
        self.assertGreater(steps, 3)
        self.assertGreater(bar_seen, 0)                       # the walk did reach the screens where the bar shows
        self.assertEqual(over, [])
        small = {}
        for width, height in ((320, 568), (360, 640)):        # the smallest phones still in use take it too
            ctx = _context(self.browser, width, height)
            try:
                small[(width, height)] = self.open(ctx).evaluate(
                    'document.getElementById("cookie-banner").getBoundingClientRect().height <= innerHeight / 4')
            finally:
                ctx.close()
        self.assertEqual(small, {(320, 568): True, (360, 640): True})

    def test_an_answer_hides_it_and_it_stays_hidden_after_a_reload(self):
        answers = {}
        for name in ('אישור', 'רק הכרחי', 'סגירת ההודעה'):
            ctx = _context(self.browser)
            try:
                pg = self.open(ctx)
                errors = []
                pg.on('pageerror', lambda exc: errors.append(str(exc)))
                self.assertTrue(self.shown(pg), name)
                pg.get_by_role('button', name=name, exact=True).click()
                hidden_now = not self.shown(pg)
                answers[name] = pg.evaluate(f'sessionStorage.getItem("{L.COOKIE_KEY}")')
                pg.reload(wait_until='load')
                pg.wait_for_timeout(200)
                self.assertEqual((hidden_now, self.shown(pg), errors), (True, False, []), name)
                fresh = self.open(ctx)                        # another tab of the same browser: a new visit
                self.assertTrue(self.shown(fresh), name)
            finally:
                ctx.close()
        self.assertEqual(answers, {'אישור': 'accept', 'רק הכרחי': 'necessary', 'סגירת ההודעה': 'necessary'})

    def test_a_storage_the_browser_refuses_still_shows_it_and_an_answer_still_hides_it(self):
        ctx = _context(self.browser)
        ctx.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() { throw new Error('denied'); }});")
        try:
            pg = self.open(ctx)
            errors = []
            pg.on('pageerror', lambda exc: errors.append(str(exc)))
            self.assertTrue(self.shown(pg))
            pg.get_by_role('button', name='אישור', exact=True).click()
            self.assertEqual((self.shown(pg), errors), (False, []))
        finally:
            ctx.close()


@unittest.skipUnless(CHROMIUM, 'the browser stages need a local Chromium (playwright)')
class TheRealChain(unittest.TestCase):
    """The owner's brief with the cookie banner approved, through the REAL engine and the REAL production verification
    chain in the worker's install order (tests/test_site_content_engine.build_engine: the window gate, every
    WORKER_GATES unit, G-APPLE, visual QA in Chromium...). Only the model is scripted."""

    def test_ready_in_round_0_with_the_window_gate_satisfied(self):
        from omni_prod.behavior_acceptance import find_in_chain
        from tests import test_site_content_engine as E
        with mock.patch.dict(os.environ, E.ENV), mock.patch.object(E, 'PROMPT', COOKIE):
            for key in ('OMNI_GATE_HE', 'OMNI_VISUAL_QA_ENFORCE', 'OMNI_GATE_SITE_PARITY'):
                os.environ.pop(key, None)
            gw = E.ScriptedGateway()
            engine, prompt = E.build_engine(gw)
            result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds, result.stop_reason), ('ready', 0, 'passed'),
                         [f'{f.acceptance_id}: {f.message[:200]}' for f in result.report.failures])
        self.assertEqual(gw.roles().count('content'), 1)
        evidence = SC.report(engine)
        self.assertEqual((evidence['route'], evidence['windows']), ('section_library', ['cookie_banner']))
        gate = find_in_chain(engine.executor, W.WindowGateExecutor)
        self.assertEqual((gate.approved, gate.last_windows['failures']), (['cookie_banner'], []))
        self.assertEqual([wid for _, wid, _ in W.window_roots(result.repository[R.PAGE])], ['cookie_banner'])


if __name__ == '__main__':
    unittest.main()
