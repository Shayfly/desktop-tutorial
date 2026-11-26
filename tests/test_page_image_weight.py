"""The page's images are fitted to the page budget before any code is paid for, and their weight never fails a build
(release review of 550320c, finding S2, 2026-11-26).

Found: a4.plan raised AssetPlanError above PAGE_IMAGE_BUDGET_BYTES (1.5 MB). a4.install runs at worker_tasks after the
pictures were generated and checked by the vision model (both paid), failure_code mapped the error to worker_exception,
the customer read "משהו השתבש אצלנו", and a retry paid again for the same failure. Production pictures were 65,240 and
112,128 bytes, so only 22 or 13 fitted: "עם 20 תמונות" was an easy trigger.

The owner, 2026-11-26: no image cap at all, and every image reduced to the smallest size at the best quality. Now
a4.install re-encodes the page's images to fit (web_rendition.fit_page: Pillow, each in its own type, descending
quality and width, bounded steps, quality floor 60); what still does not fit is carried with a PAGE_WEIGHT_OVER_BUDGET
warning in the build evidence. Declared as a weakening in docs/identity/allowed-deletions.json.

Real path: the production engine (AutonomousProductEngine with the skill-gate test doubles of tests/test_skill_gates,
as tests/test_a4_asset_plan.OnTheBuild), real GeneratedImage objects carrying real Pillow-encoded JPEG and WebP bytes of
the production sizes, a4.install, the repository transform the build writes files with, and the part ledger's check.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import random
import unittest
from unittest import mock

from PIL import Image, ImageDraw, ImageFilter

from omni_prod import a4
from omni_prod import part_ledger as PL
from omni_prod import web_rendition as W
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.generated_images import GeneratedImage
from omni_prod.repository_assets import decode
from tests.test_skill_gates import _Arch, _Files, _Sandbox, as_app_py
from tests.test_a4_asset_plan import page, section

SIZES = (65_240, 112_128)        # the production pictures' bytes (release review S2)


def scene(seed: int, size=(1344, 768)) -> Image.Image:
    """A photo-like picture (gradient, shapes, blur, grain) at FLUX's 16:9 size: it compresses like a photo."""
    rnd = random.Random(seed)
    img = Image.blend(Image.linear_gradient('L').resize(size).convert('RGB'),
                      Image.new('RGB', size, tuple(rnd.randrange(40, 220) for _ in range(3))), 0.6)
    draw = ImageDraw.Draw(img)
    for _ in range(60):
        x, y, r = rnd.randrange(size[0]), rnd.randrange(size[1]), rnd.randrange(10, 160)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=tuple(rnd.randrange(256) for _ in range(3)))
    return Image.blend(img.filter(ImageFilter.GaussianBlur(3)), Image.effect_noise(size, 18).convert('RGB'), 0.12)


def encoded(seed: int, fmt: str, target: int) -> bytes:
    """The scene encoded as close to `target` bytes as a bounded quality search gets (8 encodes)."""
    lo, hi, best, img = 5, 95, None, scene(seed)
    for _ in range(8):
        q = (lo + hi) // 2
        out = io.BytesIO()
        img.save(out, format=fmt, quality=q)
        if best is None or abs(out.tell() - target) < abs(len(best) - target):
            best = out.getvalue()
        lo, hi = (lo, q - 1) if out.tell() > target else (q + 1, hi)
    return best


_CACHE: dict = {}


def picture(index: int) -> GeneratedImage:
    """Picture `index` of the twenty: odd ones a JPEG near 65,240 bytes, even ones a WebP near 112,128 bytes."""
    fmt, mime, target = (('JPEG', 'image/jpeg', SIZES[0]) if index % 2 else ('WEBP', 'image/webp', SIZES[1]))
    key = (index, fmt)
    if key not in _CACHE:
        _CACHE[key] = encoded(index, fmt, target)
    data = _CACHE[key]
    return GeneratedImage(index=index, requirement_id=f'r{index}', purpose=a4.ITEM_PURPOSE if index > 1 else
                          'hero/brand visual', mime=mime, width=1344, height=768,
                          sha256=hashlib.sha256(data).hexdigest(), alt=f'פריט {index}', data=data)


