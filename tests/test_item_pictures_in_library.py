"""Visual plan S3: the pictures of the customer's items stay on the section library route.

Before: a picture per item (asked in words, or by default since the owner's decision of 2026-11-27) sent the build to the
legacy path (`beyond_one_page: picture_per_item`, `item_pictures_default`), which costs 5 to 9 times more and looks worse,
because the library had no card that could carry a picture and no gallery the route could fill. Now:

* the fact sheet binds each listed item to its picture (`@item:N`: a generated one by its alt, the customer's own photos in
  the order of the list) and keeps the rest for the gallery;
* a services card names the item it shows (`"item": "@item:N"`), the renderer attaches the picture, the model never sees or
  chooses one; an unknown reference is REF_UNKNOWN, an item no card names (or a card with no item) is ITEM_PICTURE_UNPLACED;
* all or none: the cards carry pictures only when every item has one; otherwise they carry none and the item pictures stand
  in the gallery (nothing paid for is dropped), which then stands in for the products section for a4;
* decide() keeps the build on the library route; a page per item and the owner's later edits still go to the legacy path.

Real path: the owner's law-firm brief with a services list (tests/test_item_pictures_default.py), the real asset plan
(a4.plan), the real fact sheet, validator and renderer, a4.check on the finished page, and the section library in Chromium."""
import copy
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import a4
from omni_prod import section_library as L
from omni_prod import site_content as SC
from omni_prod.generated_images import GeneratedImage
from omni_prod.section_library import DIRECTIONS
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from omni_prod.site_content import schema as K
from omni_prod.site_content import validate as V
from tests import test_site_content_render as T
from tests.test_item_pictures_default import LISTED, SERVICES, listing, on
from tests.test_site_content_route import with_request

ITEM = a4.ITEM_PURPOSE
LOGO = (Path(__file__).resolve().parent.parent / 'BRAND_PACK' / '148AI-logo-64.png').read_bytes()      # a real PNG


def image(n, alt, purpose=ITEM):
    return GeneratedImage(index=n, requirement_id=f'asset-{n:03d}', purpose=purpose, mime='image/png', width=64, height=64,
                          sha256=f'{n:064x}', alt=alt, data=LOGO)


def items_plan(services=SERVICES, hero=True, skip=()):
    imgs = ([image(1, 'משרד עורכי דין בתל אביב', 'hero/brand visual')] if hero else [])
    n = len(imgs)
    for name in services:
        n += 1
        if name not in skip:
            imgs.append(image(n, name))
    return imgs, a4.plan((), imgs)


def sheet_for(prompt, imgs, slots):
    return Fx.fact_sheet(prompt, asset_plan=slots, images=imgs)


def document(sheet, refs=True):
    """The scripted content of the owner's brief with the services section written for the customer's items."""
    doc = copy.deepcopy(T.FIXTURE['scripted_content'])
    cards = [{'title': it['text'], 'desc': f"בדיקה וייצוג בנושא {it['text']}."} for it in sheet.items] or doc['sections']['services']['items']
    if refs:
        for card, it in zip(cards, sheet.items):
            card['item'] = it['id']
    doc['sections']['services']['items'] = cards
    return doc


def offered(sheet):
    return K.offered_sections(sheet, DIRECTIONS['palettes']['counsel'], T.ORDER, T.TITLES)[0]


def codes(doc, sheet):
    return {(p.path, p.code) for p in V.validate(doc, sheet, offered(sheet), T.TITLES, claim_mode='warn')}


