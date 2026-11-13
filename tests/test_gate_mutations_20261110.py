"""Meta-verification (Michael 2026-11-10): we test the testers.

Two fixture sets, one summary line:
  MUTATIONS       -- the product is broken on purpose; the gates MUST catch it (kill ratio must be 100%).
  FALSE_POSITIVES -- the product is fine; the gates MUST pass (yesterday's "בטלפון" class: a gate that over-blocks
                     burns repair rounds exactly like one that misses).
Every production gate failure that reached a customer becomes a fixture here the same day.
"""
import json
import os
import unittest
from decimal import Decimal

from omni_prod.fact_canon import build_canon, norm_address, phone_e164, validate_canon
from omni_prod.preview_smoke import _rendered_pages
from omni_prod.skills_runtime import static_findings

REQUEST = ('דף נחיתה לבית קפה "בוקר טוב" בחיפה. טלפון 050-123-4567, כתובת רחוב הנביאים 12 חיפה, '
           'פתוח א-ה 07:00-14:00. נשמח לראות אתכם, מגיעים גם בטלפון. צבעים חום, קרם וירוק.')

GOOD_PAGE = '''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>קפה בוקר טוב</title>
<style>:root{--brand:#6b4226;--cream:#f5ecd9;--green:#1f7a3a;--ink:#2b2118;--radius:12px;--gap:16px}
body{margin:0;font-family:Assistant,system-ui;background:var(--cream);color:var(--ink)}
header{background:var(--brand);color:#fff;padding:24px;display:flex;justify-content:space-between;align-items:center}
h1{margin:0;font-size:28px}h2{font-size:22px;margin:24px 0 8px}.cta{background:var(--green);color:#fff;border-radius:999px;padding:12px 24px;text-decoration:none;font-weight:700;display:inline-block;min-height:44px}
main{max-width:960px;margin:0 auto;padding:24px}.menu{display:grid;gap:var(--gap);grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.item{background:#fff;border-radius:var(--radius);padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.price{color:var(--green);font-weight:700}footer{padding:24px;text-align:center;font-size:14px}
img{max-width:100%;height:auto;border-radius:var(--radius)}label{display:block;margin-bottom:4px}
input{padding:8px;border:1px solid #ccc;border-radius:8px;width:100%}@media(max-width:600px){header{padding:16px}h1{font-size:22px}}
a:focus,button:focus{outline:3px solid var(--green);outline-offset:2px}.muted{opacity:.8}.row{display:flex;gap:8px}
.badge{background:var(--green);color:#fff;border-radius:6px;padding:2px 8px;font-size:12px}
</style></head><body>
<header><h1>קפה "בוקר טוב"</h1><a class="cta" href="https://wa.me/972501234567">הזמנה ב-WhatsApp</a></header>
<main>
<h2>הקפה הכי טוב בשכונה, כבר 10 שנים</h2>
<p>בית קפה שכונתי בחיפה: פולי קפה קלויים במקום, מאפים טריים וארוחת בוקר חמה לכל המשפחה. מגיעים גם בטלפון.</p>
<img src="/static/cafe.jpg" alt="חלל בית הקפה בבוקר">
<h2>התפריט</h2>
<div class="menu"><div class="item">אספרסו כפול <span class="price">₪ 10</span></div>
<div class="item">הפוך גדול <span class="price">₪ 14</span></div><div class="item">קרואסון חמאה <span class="price">₪ 12</span></div></div>
<h2>איך מגיעים</h2>
<p>כתובת: רח' הנביאים 12, חיפה. טלפון: <a href="tel:+972-50-123-4567">050-1234567</a>. פתוח א-ה 07:00-14:00.</p>
<h2>המלצות (לדוגמה)</h2>
<blockquote>“הקפה הכי טוב בעיר” — לקוחה</blockquote><blockquote>“המאפים טריים כל בוקר” — לקוח</blockquote>
<form><label for="email">הרשמה לעדכונים</label><input id="email" type="email"></form>
</main><footer>© קפה בוקר טוב</footer></body></html>'''