def img_tag(img):
    return f'<img src="{img.marker}" alt="{img.alt}" loading="lazy">'


def build(images):
    """a4.install and the build, on the production engine, with every picture on the page."""
    hero, items = images[0], images[1:]
    html = page(img_tag(hero), section('products', *items) if items else '')
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(html)}),
                                repairer=_Files({'app.py': as_app_py(html)}), executor=_Sandbox(), max_repair_rounds=1)
    e.uploaded_images, e.generated_images = [], list(images)
    # the worker's order: generated_images.install puts its transform (built from the bytes as bound) BEFORE a4.install
    from omni_prod.generated_images import _Transform
    e.repository_transform = _Transform(None, e.generated_images)
    with mock.patch.dict(os.environ, {}):
        os.environ.pop('OMNI_GATE_A4', None)
        prompt = a4.install(e, prompt='PROMPT')
    return e, prompt


class TwentyPicturesOfTheProductionSize(unittest.TestCase):
    def test_the_fixture_is_the_production_size(self):
        for index in (1, 2):
            with self.subTest(index):
                self.assertLess(abs(len(picture(index).data) - SIZES[(index + 1) % 2]) / SIZES[(index + 1) % 2], 0.08)
        self.assertGreater(sum(len(picture(i).data) for i in range(1, 21)), a4.PAGE_IMAGE_BUDGET_BYTES)

    def test_they_are_fitted_before_any_code_and_the_build_goes_on(self):
        images = [picture(i) for i in range(1, 21)]
        before = {img.marker: (img.mime, len(img.data), img.carried.path) for img in images}
        e, prompt = build(images)                          # no AssetPlanError: nothing to map to worker_exception
        weight = a4.report(e)['page_weight']
        self.assertGreater(weight['bytes_before'], a4.PAGE_IMAGE_BUDGET_BYTES)
        self.assertTrue(weight['fits'], weight)
        self.assertLessEqual(weight['bytes_after'], a4.PAGE_IMAGE_BUDGET_BYTES)
        self.assertEqual(sum(len(img.data) for img in images), weight['bytes_after'])
        self.assertIsNone(weight['warning'])
        self.assertEqual((weight['count'], weight['budget']), (20, a4.PAGE_IMAGE_BUDGET_BYTES))
        self.assertTrue(weight['images'])
        for row in weight['images']:
            self.assertGreaterEqual(row['step'][1], W.PAGE_FIT_QUALITY_FLOOR)
            self.assertLess(row['bytes'], row['bytes_before'])
        repo = e.repository_transform({'app.py': 'x'})
        fit = json.loads(repo[a4.PAGE_FIT_PATH])
        for img in images:
            mime, _, path = before[img.marker]
            self.assertEqual((img.mime, img.carried.path), (mime, path))          # the same file, the same type
            self.assertEqual(decode(path, repo[path]), img.data)                  # the transform carries the new bytes
            Image.open(io.BytesIO(img.data)).load()                               # a real picture
        self.assertEqual(set(fit['files']), {next(i.carried.path for i in images if i.marker == r['marker'])
                                             for r in weight['images']})
        self.assertEqual(len(a4.report(e)['plan']), 20)
        result = e.build('a page')
        self.assertEqual(result.status, 'ready', result)
        self.assertIn('Asset plan (decided by 148AI', prompt)

    def test_what_cannot_fit_is_carried_and_said_never_a_failure(self):
        images = [picture(i) for i in range(1, 5)]
        with mock.patch.object(a4, 'PAGE_IMAGE_BUDGET_BYTES', 20_000), \
                self.assertLogs(a4.__name__, level='WARNING') as logs:
            e, _ = build(images)
        weight = a4.report(e)['page_weight']
        self.assertFalse(weight['fits'])
        self.assertGreater(weight['bytes_after'], 20_000)
        self.assertTrue(weight['warning'].startswith(a4.PAGE_WEIGHT_WARNING))
        for said in ('4 images', f'{weight["bytes_after"]:,} bytes', '20,000'):
            self.assertIn(said, weight['warning'])
        self.assertTrue(any('PAGE_FIT' in line and 'fits=False' in line for line in logs.output), logs.output)
        self.assertEqual(e.build('a page').status, 'ready')

    def test_the_plan_never_refuses_weight(self):
        heavy = [picture(i) for i in range(1, 21)]
        self.assertEqual(len(a4.plan([], heavy)), 20)


