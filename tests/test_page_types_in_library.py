"""Warehouse 123: section_library consumes the page-type skeletons (omni_prod/output_profile/page_types.json).

`page(content, contract, page_type=...)` takes the type's skeleton as its order, refuses a page without the sections the
type cannot do without, says in `skipped` what the skeleton left out, and carries data-page-type. Without the keyword the
owner's law-firm page (section_library.demo_law_firm, from production bld_b0eb47a5) is byte-identical to main c7acb59.
The registry, the detector and the threshold measure are tests/test_page_types.py.
"""
import copy
import hashlib
import re
import unittest
from unittest import mock

from omni_prod import section_library as L
from omni_prod.output_profile import page_types as PT
from omni_prod.section_library import demo_law_firm as D

# sha256 of the owner's law-firm page (section_library.demo_law_firm.build) on main c7acb59, before the keyword existed
# visual S1 (2026-11-27): LIBRARY_VERSION 2 -> 4 over main; the only byte of the demo page that differs is the body marker
# data-148-kit section-library/2 -> /4 (tests/test_direction_sketch.py DEMO_SHA is the same page)
LAW_PAGE_SHA = '3caaac236723037a4dddc8ef0e66a58317ced1a4fac4e1f1a89a379746bbe733'


class SkeletonInTheLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.contract, cls.skipped = D.build()

    def test_the_library_stops_at_import_on_a_skeleton_with_a_section_it_does_not_render(self):
        L.check_page_types()                                     # the real registry passes, as it did at import
        bad = copy.deepcopy(PT._DATA)
        bad['types']['event']['sections'].append('schedule')
        with mock.patch.object(PT, '_DATA', bad), self.assertRaisesRegex(RuntimeError, 'not in the section library'):
            L.check_page_types()
        faked = copy.deepcopy(PT._DATA)
        faked['types']['event']['not_in_library'].append('faq')
        with mock.patch.object(PT, '_DATA', faked), self.assertRaisesRegex(RuntimeError, 'but it has them'):
            L.check_page_types()

    @staticmethod
    def ids(doc):
        return re.findall(r'<section class="[^"]*" id="(\w+)"', doc[doc.index('<main'):doc.index('</main>')])

    def content(self, **extra):
        c = copy.deepcopy(D.CONTENT)
        c.update(extra)
        return c

    def test_without_a_page_type_the_owners_page_is_byte_identical_to_main(self):
        self.assertEqual(hashlib.sha256(self.doc.encode('utf-8')).hexdigest(), LAW_PAGE_SHA)
        self.assertNotIn('data-page-type', self.doc)
        self.assertEqual(L.page(D.CONTENT, self.contract, page_type=None)[0], self.doc)

    def test_the_business_skeleton_is_the_librarys_own_order(self):
        self.assertEqual(PT.skeleton('business')['sections'], [k for k, _ in L.ORDER])
        doc, skipped = L.page(D.CONTENT, self.contract, page_type='business')
        self.assertEqual(self.ids(doc), self.ids(self.doc))
        self.assertEqual(skipped, self.skipped)
        self.assertEqual(doc.replace(' data-page-type=business', ''), self.doc)

    def test_a_portfolio_page_follows_its_skeleton_and_says_what_it_left_out(self):
        gallery = {'eyebrow': 'עבודות', 'title': 'עבודות נבחרות',
                   'images': [{'src': f'assets/work-{i}.webp', 'alt': f'עבודה {i}', 'width': 800, 'height': 600}
                              for i in range(1, 4)]}
        doc, skipped = L.page(self.content(gallery=gallery), self.contract, page_type='portfolio')
        ids = self.ids(doc)
        self.assertEqual(ids[:2], ['top', 'gallery'])
        self.assertLess(ids.index('gallery'), ids.index('services'))
        self.assertLess(ids.index('services'), ids.index('about'))
        self.assertIn('data-page-type=portfolio', doc)
        self.assertIn('stats:not in the portfolio skeleton', skipped)
        self.assertNotIn('faq', ids)                               # the portfolio skeleton has no FAQ
        self.assertIn('faq:not in the portfolio skeleton', skipped)
        self.assertEqual(PT.judge('portfolio', doc), [])           # the page the skeleton made is inside its own table

    def test_a_page_type_cannot_be_built_without_the_sections_it_cannot_do_without(self):
        with self.assertRaisesRegex(ValueError, r"page type 'portfolio' cannot do without \['gallery'\]"):
            L.page(D.CONTENT, self.contract, page_type='portfolio')
        no_cta = self.content()
        del no_cta['cta']
        with self.assertRaisesRegex(ValueError, "page type 'landing' cannot do without"):
            L.page(no_cta, self.contract, page_type='landing')

    def test_an_unknown_page_type_raises(self):
        for bad in ('hologram', '', 'website'):
            with self.subTest(bad), self.assertRaises(PT.UnknownPageType):
                L.page(D.CONTENT, self.contract, page_type=bad)

    def test_the_customers_own_outline_still_wins_over_the_skeleton(self):
        doc, _ = L.page(D.CONTENT, self.contract, order=['faq', 'services'], page_type='business')
        self.assertEqual(self.ids(doc)[:3], ['top', 'faq', 'services'])
        self.assertIn('data-page-type=business', doc)


if __name__ == '__main__':
    unittest.main()