def gates(page: str, *, request: str = REQUEST, repository: dict | None = None) -> list[dict]:
    """The static gates as production runs them: on the SERVED page, with the request's fact canon."""
    repo = repository if repository is not None else {'page.py': 'HTML = """' + page + '"""', 'app.py': 'pass'}
    ctx = {'request': request, 'rendered_pages': {'/': page, 'assets': ''}, 'canon': build_canon(request)}
    return [f.to_dict() for f in static_findings(repo, ctx)]


def blocking(findings) -> list[str]:
    return [f['skill'] + ': ' + f['problem'] for f in findings if f['severity'] == 'blocking']


MUTATIONS = {
    'rtl removed': (lambda p: p.replace(' dir="rtl"', ''), 'skill.text_locale'),
    'phone fabricated': (lambda p: p.replace('050-1234567', '052-9876543'), 'skill.copy_quality'),
    'whatsapp fabricated': (lambda p: p.replace('wa.me/972501234567', 'wa.me/972549990000'), 'skill.copy_quality'),
    'street fabricated': (lambda p: p.replace("רח' הנביאים 12", 'רחוב הרצל 7'), 'skill.copy_quality'),
    'testimonials unlabelled': (lambda p: p.replace('המלצות (לדוגמה)', 'המלצות'), 'skill.copy_quality'),
    # #335: the change the 'prices and hours are not phones' case used to make (a DAY's hours rewritten) is now a
    # blocking contradiction, and it is kept here as a mutation that must be caught
    'opening hours fabricated': (lambda p: p.replace('07:00-14:00', '07:30-23:45'), 'skill.copy_quality'),
    'design system removed': (lambda p: p[:p.index('<style>')] + '<style>body{margin:0}</style>' + p[p.index('</style>') + 8:],
                              'skill.visual_design'),
}

ADVISORY_MUTATIONS = {
    'alt removed': (lambda p: p.replace(' alt="חלל בית הקפה בבוקר"', ''), 'skill.accessibility'),
    'label removed': (lambda p: p.replace('<label for="email">הרשמה לעדכונים</label>', ''), 'skill.accessibility'),
    'placeholder left': (lambda p: p.replace('© קפה בוקר טוב', '[שם העסק]'), 'skill.copy_quality'),
}

FALSE_POSITIVES = {
    'the good page': lambda p: p,
    'phone in another format': lambda p: p.replace('050-1234567', '+972 50 123 4567'),
    'phone without dashes': lambda p: p.replace('tel:+972-50-123-4567', 'tel:0501234567'),
    "street with רחוב instead of רח'": lambda p: p.replace("רח' הנביאים 12", 'רחוב הנביאים 12'),
    # #335: a DAY's hours that differ from the request are now a contradiction (blocking); the time range alone,
    # with no day, is what this case checks -- it must not read as a phone
    'prices and hours are not phones': lambda p: p.replace('₪ 10', '₪ 1,234,567').replace('</body>', '<p>07:30-23:45</p></body>'),
    'word with the delete stem inside': lambda p: p.replace('מגיעים גם בטלפון', 'מגיעים גם בטלפון ומבטלים בוואטסאפ'),
    'english page sets its own direction': lambda p: p.replace('lang="he" dir="rtl"', 'lang="en" dir="ltr"'),
}

# Code-probe false positives (2026-11-10 gate regression): a correct product's SOURCE must not block either.
CODE_FALSE_POSITIVES = {
    'port from the environment': 'import os\nPORT = int(os.environ["PORT"])\nP2 = int(os.getenv("PORT", "8000"))\n',
}


