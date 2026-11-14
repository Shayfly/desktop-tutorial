"""Michael 2026-11-15: "שעות -- תיקון עם bdi". On the butcher page (bld_83529c13, served version v_8d8ed793) the
browser showed "07:00–19:00" as "19:00–07:00": a time range in a dir="rtl" page is laid out right-to-left unless
isolated. Real path: the page exactly as served (tests/fixtures/butcher_served_page_2026_11_14.json), judged as the
gate judges it (context['rendered_pages']['/']), and a real .html page through the engine's own repository transform
(page_locale.install). The visual order was checked in Chromium separately (PR description); CI has no browser."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.bidi_ranges import unwrapped_ranges, wrap_ranges
from omni_prod.page_locale import ensure_rtl, install
from omni_prod.probe_manifest import PROBES
from omni_prod.skills_runtime import _invented_contact, _time_ranges_isolated

SERVED = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'butcher_served_page_2026_11_14.json').read_text())
PAGE = SERVED['page']
REQUEST = SERVED['brief']['prompt']


def judged(page):
    return _time_ranges_isolated({}, {'request': REQUEST, 'rendered_pages': {'/': page}})


class TheButcherPage(unittest.TestCase):
    def test_the_served_page_has_its_hours_unisolated_and_is_blocked(self):
        self.assertEqual([t for _, t in unwrapped_ranges(PAGE)], ['07:00–19:00', '07:00–14:00'])
        found = judged(PAGE)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, 'blocking')
        self.assertIn('07:00–19:00', found[0].problem)
        self.assertIn('<bdi dir="ltr">', found[0].fix)

    def test_wrapped_it_passes_and_nothing_else_changed(self):
        fixed = wrap_ranges(PAGE)
        self.assertEqual(judged(fixed), [])
        self.assertEqual(fixed.count('<bdi dir="ltr">'), 2)
        self.assertEqual(fixed.replace('<bdi dir="ltr">', '').replace('</bdi>', ''), PAGE)
        self.assertIn('"Su-Th 07:00-19:00"', fixed)                     # JSON-LD in <script> untouched
        self.assertEqual(wrap_ranges(fixed), fixed)                      # idempotent

    def test_the_truth_gate_reads_the_hours_the_same_after_wrapping(self):
        before = _invented_contact({}, {'request': REQUEST, 'rendered_pages': {'/': PAGE}})
        after = _invented_contact({}, {'request': REQUEST, 'rendered_pages': {'/': wrap_ranges(PAGE)}})
        self.assertEqual([f.problem for f in after], [f.problem for f in before])

    def test_a_ltr_page_is_not_judged(self):
        self.assertEqual(judged(PAGE.replace('dir="rtl"', 'dir="ltr"', 1)), [])


class ByConstruction(unittest.TestCase):
    HTML = ('<!doctype html><html><head><script type="application/ld+json">{"openingHours":"Mo 07:00-19:00"}'
            '</script></head><body><p title="07:00-19:00">שעות: א׳–ה׳ 07:00–19:00, ו׳ 7:00 - 14:00</p></body></html>')

    def test_an_rtl_request_gets_isolated_ranges_through_the_engine_transform(self):
        core = SimpleNamespace(repository_transform=None)
        self.assertEqual(install(SimpleNamespace(core=core), 'אטליז בירושלים'), 'he')
        out = core.repository_transform({'index.html': self.HTML, 'app.py': 'X = "07:00-19:00"'})
        self.assertIn('<html dir="rtl" lang="he">', out['index.html'])
        self.assertIn('<bdi dir="ltr">07:00–19:00</bdi>', out['index.html'])
        self.assertIn('<bdi dir="ltr">7:00 - 14:00</bdi>', out['index.html'])
        self.assertIn('"Mo 07:00-19:00"', out['index.html'])             # script content untouched
        self.assertIn('title="07:00-19:00"', out['index.html'])           # attribute untouched
        self.assertEqual(out['app.py'], 'X = "07:00-19:00"')              # code is the served-page gate's job

    def test_a_page_that_chose_ltr_is_left_as_written(self):
        page = self.HTML.replace('<html>', '<html dir="ltr" lang="en">')
        self.assertEqual(ensure_rtl({'index.html': page}, 'he')['index.html'], page)

    def test_already_isolated_ranges_are_not_wrapped_twice(self):
        page = '<p><bdi dir="ltr">07:00–19:00</bdi> <span dir="ltr">08:00-12:00</span></p>'
        self.assertEqual(unwrapped_ranges(page), [])
        page2 = '<p><span dir="ltr">x</span> 08:00-12:00</p>'              # the ltr element closed before the range
        self.assertEqual([t for _, t in unwrapped_ranges(page2)], ['08:00-12:00'])

    def test_the_probe_is_declared_critical(self):
        self.assertEqual(PROBES['_time_ranges_isolated'], {'skill': 'skill.text_locale', 'reads_source': None,
                                                           'critical': True})


if __name__ == '__main__':
    unittest.main()