class TheFitIsBounded(unittest.TestCase):
    def test_at_most_one_encode_per_step_per_image(self):
        images = [picture(i) for i in range(1, 7)]
        real, calls = W._reencode, []

        def counted(*a, **kw):
            calls.append(a[0][:8])
            return real(*a, **kw)
        with mock.patch.object(W, '_reencode', counted):
            out = W.fit_page(images, budget=60_000)
        self.assertLessEqual(len(calls), 6 * len(W.PAGE_FIT_STEPS))
        self.assertFalse(out['fits'])
        self.assertTrue(all(q >= W.PAGE_FIT_QUALITY_FLOOR for _, q in W.PAGE_FIT_STEPS))

    def test_a_heavier_encode_is_never_taken(self):
        images = [picture(1), picture(2)]
        kept = [img.data for img in images]
        with mock.patch.object(W, '_reencode', lambda data, mime, scale, quality: (data + b'\0' * 10, 1, 1)):
            out = W.fit_page(images, budget=1_000)
        self.assertEqual([img.data for img in images], kept)
        self.assertEqual((out['images'], out['fits']), ([], False))

    def test_a_bad_argument_raises(self):
        for kw in ({'budget': 0}, {'budget': True}, {'budget': 10, 'places': {'nope': 'hero'}},
                   {'budget': 10, 'places': {'148ai-asset://image/1': 'footer'}}):
            with self.subTest(kw), self.assertRaises(ValueError):
                W.fit_page([picture(1)], **kw)


class TheLedgerAttestsAFittedFile(unittest.TestCase):
    def test_page_fit_state(self):
        row = {'from_sha256': 'a' * 64, 'sha256': 'b' * 64}
        self.assertEqual(PL._bytes_state('b' * 64, 'image/png', 10, 'a' * 64, bound_over_budget=False, page_fit=row),
                         'page_fit')
        self.assertIsNone(PL._bytes_state('b' * 64, 'image/png', 10, 'c' * 64, bound_over_budget=False, page_fit=row))
        self.assertIsNone(PL._bytes_state('d' * 64, 'image/png', 10, 'a' * 64, bound_over_budget=False, page_fit=row))
        self.assertIn(a4.PAGE_FIT_PATH, PL.RECORD_FILES)


class ImagesBeyondTheFirstScreenAreLazy(unittest.TestCase):
    """Requirement 2 was already met: the renderer emits loading="lazy" for every image but the first screen's, and G4's
    perf_lazy_images probe holds generated code to it. Pinned here."""

    def test_the_renderer(self):
        from omni_prod.section_library import img
        self.assertIn('loading="lazy"', img({'src': 'a.webp', 'alt': 'x'}))
        self.assertNotIn('loading="lazy"', img({'src': 'a.webp', 'alt': 'x'}, eager=True))

    def test_the_g4_probe(self):
        from omni_prod.skill_units.perf_lazy_images.probe import probe
        bad = probe('<img src="a.webp" alt="a"><img src="b.webp" alt="b">')
        good = probe('<img src="a.webp" alt="a"><img src="b.webp" alt="b" loading="lazy">')
        self.assertEqual((bad['status'], bad['code'], good['status']), ('fail', 'IMG_NOT_LAZY', 'pass'))


if __name__ == '__main__':
    logging.basicConfig()
    unittest.main()