class MutationTests(unittest.TestCase):
    def test_every_mutation_is_caught(self):
        killed, missed = 0, []
        for name, (mutate, skill) in MUTATIONS.items():
            found = blocking(gates(mutate(GOOD_PAGE)))
            if any(f.startswith(skill) for f in found):
                killed += 1
            else:
                missed.append(f'{name} (expected {skill}; got {found})')
        for name, (mutate, skill) in ADVISORY_MUTATIONS.items():
            found = [f['skill'] for f in gates(mutate(GOOD_PAGE))]
            if skill in found:
                killed += 1
            else:
                missed.append(f'{name} (expected advisory {skill}; got {found})')
        total = len(MUTATIONS) + len(ADVISORY_MUTATIONS)
        _annotate(f'gate mutations: {killed}/{total} killed, false positives: see next line')
        self.assertEqual(missed, [], f'gates missed {len(missed)}/{total} mutations')

    def test_no_false_positives(self):
        wrong = []
        for name, fix in FALSE_POSITIVES.items():
            found = blocking(gates(fix(GOOD_PAGE)))
            if found:
                wrong.append(f'{name}: {found}')
        _annotate(f'gate false positives: {len(FALSE_POSITIVES) - len(wrong)}/{len(FALSE_POSITIVES)} clean')
        self.assertEqual(wrong, [], 'gates blocked a correct product')


class DaylessRangeIsOutOfScope(unittest.TestCase):
    """#335, declared explicitly (Michael 2026-11-13): a time range with NO day ("07:30-23:45") is OUTSIDE the hours
    gate -- the gate checks hours per day only, and a bare range is not read as anyone's opening hours (it can be an
    event time, a happy hour, a delivery window). The 'prices and hours are not phones' case uses such a range only to
    check that it is not read as a phone; it checks nothing about hours. This test pins that scope, so widening or
    narrowing it is a visible change."""

    def test_a_dayless_range_is_not_hours(self):
        from omni_prod import opening_hours as H
        self.assertEqual(H.parse('<p>07:30-23:45</p>'), {})
        page = GOOD_PAGE.replace('</body>', '<p>07:30-23:45</p></body>')
        self.assertEqual([f for f in blocking(gates(page)) if 'hours' in f], [])


class CodeProbeFalsePositives(unittest.TestCase):
    def test_correct_source_does_not_block(self):
        for name, src in CODE_FALSE_POSITIVES.items():
            found = blocking([f.to_dict() for f in static_findings({'app.py': src}, {'request': REQUEST})])
            self.assertEqual(found, [], name)


class GatesJudgeTheServedPage(unittest.TestCase):
    """bld_1721136c (2026-11-10): dir="rtl" was in the rendered page, the gate read page.py and burned two rounds."""

    def test_page_inside_python_string_is_judged_as_served(self):
        source = GOOD_PAGE.replace(' dir="rtl"', ' dir="{direction}"')           # the source never says rtl literally
        repo = {'page.py': 'def render(direction="rtl"):\n    return """' + source + '"""\n'}
        ctx = {'request': REQUEST, 'rendered_pages': {'/': GOOD_PAGE, 'assets': ''}}
        self.assertEqual(blocking([f.to_dict() for f in static_findings(repo, ctx)]), [])

    def test_broken_served_page_fails_even_when_source_looks_fine(self):
        repo = {'page.py': 'HTML = """' + GOOD_PAGE + '"""'}                      # source has dir="rtl" ...
        ctx = {'request': REQUEST, 'rendered_pages': {'/': GOOD_PAGE.replace(' dir="rtl"', ''), 'assets': ''}}
        self.assertTrue(any('dir="rtl"' in f for f in blocking([f.to_dict() for f in static_findings(repo, ctx)])))

    def test_without_a_served_page_only_html_files_are_judged(self):
        repo = {'page.py': 'HTML = "<html><body>שלום</body></html>"', 'index.html': GOOD_PAGE}
        self.assertEqual(blocking([f.to_dict() for f in static_findings(repo, {'request': REQUEST})]), [])

    def test_template_wrapper(self):
        tpl = GOOD_PAGE.replace('<h1>קפה "בוקר טוב"</h1>', '<h1>{{ name }}</h1>').replace(' dir="rtl"', ' dir="{{ dir }}"')
        repo = {'templates/index.html': tpl, 'app.py': 'pass'}
        served_ok = {'request': REQUEST, 'rendered_pages': {'/': GOOD_PAGE, 'assets': ''}}
        served_bad = {'request': REQUEST, 'rendered_pages': {'/': GOOD_PAGE.replace(' dir="rtl"', ''), 'assets': ''}}
        self.assertEqual(blocking([f.to_dict() for f in static_findings(repo, served_ok)]), [])
        self.assertTrue(blocking([f.to_dict() for f in static_findings(repo, served_bad)]))

    def test_smoke_output_parsing(self):
        out = 'PREVIEW-SMOKE OK\nserver log\nPREVIEW-PAGE ' + json.dumps({'/': GOOD_PAGE, 'assets': 'a{}'}, ensure_ascii=False)
        pages = _rendered_pages(out)
        self.assertEqual(pages['/'], GOOD_PAGE)
        self.assertIsNone(_rendered_pages('PREVIEW-SMOKE HTTP 500\n'))
        self.assertIsNone(_rendered_pages('PREVIEW-PAGE {not json'))