class TheSheetBindsItemsToPictures(unittest.TestCase):
    def test_a_generated_picture_is_the_picture_of_the_item_its_alt_names(self):
        imgs, slots = items_plan()
        sheet = sheet_for(LISTED, imgs, slots)
        self.assertEqual([i['text'] for i in sheet.items], list(SERVICES))
        self.assertEqual([i['id'] for i in sheet.items], ['@item:1', '@item:2', '@item:3'])
        self.assertEqual({k: v['alt'] for k, v in sheet.item_images.items()}, {f'@item:{n}': s for n, s in enumerate(SERVICES, 1)})
        self.assertTrue(sheet.services_pictured())
        self.assertEqual(sheet.gallery_pictures(), [])
        self.assertEqual(sheet.problems, [])
        self.assertIn('hero', sheet.images)

    def test_an_alt_that_names_no_item_is_not_bound_to_the_wrong_one(self):
        imgs, slots = items_plan()
        slots[1]['alt'] = 'something else'
        sheet = sheet_for(LISTED, imgs, slots)
        self.assertEqual(len(sheet.item_images), 2)
        self.assertEqual([p['alt'] for p in sheet.gallery_images], ['something else'])
        self.assertFalse(sheet.services_pictured())
        self.assertTrue(sheet.products_in_gallery())

    def test_the_customers_own_photos_cover_the_first_items_in_order(self):
        imgs, slots = items_plan()
        own = [SimpleNamespace(index=n, marker=f'148ai-asset://upload/{n}', alt=f'תמונה {n}', place='products',
                               sha256=f'{n:064x}', data=b'x', width=10, height=10, uri=f'assets/u{n}.png') for n in (1, 2)]
        slots = a4.plan(own, [x for x in imgs if x.alt in (SERVICES[2], 'משרד עורכי דין בתל אביב')])
        sheet = sheet_for(LISTED, [*own, *imgs], slots)
        self.assertEqual([sheet.item_images[f'@item:{n}']['src'] for n in (1, 2)], [o.marker for o in own])
        self.assertEqual(sheet.item_images['@item:3']['alt'], SERVICES[2])
        self.assertTrue(sheet.services_pictured())

    def test_a_picture_with_no_list_in_the_brief_stands_in_the_gallery(self):
        imgs, slots = items_plan()
        sheet = sheet_for(T.PROMPT, imgs, slots)                 # the owner's brief lists no items
        self.assertEqual((sheet.items, sheet.item_images), ([], {}))
        self.assertEqual(len(sheet.gallery_images), 3)
        self.assertTrue(sheet.products_in_gallery())

    def test_no_picture_among_the_items_changes_nothing(self):
        sheet = Fx.fact_sheet(T.PROMPT)
        self.assertEqual((sheet.items, sheet.item_images, sheet.gallery_pictures(), sheet.services_pictured()), ([], {}, [], False))
        self.assertNotIn('items_with_pictures', sheet.for_model())

    def test_the_model_is_told_the_items_and_never_a_picture(self):
        imgs, slots = items_plan()
        told = sheet_for(LISTED, imgs, slots).for_model()
        self.assertEqual([i['id'] for i in told['items_with_pictures']], ['@item:1', '@item:2', '@item:3'])
        self.assertNotIn('148ai-asset', str(told))


class TheValidator(unittest.TestCase):
    def setUp(self):
        self.imgs, self.slots = items_plan()
        self.sheet = sheet_for(LISTED, self.imgs, self.slots)

    def test_a_document_that_names_each_item_once_is_clean(self):
        self.assertEqual([p for p in V.validate(document(self.sheet), self.sheet, offered(self.sheet), T.TITLES, claim_mode='warn')
                          if p.severity == 'block'], [])

    def test_an_unknown_item_reference_is_refused(self):
        doc = document(self.sheet)
        doc['sections']['services']['items'][0]['item'] = '@item:9'
        self.assertIn(('sections.services.items[0].item', 'REF_UNKNOWN'), codes(doc, self.sheet))

    def test_a_card_with_no_item_while_every_item_has_a_picture_is_refused(self):
        doc = document(self.sheet, refs=False)
        found = codes(doc, self.sheet)
        self.assertIn(('sections.services.items[0]', 'ITEM_PICTURE_UNPLACED'), found)
        self.assertIn(('sections.services.items', 'ITEM_PICTURE_UNPLACED'), found)

    def test_two_cards_for_one_item_and_an_item_no_card_names_are_refused(self):
        doc = document(self.sheet)
        doc['sections']['services']['items'][1]['item'] = '@item:1'
        found = codes(doc, self.sheet)
        self.assertIn(('sections.services.items[1].item', 'ITEM_PICTURE_UNPLACED'), found)
        self.assertIn(('sections.services.items', 'ITEM_PICTURE_UNPLACED'), found)

    def test_a_reference_is_not_copy(self):
        self.assertFalse([c for c in codes(document(self.sheet), self.sheet) if c[1] in ('NOT_HEBREW', 'SCHEMA_SHAPE')])

    def test_without_pictures_the_references_are_optional(self):
        sheet = Fx.fact_sheet(T.PROMPT)
        doc = document(sheet, refs=False)
        self.assertEqual([p for p in V.validate(doc, sheet, offered(sheet), T.TITLES, claim_mode='warn') if p.severity == 'block'], [])


