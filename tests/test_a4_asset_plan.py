"""A4, the assets agent, first slice: one asset plan per build, a stated place for every image, and a placement check
that enters at warn (the owner, 2026-11-16, stage D and rule 4).

The real GeneratedImage, _MainImage, place_state, the gate's page reader and the engine's executor chain run; the
pages are the butcher page (a real generated page) with images put where each case needs them."""
import hashlib
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import a4
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.generated_images import GeneratedImage
from omni_prod.skill_units import gate as G
from omni_prod.uploaded_assets import _MainImage
from omni_prod.web_rendition import PLACE_SIDE
from tests import real_images
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

ROOT = Path(__file__).resolve().parent.parent


def gen(index, purpose='hero/brand visual', size=2000):
    data = b'\x89PNG\r\n\x1a\n' + bytes([index]) * size      # the full PNG signature: a carried file is sniffed (118)
    return GeneratedImage(index=index, requirement_id='r1', purpose=purpose, mime='image/png', width=1600, height=900,
                          sha256=hashlib.sha256(data).hexdigest(), alt=f'תמונה {index}', data=data)


def up(index, place):
    data = real_images.jpeg(index + 100)       # a real photo: every photo is converted (image weight, 2026-11-26)
    img = _MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), f'צילום {index}', 800, 600, index=index,
                     place=place if place in PLACE_SIDE else 'hero')
    img.place = place                          # A4 judges the place itself: an unknown one is A4's refusal to make
    return img


def page(*chunks):
    """The butcher page with extra markup put right after <body ...>."""
    html = BUTCHER['page']
    at = html.index('>', html.index('<body')) + 1
    return html[:at] + ''.join(chunks) + html[at:]


def img_tag(image):
    return f'<img src="{image.marker}" alt="{image.alt}">'


def section(word, *images):
    return f'<section id="{word}"><h2>{word}</h2>' + ''.join(img_tag(i) for i in images) + '</section>'


