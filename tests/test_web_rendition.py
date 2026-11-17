"""Warehouse 114, first half: the page carries a web-sized rendition of the customer's photo.

Production, 2026-11-14 (the butcher, bld_83529c13): the hero photo was inlined as 1,735,408 base64 characters. The
photos here are made with Pillow at phone size (a real JPEG and PNG encoder and decoder run); the G4 unit that
measured the butcher page is the one that judges the result."""
import base64
import hashlib
import io
import unittest
from pathlib import Path

from PIL import Image

from omni_prod import web_rendition as W
from omni_prod.skill_units import run as run_unit
from omni_prod.uploaded_assets import _MainImage

ROOT = Path(__file__).resolve().parent.parent


def photo(size=(4000, 3000), fmt='JPEG', orientation=None, mode='RGB', quality=95):
    """A phone-sized picture with detail in it (noise does not compress away), and one red corner at top-left."""
    img = Image.effect_noise(size, 48).convert(mode)
    img.paste((220, 0, 0) + ((255,) if mode == 'RGBA' else ()), (0, 0, size[0] // 4, size[1] // 4))
    out, extra = io.BytesIO(), {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        extra['exif'] = exif
    img.save(out, fmt, **({'quality': quality} if fmt == 'JPEG' else {}), **extra)
    return out.getvalue()


def decoded(r):
    return Image.open(io.BytesIO(r['data']))


class AHeavyPhotoBecomesLight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = photo()
        cls.r = W.rendition(cls.data, 'image/jpeg')

    def test_it_was_heavy_like_the_butchers(self):
        self.assertGreater(len(base64.b64encode(self.data)), 1_700_000)

    def test_it_fits_the_budget_and_the_screen(self):
        self.assertTrue(self.r['changed'])
        self.assertLessEqual(len(self.r['data']), W.BUDGET_BYTES)
        self.assertLessEqual(max(self.r['width'], self.r['height']), W.MAX_SIDE)
        self.assertEqual(self.r['mime'], 'image/webp')
        self.assertIn(tuple(self.r['step']), W.STEPS)

    def test_it_is_the_same_picture_with_the_same_proportions(self):
        img = decoded(self.r)
        self.assertEqual(img.size, (self.r['width'], self.r['height']))
        self.assertAlmostEqual(img.width / img.height, 4000 / 3000, places=2)
        r, g, b = img.convert('RGB').getpixel((img.width // 16, img.height // 16))
        self.assertTrue(r > 150 and g < 90 and b < 90, (r, g, b))           # the red corner is still top-left

    def test_both_digests_are_recorded(self):
        self.assertEqual(self.r['original_sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(self.r['sha256'], hashlib.sha256(self.r['data']).hexdigest())
        self.assertEqual(self.r['original_bytes'], len(self.data))

    def test_the_page_passes_the_unit_that_failed_on_the_butcher(self):
        digest = hashlib.sha256(self.data).hexdigest()
        img = _MainImage(self.data, 'image/jpeg', digest, 'דלתות פנים', 4000, 3000)
        heavy = 'data:image/jpeg;base64,' + base64.b64encode(self.data).decode('ascii')
        self.assertEqual(run_unit('perf_inline_image_weight', f'<img src="{heavy}" alt="x">')['status'], 'fail')
        self.assertEqual(run_unit('perf_inline_image_weight', f'<img src="{img.uri}" alt="x">')['status'], 'pass')
        self.assertEqual(img.sha256, digest)                                 # the brief's binding is the original's
        self.assertEqual((img.width, img.height, img.mime), (self.r['width'], self.r['height'], 'image/webp'))
        self.assertEqual(img.rendition['original_sha256'], digest)
        self.assertTrue(img.rendition['changed'])


class AGeneratedImageBecomesLightToo(unittest.TestCase):
    """The butcher's 1.7 MB hero was a GENERATED image: the platform's own picture goes through the same rendition."""
    def test_the_real_collect_path_carries_the_light_rendition_and_keeps_the_verified_digest(self):
        from types import SimpleNamespace
        from omni_prod import generated_images as G
        data = photo(size=(1920, 1080), fmt='PNG')
        self.assertGreater(len(base64.b64encode(data)), 1_700_000)
        digest = hashlib.sha256(data).hexdigest()
        plan = SimpleNamespace(requirements=[SimpleNamespace(id='r1', key=G.IMAGE_CAPABILITY, purpose='hero/brand visual',
                                                             constraints={'subject': 'נתחי בקר טריים'})])
        evidence = {'requirements': [{'requirement_id': 'r1', 'capability_key': G.IMAGE_CAPABILITY, 'status': 'VERIFIED',
                                      'verification': {'artifacts': [{'artifact_key': 'k1', 'sha256': digest}]}}]}
        store = SimpleNamespace(get_bytes=lambda key: data)
        with self.assertLogs(G.__name__, level='INFO') as logs:
            (img,) = G.collect(plan=plan, evidence=evidence, store=store, prompt='אטליז')
        self.assertEqual(img.sha256, digest)
        self.assertEqual(img.mime, 'image/webp')
        self.assertLessEqual(len(img.data), W.BUDGET_BYTES)
        self.assertAlmostEqual(img.width / img.height, 1920 / 1080, places=2)
        self.assertEqual(run_unit('perf_inline_image_weight', f'<img src="{img.uri}" alt="x">')['status'], 'pass')
        self.assertIn('GENERATED_IMAGE index=1 changed=True', logs.output[0])
        self.assertEqual(G.placement({'index.html': f'<img src="{img.marker}" alt="בשר">'}, img), 'ok')


class TheRules(unittest.TestCase):
    def test_a_light_photo_is_carried_byte_for_byte(self):
        data = photo(size=(800, 600), quality=70)
        self.assertLessEqual(len(data), W.BUDGET_BYTES)
        r = W.rendition(data, 'image/jpeg')
        self.assertFalse(r['changed'])
        self.assertIs(r['data'], data)
        self.assertEqual((r['mime'], r['step']), ('image/jpeg', None))
        img = _MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), 'x', 800, 600)
        self.assertEqual((img.data, img.width, img.height), (data, 800, 600))

    def test_a_phone_photo_stored_sideways_comes_out_upright(self):
        data = photo(size=(4000, 3000), orientation=6)      # tag 6: rotate 90 degrees clockwise to show
        r = W.rendition(data, 'image/jpeg')
        img = decoded(r)
        self.assertGreater(img.height, img.width)           # portrait now
        px = img.convert('RGB').getpixel((img.width - img.width // 16, img.height // 16))
        self.assertTrue(px[0] > 150 and px[1] < 90, px)     # the stored top-left corner is shown at top-right

    def test_transparency_is_kept(self):
        data = photo(size=(2400, 1800), fmt='PNG', mode='RGBA')
        self.assertGreater(len(data), W.BUDGET_BYTES)
        img = Image.open(io.BytesIO(data)).convert('RGBA')
        img.paste((0, 0, 0, 0), (1800, 1350, 2400, 1800))   # a transparent corner
        out = io.BytesIO()
        img.save(out, 'PNG')
        r = W.rendition(out.getvalue(), 'image/png')
        got = decoded(r).convert('RGBA')
        self.assertEqual(got.getpixel((got.width - 5, got.height - 5))[3], 0)

    def test_it_never_enlarges(self):
        data = photo(size=(1200, 900), quality=100)
        if len(data) <= W.BUDGET_BYTES:
            self.skipTest('NOT_RUN: this encoder made the 1200 px photo lighter than the budget')
        r = W.rendition(data, 'image/jpeg')
        self.assertLessEqual((r['width'], r['height']), (1200, 900))

    def test_a_heavy_file_that_is_not_an_image_stops_the_build(self):
        with self.assertRaises(W.RenditionError) as ctx:
            W.rendition(b'\xff\xd8\xff' + b'x' * (W.BUDGET_BYTES + 1), 'image/jpeg')
        self.assertIn('could not be read', str(ctx.exception))

    def test_an_animated_image_is_refused(self):
        frames = [Image.effect_noise((900, 900), 60).convert('RGB') for _ in range(3)]
        out = io.BytesIO()
        frames[0].save(out, 'WEBP', save_all=True, append_images=frames[1:], lossless=True)
        self.assertGreater(out.tell(), W.BUDGET_BYTES)
        with self.assertRaises(W.RenditionError):
            W.rendition(out.getvalue(), 'image/webp')

    def test_the_steps_are_a_bounded_list_that_only_gets_lighter(self):
        self.assertLessEqual(len(W.STEPS), 8)
        self.assertEqual(W.STEPS[0][0], W.MAX_SIDE)
        sides = [s for s, _ in W.STEPS]
        self.assertEqual(sides, sorted(sides, reverse=True))
        self.assertLess(W.BUDGET_BYTES * 4 / 3, 500_000)    # under the G4 unit's limit, in base64 characters

    def test_the_worker_image_installs_the_same_pillow_the_tests_use(self):
        prod = (ROOT / 'requirements-production.txt').read_text(encoding='utf-8').split()
        test = (ROOT / 'requirements-test.txt').read_text(encoding='utf-8').split()
        pin = [line for line in test if line.lower().startswith('pillow==')]
        self.assertEqual(len(pin), 1)
        self.assertIn(pin[0], prod)


if __name__ == '__main__':
    unittest.main()