class TheRenderer(unittest.TestCase):
    def render(self, prompt=LISTED, skip=(), services=SERVICES, hero=True):
        imgs, slots = items_plan(services, hero, skip)
        sheet = sheet_for(prompt, imgs, slots)
        doc = document(sheet)
        if sheet.gallery_pictures():
            doc['sections']['gallery'] = {'title': 'התמונות שלנו', 'nav': 'גלריה'}
        html, _ = T.render(doc=doc, sheet=sheet)
        return html, sheet, imgs, slots

    def cards(self, html):
        return re.findall(r'<article class="card card--picture"><img class="card-photo" src="([^"]+)" alt="([^"]*)"[^>]*>'
                          r'<div class="card-body"><h3>([^<]*)</h3>', html)

    def test_each_picture_is_inside_the_card_of_its_item_with_the_items_words_as_alt(self):
        html, sheet, imgs, slots = self.render()
        got = self.cards(html)
        self.assertEqual([(g[1], g[2]) for g in got], [(s, s) for s in SERVICES])
        self.assertEqual([g[0] for g in got], [sheet.item_images[f'@item:{n}']['src'] for n in (1, 2, 3)])
        self.assertIn('data-layout="', html)
        self.assertRegex(html, r'services:cards')
        self.assertRegex(html, r'<section class="[^"]*" id="services" data-places="products"')

    def test_the_placement_check_of_the_asset_plan_passes_on_the_finished_page(self):
        html, sheet, imgs, slots = self.render()
        by_marker = {i.marker: SimpleNamespace(marker=i.marker, uri=i.uri) for i in imgs}
        self.assertEqual(a4.check({R.PAGE: html}, slots, by_marker), [])

    def test_an_item_with_no_picture_leaves_the_cards_bare_and_the_pictures_in_the_gallery(self):
        html, sheet, imgs, slots = self.render(skip=(SERVICES[1],))
        self.assertEqual(self.cards(html), [])
        self.assertNotIn('card--picture', html)
        gallery = re.search(r'<section[^>]*id="gallery"[^>]*>(.*?)</section>', html, re.S)
        self.assertIsNotNone(gallery)
        self.assertEqual(len(re.findall(r'<img', gallery.group(1))), 2)             # the two pictures there are
        self.assertIn('data-places="products"', gallery.group(0))
        by_marker = {i.marker: SimpleNamespace(marker=i.marker, uri=i.uri) for i in imgs}
        self.assertEqual(a4.check({R.PAGE: html}, slots, by_marker), [])             # the gallery stands for the products

    def test_a_picture_among_the_items_with_no_list_is_in_a_gallery_that_says_so(self):
        html, sheet, imgs, slots = self.render(prompt=T.PROMPT)
        self.assertEqual(self.cards(html), [])
        self.assertIn('id="gallery" data-places="products"', html)

    def test_a_page_without_item_pictures_is_the_page_it_was(self):
        sheet = Fx.fact_sheet(T.PROMPT)
        html, _ = T.render(sheet=sheet)
        self.assertNotIn('card--picture', html)
        self.assertNotIn('id="gallery"', html)
        self.assertNotIn('data-places', html)

    def test_a_card_reaching_the_renderer_without_its_item_is_a_platform_defect(self):
        imgs, slots = items_plan()
        sheet = sheet_for(LISTED, imgs, slots)
        doc = document(sheet, refs=False)
        with self.assertRaises(R.SiteRenderDefect):
            T.render(doc=doc, sheet=sheet)

    def test_the_gallery_is_offered_only_with_pictures_for_it(self):
        sheet = Fx.fact_sheet(T.PROMPT)
        self.assertNotIn('gallery', offered(sheet))
        imgs, slots = items_plan()
        self.assertEqual(offered(sheet_for(T.PROMPT, imgs, slots))['gallery'], 'required')
        self.assertNotIn('gallery', offered(sheet_for(LISTED, imgs, slots)))        # every card carries its picture