class CanonTests(unittest.TestCase):
    def test_facts_from_the_request_with_sources(self):
        canon = build_canon(REQUEST)
        self.assertEqual(canon.values('phone'), {'+972501234567'})
        self.assertEqual(canon.values('address'), {'רחוב הנביאים 12 חיפה'})
        self.assertEqual(canon.values('hours'), {'א-ה 07:00-14:00'})
        self.assertTrue(all(f.source_ref in REQUEST for f in canon.facts))
        self.assertEqual(validate_canon(canon, REQUEST), [])
        self.assertEqual(len(canon.hash), 16)

    def test_same_fact_different_form(self):
        for a, b in [('03-1234567', '+972-3-1234567'), ('+972 3 123 4567', '03-1234567'), ('0501234567', '050-123-4567')]:
            self.assertEqual(phone_e164(a), phone_e164(b), (a, b))
        self.assertEqual(norm_address("רח' יפו 5"), norm_address('רחוב יפו 5'))
        self.assertEqual(norm_address('רחוב הנביאים 12, חיפה'), 'רחוב הנביאים 12 חיפה')

    def test_validator_catches_a_fact_not_in_the_brief(self):
        canon = build_canon(REQUEST)
        issues = validate_canon(canon, 'בית קפה בלי פרטים')
        self.assertTrue(any(i['code'] == 'FACT_NOT_IN_BRIEF' for i in issues))

    def test_review_runs_against_the_canon_hash(self):
        from omni_prod.product_review import ProductReviewExecutor

        class Inner:
            def execute(self, *, repository, spec):
                from omni_prod.autonomous_core import ExecutionReport
                return ExecutionReport(True, (), '')

        ex = ProductReviewExecutor(Inner(), gateway=None, request_text=REQUEST)
        ctx = ex._context(type('S', (), {'title': '', 'summary': ''})())
        self.assertEqual(ctx['canon'].values('phone'), {'+972501234567'})
        self.assertNotIn('rendered_pages', ctx)      # no preview smoke in this chain -> html files only


class QuarantineTests(unittest.TestCase):
    def test_third_identical_static_finding_is_quarantined(self):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.product_review import ProductReviewExecutor

        class Inner:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), '')

        spec = type('S', (), {'title': '', 'summary': '', 'requirements': (), 'acceptance': ()})()
        ex = ProductReviewExecutor(Inner(), gateway=None, max_reviews=6, request_text=REQUEST)
        repo = {'index.html': GOOD_PAGE.replace(' dir="rtl"', '')}
        r1 = ex.execute(repository=repo, spec=spec)
        r2 = ex.execute(repository=repo, spec=spec)
        self.assertFalse(r1.passed)
        self.assertFalse(r2.passed)                               # one repeat: a repair may simply have missed
        r3 = ex.execute(repository=repo, spec=spec)
        self.assertTrue(r3.passed)                                # third time: the gate is quarantined
        self.assertEqual(ex.gate_waste_rounds, 2)
        self.assertEqual(ex.quarantined[0]['skill'], 'skill.text_locale')
        self.assertEqual(ex.reviews[-1]['findings'][0]['classification'], 'probe_bug')


