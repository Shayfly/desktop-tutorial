"""The rehearsal gives the review the approved request, as the worker does (rehearsal 44043708644, the butcher,
2026-11-17: without it the fact canon was empty, the customer's own opening hours were "invented", and the build paid
a repair round for it). The real ProductReviewExecutor and the real page-locale transform are installed here."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import rehearsal as R
from omni_prod.product_review import ProductReviewExecutor

BUTCHER = ('אתר תדמית בעברית לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456. שעות פתיחה: ראשון עד '
           'חמישי 8:00 עד 19:00, שישי 7:00 עד 14:00.')
ROOT = Path(__file__).resolve().parent.parent


class Stop(Exception):
    pass


class _Inner:
    def execute(self, *, repository, spec):
        raise AssertionError('not reached')


def run_until_the_build(prompt):
    review = ProductReviewExecutor(_Inner(), gateway=None, max_reviews=1)
    engine = SimpleNamespace(executor=review, architect=None)

    def build(given):
        engine.given = given
        raise Stop('the build itself is not part of this test')
    engine.build = build
    with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
        report = R.run(prompt)
    return engine, review, report


class TheReviewGetsTheRequest(unittest.TestCase):
    def test_the_canon_of_the_review_is_the_customers_request(self):
        engine, review, report = run_until_the_build(BUTCHER)
        self.assertIs(report['review_request_installed'], True)
        self.assertEqual(review._request, BUTCHER)
        self.assertNotIn('request_installs_error', report)
        # what the missing step cost: with the request, the customer's own hours are in the canon the review reads
        from omni_prod.fact_canon import build_canon
        from omni_prod.opening_hours import compare, decode, parse
        page = 'ראשון 08:00-19:00, שני 08:00-19:00, שלישי 08:00-19:00, רביעי 08:00-19:00, חמישי 08:00-19:00, שישי 07:00-14:00'
        self.assertEqual(compare(parse(page), decode(build_canon(review._request).values('hours_day'))), ([], []))
        self.assertEqual(len(compare(parse(page), decode(build_canon('').values('hours_day')))[0]), 6)

    def test_a_hebrew_request_gets_the_right_to_left_rule(self):
        engine, _, _ = run_until_the_build(BUTCHER)
        transform = getattr(engine, 'repository_transform', None)
        # the transform itself writes dir="rtl" (another transform, e.g. the share preview, is not enough)
        self.assertIn('dir="rtl"', transform({'index.html': '<html><body><p>x</p></body></html>'})['index.html'])

    def test_an_engine_without_a_review_says_so(self):
        engine = SimpleNamespace(executor=_Inner(), architect=None, build=mock.Mock(side_effect=Stop('x')))
        with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
            report = R.run(BUTCHER)
        self.assertIs(report['review_request_installed'], False)

    def test_it_is_installed_before_the_gates_as_in_the_worker(self):
        source = (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertLess(source.index('install_review_request(engine, prompt)'), source.index('install_all(engine)'))
        self.assertLess(source.index('install_page_locale(engine, prompt)'),
                        source.index('install_review_request(engine, prompt)'))


class TheContentRouteIsInstalledAsInTheWorker(unittest.TestCase):
    """The content-document route (omni_prod/site_content) is decided in the rehearsal exactly where the worker decides
    it -- right after the components, before any install that wraps the architect -- so a calibration build exercises
    the route a customer's build takes."""

    def test_it_is_installed_first_in_the_rehearsal_and_in_the_worker(self):
        rehearsal = (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        worker = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertLess(rehearsal.index('engine, gateway = _live_components()'), rehearsal.index('site_content.install('))
        self.assertLess(rehearsal.index('site_content.install('), rehearsal.index('install_page_locale(engine, prompt)'))
        self.assertLess(worker.index('engine, gateway = components_factory()'), worker.index('site_content.install('))
        self.assertLess(worker.index('site_content.install('), worker.index('install_uploaded_assets(engine'))
        self.assertLess(worker.index('site_content.install('), worker.index('install_page_locale(engine, prompt)'))

    def test_with_the_flag_off_the_rehearsal_says_legacy_and_why(self):
        import os
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'off'}):
            engine, _, report = run_until_the_build(BUTCHER)
        self.assertEqual((report['site_route']['route'], report['site_route']['reason']), ('legacy', 'flag_off'))
        self.assertIsNone(engine.architect)

    def test_with_the_flag_on_the_owners_brief_takes_the_route_and_the_wrappers_go_around_it(self):
        import json
        import os
        from omni_prod.site_content.agents import ContentSiteGenerator, ContentSpecArchitect
        prompt = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json')
                            .read_text(encoding='utf-8'))['prompt']
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            engine, _, report = run_until_the_build(prompt)
        self.assertEqual(report['site_route']['route'], 'section_library')
        self.assertIsInstance(engine.generator, ContentSiteGenerator)
        architect, seen = engine.architect, []
        for _ in range(12):                        # the request installs wrap the route's architect, as in the worker
            seen.append(type(architect).__name__)
            if isinstance(architect, ContentSpecArchitect):
                break
            architect = architect._inner
        self.assertEqual(seen[-1], 'ContentSpecArchitect')
        self.assertIn('FactsArchitect', seen)


if __name__ == '__main__':
    unittest.main()