class TheLibrary(unittest.TestCase):
    def contract(self):
        from tests.test_section_library_conformance import contract_for
        return contract_for('counsel')

    def content(self, pictured=True, partial=False):
        from tests.test_section_library_conformance import FULL
        c = dict(copy.deepcopy(FULL), direction='formal')
        c['about'].pop('image')                      # a file that is not served is a broken image on the fixture's server
        c['team']['members'] = [{k: v for k, v in m.items() if k != 'photo'} for m in c['team']['members']]
        c['gallery']['images'] = [{'src': 'data:image/png;base64,AAAA', 'alt': 'עבודה', 'width': 64, 'height': 64}]
        items = []
        for n, (t, d) in enumerate(c['services']['items']):
            row = (t, d)
            if pictured and not (partial and n == 1):
                row += ({'src': f'/assets/i{n}.webp', 'alt': t, 'width': 640, 'height': 480},)
            items.append(row)
        c['services']['items'] = items
        return c

    def test_some_cards_with_a_picture_and_some_without_raises(self):
        with self.assertRaisesRegex(ValueError, 'all or none'):
            L.page(self.content(partial=True), self.contract())

    def test_a_pictured_services_section_is_cards_even_when_the_list_was_asked(self):
        doc, _ = L.page(dict(self.content(), layout={'services': 'list'}), self.contract())
        self.assertIn('services:cards', doc)
        self.assertNotIn('svc-list', doc)

    def test_a_services_section_without_pictures_is_unchanged(self):
        doc, _ = L.page(self.content(pictured=False), self.contract())
        self.assertNotIn('card--picture', doc)
        self.assertNotIn('data-places', doc)

    def test_the_rules_of_the_pictured_cards_are_only_on_a_page_that_has_them(self):
        with_cards, _ = L.page(self.content(), self.contract())
        without, _ = L.page(self.content(pictured=False), self.contract())
        self.assertIn('.card-photo', with_cards)
        self.assertNotIn('.card-photo', without)


class TheRoute(unittest.TestCase):
    def test_a_picture_per_item_never_sends_the_build_to_the_legacy_path(self):
        with on():
            for label, prompt in (('listed items, the default', LISTED),
                                  ('asked in words', with_request('ליד כל שירות תשימו תמונה.', LISTED)),
                                  ('asked in words, no list', with_request('ליד כל שירות תשימו תמונה.')),
                                  ('five pictures', with_request('אני רוצה 5 תמונות.', LISTED)),
                                  ('six items', listing(SERVICES + ('ייצוג מעסיקים', 'ייעוץ מס', 'חוזי עבודה')))):
                with self.subTest(label):
                    route = SC.decide(prompt, {'user_id': 'usr_owner_test'}, year='2026')
                    self.assertEqual((route.route, route.reason), ('section_library', 'all preconditions hold'))

    def test_a_page_per_item_and_the_owners_later_edits_still_go_to_the_legacy_path_by_name(self):
        with on():
            for text, kind in (('עמוד נפרד לכל תחום התמחות.', 'separate_pages'),
                               ('ושאוכל לעדכן את השאלות הנפוצות בעצמי.', 'owner_edits_later')):
                with self.subTest(kind):
                    route = SC.decide(with_request(text, LISTED), {'user_id': 'usr_owner_test'}, year='2026')
                    self.assertEqual(route.route, 'legacy')
                    self.assertTrue(route.reason.startswith(f'beyond_one_page: {kind} "'), route.reason)

    def test_a_picture_asked_for_with_an_icon_still_goes_to_the_legacy_path(self):
        with on():
            self.assertEqual(SC.decide(with_request('אני רוצה גם לוגו למשרד.', LISTED), {'user_id': 'usr_owner_test'}).reason,
                             'icon_image')