class ThePlan(unittest.TestCase):
    def test_a_customers_photo_keeps_its_place_and_a_generated_picture_is_the_hero(self):
        slots = a4.plan([up(1, 'products')], [gen(1)])
        self.assertEqual([(s['place'], s['source']) for s in slots], [('hero', 'generated'), ('products', 'upload')])
        self.assertEqual(slots[1]['why'], 'the place the customer chose')

    def test_the_customers_hero_wins_and_the_generated_picture_goes_to_the_gallery_with_the_reason(self):
        slots = a4.plan([up(1, 'hero')], [gen(1)])
        self.assertEqual([(s['place'], s['source']) for s in slots], [('hero', 'upload'), ('gallery', 'generated')])
        self.assertIn('already taken', slots[1]['why'])

    def test_an_icon_goes_to_the_header_and_further_pictures_to_the_gallery(self):
        slots = a4.plan([], [gen(1, 'Product icon / logo'), gen(2), gen(3)])
        self.assertEqual([s['place'] for s in slots], ['icon', 'hero', 'gallery'])

    def test_every_image_has_exactly_one_slot_and_no_bytes_are_in_the_plan(self):
        images = [up(1, 'story'), up(2, 'gallery')], [gen(1), gen(2)]
        slots = a4.plan(*images)
        self.assertEqual(sorted(s['marker'] for s in slots), sorted(i.marker for group in images for i in group))
        self.assertTrue(all(set(s) == {'place', 'source', 'index', 'marker', 'alt', 'sha256', 'bytes', 'why'} for s in slots))

    def test_what_cannot_be_planned_stops_the_build(self):
        with self.assertRaises(a4.AssetPlanError) as two:
            a4.plan([up(1, 'hero'), up(2, 'hero')], [])
        self.assertIn('two uploaded images claim the hero', str(two.exception))
        with self.assertRaises(a4.AssetPlanError):
            a4.plan([up(1, 'footer')], [])
        # S2 (the owner, 2026-11-26: no image cap): weight is not a reason -- install fits the page and says what does
        # not fit (tests/test_page_image_weight.py); declared in docs/identity/allowed-deletions.json "weakening"
        heavy = a4.plan([], [gen(1, size=a4.PAGE_IMAGE_BUDGET_BYTES // 2 + 1), gen(2, size=a4.PAGE_IMAGE_BUDGET_BYTES // 2 + 1)])
        self.assertEqual(len(heavy), 2)

    def test_the_number_of_images_never_stops_the_plan(self):
        """The owner, 2026-11-26: no image cap. Until then a page with more than 12 images was refused."""
        slots = a4.plan([up(1, 'story')], [gen(i) for i in range(1, 30)])
        self.assertEqual(len(slots), 30)
        self.assertEqual([s['place'] for s in slots].count('gallery'), 28)
        self.assertFalse(hasattr(a4, 'MAX_ASSETS'))

    def test_a_picture_of_one_item_goes_next_to_that_item(self):
        slots = a4.plan([], [gen(1), gen(2, a4.ITEM_PURPOSE), gen(3, a4.ITEM_PURPOSE)])
        self.assertEqual([s['place'] for s in slots], ['hero', 'products', 'products'])
        rules = a4.rules(slots)
        self.assertIn('src="148ai-asset://image/2" (generated): inside the products section.\n'
                      '  It shows "תמונה 2": put it next to that item.', rules)
        self.assertNotIn('It shows "תמונה 1"', rules)                  # the main image is not an item's picture

    def test_the_rules_name_every_image_and_its_place(self):
        slots = a4.plan([up(1, 'products')], [gen(1)])
        text = a4.rules(slots)
        self.assertIn('src="148ai-asset://image/1" (generated): the first image of the page', text)
        self.assertIn('src="148ai-asset://upload/1" (upload): inside the products section', text)
        self.assertIn('The main image comes before every other picture', text)
        self.assertEqual(a4.rules([]), '')


class TheCheck(unittest.TestCase):
    def run_check(self, html, uploaded=(), generated=()):
        slots = a4.plan(uploaded, generated)
        images = {i.marker: i for i in (*uploaded, *generated)}
        return a4.check({'app.py': as_app_py(html)}, slots, images)

    def test_a_page_that_follows_the_plan_has_no_finding(self):
        hero, photo = gen(1), up(1, 'products')
        self.assertEqual(self.run_check(page(img_tag(hero), section('products', photo)), [photo], [hero]), [])

    def test_a_picture_before_the_main_image_is_found(self):
        hero, photo = gen(1), up(1, 'products')
        (p,) = self.run_check(page(section('products', photo), img_tag(hero)), [photo], [hero])
        self.assertEqual((p['marker'], p['state']), (hero.marker, 'not_first'))
        self.assertIn(photo.marker, p['why'])

    def test_an_icon_may_come_before_the_main_image(self):
        icon, hero = gen(1, 'Product icon'), gen(2)
        self.assertEqual(self.run_check(page(img_tag(icon), img_tag(hero)), [], [icon, hero]), [])

    def test_a_generated_gallery_picture_outside_the_gallery_is_found(self):
        mine, extra = up(1, 'hero'), gen(1)
        (p,) = self.run_check(page(img_tag(mine), section('products', extra)), [mine], [extra])
        self.assertEqual((p['marker'], p['place'], p['state']), (extra.marker, 'gallery', 'no_section'))
        self.assertEqual(self.run_check(page(img_tag(mine), section('gallery', extra)), [mine], [extra]), [])

    def test_an_image_that_is_not_on_the_page_is_left_to_its_own_check(self):
        self.assertEqual(self.run_check(page(), [], [gen(1)]), [])


class OnTheBuild(unittest.TestCase):
    def build(self, html, uploaded=(), generated=(), mode=None):
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(html)}),
                                    repairer=_Files({'app.py': as_app_py(html)}), executor=_Sandbox(), max_repair_rounds=1)
        e.uploaded_images, e.generated_images = list(uploaded), list(generated)
        env = {} if mode is None else {'OMNI_GATE_A4': mode}
        with mock.patch.dict(os.environ, env):
            if mode is None:
                os.environ.pop('OMNI_GATE_A4', None)
            prompt = a4.install(e, prompt='PROMPT')
        return e, prompt, e.build('a page')

    def test_it_enters_at_warn_the_build_goes_on_and_the_evidence_says_what_it_found(self):
        self.assertIn('A4', G.CALIBRATING)
        hero, photo = gen(1), up(1, 'products')
        with self.assertLogs(a4.__name__, level='WARNING') as logs:
            e, prompt, result = self.build(page(section('products', photo), img_tag(hero)), [photo], [hero])
        self.assertEqual(result.status, 'ready')
        self.assertIn('Asset plan (decided by 148AI', prompt)
        rep = a4.report(e)
        self.assertEqual((rep['mode'], rep['check']['status']), ('warn', 'fail'))
        self.assertEqual(rep['check']['problems'][0]['state'], 'not_first')
        self.assertEqual([s['place'] for s in rep['plan']], ['hero', 'products'])
        self.assertTrue(any('A4_PLACEMENT mode=warn' in line for line in logs.output))

    def test_in_block_mode_a_misplaced_image_fails_the_build_with_what_to_do(self):
        hero, photo = gen(1), up(1, 'products')
        e, _, result = self.build(page(section('products', photo), img_tag(hero)), [photo], [hero], mode='block')
        self.assertEqual(result.status, 'failed')
        failure = [f for f in result.report.failures if f.acceptance_id == a4.ACCEPTANCE_ID][0]
        self.assertIn('Move its <img> there', failure.message)
        self.assertIn(hero.marker, failure.message)

    def test_a_page_with_no_platform_image_gets_no_rules_and_an_empty_plan(self):
        e, prompt, result = self.build(page())
        self.assertEqual(prompt, 'PROMPT')
        self.assertEqual(a4.report(e), {'agent': 'A4', 'mode': 'warn', 'plan': [], 'check': None})

    def test_off_is_said_in_the_log_and_in_the_evidence(self):
        hero = gen(1)
        with self.assertLogs(a4.__name__, level='WARNING') as logs:
            e, prompt, _ = self.build(page(img_tag(hero)), [], [hero], mode='off')
        self.assertTrue(any('GATE_OFF gate=A4' in line for line in logs.output))
        self.assertEqual(a4.report(e)['mode'], 'off')
        self.assertIn('Asset plan', prompt)                       # the plan is still told; only the check is off

    def test_the_worker_plans_after_the_images_are_bound_and_writes_the_evidence(self):
        src = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertLess(src.index('build_prompt = install_main_image(engine'), src.index('build_prompt = install_asset_plan(engine'))
        self.assertLess(src.index('generated_images import install as install_generated_images'),
                        src.index('build_prompt = install_asset_plan(engine'))
        self.assertIn("evidence['asset_plan'] = asset_plan_report(engine)", src)


if __name__ == '__main__':
    unittest.main()