class MichaelNormalisationFixtures(unittest.TestCase):
    """Michael 2026-11-10: toE164 / normAddr fixtures, ported 1:1."""

    def test_phone_positive(self):
        from omni_prod.fact_canon import parse_phone
        for raw, want in [("03-1234567", "+97231234567"), ("+972 3 123 4567", "+97231234567"),
                          ("\u200e+972(0)3-1234567", "+97231234567"), ("00972 3 1234567", "+97231234567"),
                          ("טלפון: 03-1234567 להזמנות", "+97231234567"), ("03-1234567 שלוחה 4", "+97231234567"),
                          ("٠٣١٢٣٤٥٦٧", "+97231234567"), ("۰۵۰۱۲۳۴۵۶۷", "+972501234567"),
                          ("050-123-4567", "+972501234567"), ("+972 50 123 4567", "+972501234567")]:
            got = parse_phone(raw)
            self.assertTrue(got.ok, (raw, got))
            self.assertEqual(got.e164, want, raw)

    def test_phone_negative_with_reason(self):
        from omni_prod.fact_canon import parse_phone
        for raw, reason in [("1-800-123456", "SERVICE"), ("*1234", "SERVICE"), ("+1 415 555 0100", "NON_IL"),
                            ("03-123456", "SHORT"), ("03-12345678", "LONG"), ("06-1234567", "BAD_PREFIX"),
                            ("000-0000000", "DUMMY"), ("1234567", "AMBIGUOUS"), ("", "EMPTY")]:
            got = parse_phone(raw)
            self.assertFalse(got.ok, raw)
            self.assertEqual(got.reason, reason, raw)

    def test_address_equal_and_not_equal(self):
        from omni_prod.fact_canon import addr_matches
        for a, b in [("רח' יפו 5", "רחוב יפו 5"), ("ברחוב יפו 5", "רחוב יפו 5"), ('ר"ח יפו 5', "רחוב יפו 5"),
                     ("רחוב  יפו   5", "רחוב יפו 5"), ("יפו 5 רחוב", "רחוב יפו 5"), ("רחוב חמש", "רחוב 5"),
                     ("شارع يافا ٥", "شارع يافا 5"), ("ش. يافا 5", "شارع يافا 5")]:
            self.assertTrue(addr_matches(a, b), (a, b))
        for a, b in [("רחוב יפו 6", "רחוב יפו 5"), ("רחוב יפו", "רחוב יפו 5"), ("شارع يافا 6", "شارع يافا 5")]:
            self.assertFalse(addr_matches(a, b), (a, b))

    def test_ambiguous_number_on_page_does_not_block(self):
        page = GOOD_PAGE.replace('050-1234567', '8123456')
        self.assertEqual(blocking(gates(page)), [])
        self.assertTrue(any('do not parse' in f['problem'] for f in gates(page)))