def browser():
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image  # noqa: F401
    except ImportError:  # pragma: no cover
        raise unittest.SkipTest('playwright and pillow are required to render the page')
    return sync_playwright()


class InTheBrowser(unittest.TestCase):
    """The pictured cards and the stand-in gallery, at the viewports the visual check uses and at 320."""

    def page(self, pictured=True, partial=False):
        from tests.test_hero_photo_led import FONTS
        from tests.test_visual_picture_measures import png as solid
        c = TheLibrary().content(pictured, partial)
        for n, row in enumerate(c['services']['items']):
            if len(row) > 2:
                c['services']['items'][n] = (*row[:2], {**row[2], 'src': solid((30 + 20 * n, 80, 120), (160, 120))})
        c['gallery']['images'] = [{'src': solid((90, 120, 60), (160, 120)), 'alt': 'עבודה', 'width': 160, 'height': 120}] * 2
        doc, _ = L.page(c, TheLibrary().contract())
        return FONTS.sub('', doc)

    def test_the_audit_the_production_check_runs_finds_nothing_it_enforces(self):
        from omni_prod import visual_qa as VQ
        audit_js = re.search(r'AUDIT = r"""(.*?)"""', VQ.SCRIPT, re.S).group(1)
        found = {}
        with browser() as p:
            b = p.chromium.launch()
            for label, doc in (('cards', self.page()), ('gallery', self.page(pictured=False))):
                for name, v in VQ.VIEWPORTS.items():
                    ctx = b.new_context(viewport={'width': v['width'], 'height': v['height']}, is_mobile=v['mobile'],
                                        has_touch=v['mobile'], device_scale_factor=1, locale='he-IL')
                    pg = ctx.new_page()
                    pg.set_content(doc)
                    pg.wait_for_timeout(1000)
                    found[f'{label}/{name}'] = [f"{f['kind']} {f['at']}" for f in pg.evaluate(audit_js, v['mobile'])['findings']
                                                if f['kind'] in VQ.DEFAULT_ENFORCED]
                    ctx.close()
            b.close()
        self.assertEqual({k: v for k, v in found.items() if v}, {})
        self.assertEqual(len(found), 4)

    def test_nothing_scrolls_sideways_and_each_picture_fills_its_card(self):
        over, loose = {}, []
        with browser() as p:
            b = p.chromium.launch()
            doc = self.page()
            for w in (320, 390, 1440):
                pg = b.new_page(viewport={'width': w, 'height': 800})
                pg.set_content(doc)
                pg.wait_for_timeout(300)
                over[w] = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                loose += pg.evaluate("""[...document.querySelectorAll('.card--picture')].filter(c => {
                    const i = c.querySelector('.card-photo').getBoundingClientRect(), r = c.getBoundingClientRect();
                    return Math.abs(i.width - r.width) > 3 || i.top < r.top - 1 || i.height < 40; }).map(c => c.textContent.slice(0, 20))""")
                pg.close()
            b.close()
        self.assertEqual(over, {320: 0, 390: 0, 1440: 0})
        self.assertEqual(loose, [])

    def test_the_picture_measures_see_the_cards_pictures(self):
        # run_script starts the platform's in-sandbox script as a process, which needs playwright and the Chromium the
        # visual check finds (tests.test_visual_qa.HAVE_BROWSER). Without them this skips loudly, as the two tests above
        # do; browser-python.yml runs the file and fails on any skip, so the skip cannot hide in a job that has a browser.
        from tests.test_visual_qa import HAVE_BROWSER
        if not HAVE_BROWSER:
            raise unittest.SkipTest('playwright and chromium are required to run the in-sandbox picture measures')
        from tests.test_visual_picture_measures import rules_of, run_script
        doc = self.page()
        for vp in ('desktop', 'mobile'):
            report = run_script(doc, vp)
            m = report['measures']
            self.assertNotIn('no_picture', rules_of(report, vp), vp)
            self.assertEqual(m['pictures'], 6, vp)                         # four cards and two gallery pictures
            self.assertGreaterEqual(m['compositions'], 3, vp)


if __name__ == '__main__':
    unittest.main()