class QuarantineSafetyTests(unittest.TestCase):
    """Michael 2026-11-10 condition 1: quarantine only on an identical DOM node; critical gates never release silently."""

    def _review(self):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.product_review import ProductReviewExecutor

        class Inner:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), '')

        class State:
            external_spend_usd = 0
            external_calls = 0

        class Gw:
            state = State()

        gw = Gw()
        ex = ProductReviewExecutor(Inner(), gateway=None, max_reviews=6, request_text=REQUEST)
        ex._gateway = gw
        return ex, gw

    def test_changed_node_is_a_product_bug_not_quarantined(self):
        ex, _ = self._review()
        spec = type('S', (), {'title': '', 'summary': '', 'requirements': (), 'acceptance': ()})()
        for attrs in ('', ' class="a"', ' class="b"'):            # the repair keeps changing the <html> tag
            r = ex.execute(repository={'index.html': GOOD_PAGE.replace(' dir="rtl"', attrs)}, spec=spec)
        self.assertFalse(r.passed)
        self.assertEqual(ex.quarantined, [])

    def test_critical_quarantine_is_flagged_and_waste_is_measured(self):
        ex, gw = self._review()
        spec = type('S', (), {'title': '', 'summary': '', 'requirements': (), 'acceptance': ()})()
        repo = {'index.html': GOOD_PAGE.replace(' dir="rtl"', '')}
        ex.execute(repository=repo, spec=spec)
        gw.state.external_spend_usd, gw.state.external_calls = 0.10, 4
        ex.execute(repository=repo, spec=spec)
        gw.state.external_spend_usd, gw.state.external_calls = 0.31, 9
        r = ex.execute(repository=repo, spec=spec)
        self.assertTrue(r.passed)
        self.assertTrue(ex.quarantined[0]['critical'])
        self.assertEqual(str(ex.gate_waste_usd), '0.31')        # spend from the first review to the quarantine
        self.assertEqual(ex.gate_waste_calls, 9)

    def test_worker_withdraws_release_and_shows_banner(self):
        from omni_prod.worker_tasks import _gate_waste, _version_message
        ex, gw = self._review()
        ex.quarantined = [{'skill': 'skill.text_locale', 'problem': 'x', 'critical': True}]
        ex.gate_waste_rounds, ex.gate_waste_usd, ex.gate_waste_calls = 2, Decimal('0.3'), 7
        engine = type('E', (), {'executor': ex})()
        gw_line = _gate_waste(engine, None, 2)
        self.assertTrue(gw_line['critical_quarantine'])
        self.assertEqual(gw_line['measured_usd'], '0.3000')
        self.assertIn('פרסום לפרודקשן חסום', gw_line['banner'])
        self.assertIn('PREVIEW ONLY', _version_message('bld_x', False, gw_line['banner']))


class SourceReadersAreDeclared(unittest.TestCase):
    """Michael 2026-11-10 condition 4: a check that reads source files must declare it, with a reason."""

    def test_every_source_reader_is_declared(self):
        import inspect
        from omni_prod import skills_runtime as sr
        undeclared, declared = [], []
        for skill in sr.WEB_SKILLS:
            for check in getattr(skill, 'static_checks', ()):
                src = inspect.getsource(check)
                if '_text_files(' in src and '_pages(' not in src:
                    (declared if getattr(check, 'reads_source', None) else undeclared).append(check.__name__)
        _annotate(f'source-reading probes: {len(declared)} declared, {len(undeclared)} undeclared')
        self.assertEqual(undeclared, [], 'declare @reads_source("<why the served page cannot show this>")')
        self.assertGreaterEqual(len(declared), 5)


class CanonOnApprovalScreen(unittest.TestCase):
    def test_incomplete_canon_is_a_visible_warning(self):
        from omni_prod.fact_canon import canon_view
        v = canon_view('דף נחיתה לבית קפה בחיפה', family='website')
        self.assertEqual(v['status'], 'CANON_INCOMPLETE')
        self.assertIn('לא נמציא', v['lines'][0])
        full = canon_view(REQUEST, family='website')
        self.assertEqual(full['status'], 'OK')
        self.assertIn('050-123-4567', full['lines'][0])
        self.assertEqual(canon_view('מערכת משימות לצוות', family='app')['status'], 'OK')


def _annotate(line: str) -> None:
    if os.getenv('GITHUB_ACTIONS'):
        print(f'::notice title=gate meta-verification::{line}')


if __name__ == '__main__':
    unittest.main()
