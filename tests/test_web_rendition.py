"""Image weight (the owner, 2026-11-26): every image the page carries is converted -- the lowest bytes at the best
quality -- and nothing of the customer's file but the picture reaches the page.

Before (warehouse 114, 2026-11-16): a file of 360,000 bytes or less was carried byte for byte, its EXIF too, so a phone
photo published its GPS position, make and model in the customer's page and export (measured on main fa41a5d); and a
heavier one past the sixth fixed step STOPPED the build. Every picture here is made with Pillow -- a real encoder and
decoder run -- and the conversion is judged by what is in the bytes it returns: the size, the similarity measured
again, the metadata read back, the alpha, the rotation."""
import base64
import functools
import hashlib
import io
import json
import random
import struct
import unittest
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageCms, ImageDraw, ImageOps, PngImagePlugin

from omni_prod import generated_images as G
from omni_prod import web_rendition as W
from omni_prod.repository_assets import file_bytes, zip_bytes
from omni_prod.skill_units import run as run_unit
from omni_prod.uploaded_assets import _MainImage

ROOT = Path(__file__).resolve().parent.parent
GPS = {1: 'N', 2: (32.0, 4.0, 48.36), 3: 'E', 4: (34.0, 46.0, 51.12)}
SECRETS = (b'PhoneMaker', b'PhoneModel 15 Pro', b'2026:11:26 08:15:00', b'GPSinXMP', b'phone comment', b'ICC_PROFILE',
           b'Exif\x00\x00', b'eXIf', b'iCCP', b'ICCP', b'XMP ', b'<x:xmpmeta')


def noise(size, seed):
    """Uniform noise from a seeded generator: the same picture on every run, in any test order (Image.effect_noise
    draws from the C library's rand(), whose sequence depends on what ran before it in the process)."""
    return Image.frombytes('L', size, random.Random(seed).randbytes(size[0] * size[1]))


def textured(size, seed=1):
    """A photo-like picture: a sky gradient, a textured ground (noise at four scales), colour that varies on its own,
    hard edges and text, and one red corner at the stored top-left (to see the rotation). Deterministic per seed."""
    w, h = size
    ground = None
    for k, weight in ((3, 0.5), (2, 0.3), (1, 0.15), (0, 0.05)):
        n = noise((max(2, w >> k), max(2, h >> k)), seed * 10 + k).resize((w, h), Image.Resampling.BICUBIC)
        ground = n if ground is None else Image.blend(ground, n, weight)
    img = Image.merge('RGB', (ground.point(lambda v: 60 + v // 2), ground.point(lambda v: 50 + v // 2),
                              ground.point(lambda v: 30 + v // 3)))
    tint = Image.merge('RGB', [noise((max(2, w >> 3), max(2, h >> 3)), seed * 10 + 5 + c).resize(
        (w, h), Image.Resampling.BICUBIC) for c in range(3)])
    img = Image.blend(img, tint, 0.25)                      # colour that varies on its own, as in a photo
    sky = Image.linear_gradient('L').resize((w, h // 3))
    img.paste(Image.merge('RGB', (sky.point(lambda v: 110 + v // 4), sky.point(lambda v: 160 + v // 5),
                                  sky.point(lambda v: 235 - v // 6))), (0, 0))
    d = ImageDraw.Draw(img)
    for k in range(6):
        x0 = (k * 2 + 1) * w // 13
        d.rectangle((x0, h // 2, x0 + w // 14, h - h // 10), fill=(190 - k * 20, 150 + k * 10, 120), outline=(20, 20, 20),
                    width=max(1, w // 400))
    d.text((w // 3, h // 2 - 40), 'OPEN 08:00-20:00', fill=(250, 250, 250))
    img.paste((220, 0, 0), (0, 0, w // 4, h // 4))
    return img


def phone_exif(orientation=None):
    exif = Image.Exif()
    exif[0x010F], exif[0x0110], exif[0x0132] = 'PhoneMaker', 'PhoneModel 15 Pro', '2026:11:26 08:15:00'
    if orientation:
        exif[0x0112] = orientation
    exif.get_ifd(0x8825).update(GPS)
    return exif


SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def phone_jpeg(size=(1200, 900), orientation=6, quality=85):
    """What a phone sends: EXIF with GPS, make, model and time, the rotation tag, an XMP packet, an ICC profile and a
    comment."""
    out = io.BytesIO()
    textured(size).save(out, 'JPEG', quality=quality, exif=phone_exif(orientation), icc_profile=SRGB,
                        xmp=b'<x:xmpmeta xmlns:x="adobe:ns:meta/">GPSinXMP</x:xmpmeta>', comment=b'phone comment')
    return out.getvalue()


@functools.lru_cache(maxsize=1)
def twelve_megapixels():
    """A 12 MP phone photo (4032x3024, JPEG quality 92), made once."""
    return phone_jpeg((4032, 3024), quality=92)


def alpha_png(size=(1200, 900)):
    """A drawing with a transparent background, a half-transparent disc and an opaque rounded square."""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size
    d.rounded_rectangle((w // 12, h // 9, w // 2, h // 2), radius=w // 20, fill=(200, 40, 60, 255))
    d.ellipse((w // 2, h // 2, w - w // 10, h - h // 10), fill=(30, 90, 200, 128))
    out = io.BytesIO()
    img.save(out, 'PNG')
    return out.getvalue()


def decoded(r):
    img = Image.open(io.BytesIO(r['data']))
    img.load()
    return img


def reference(data, side):
    """The sized source, made independently: decoded in full, turned upright, resized in one Lanczos pass."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    img = img.convert('RGBA' if 'A' in img.mode else 'RGB')
    scale = min(1.0, side / max(img.size))
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)


def nothing_but_the_picture(test, data):
    img = Image.open(io.BytesIO(data))
    test.assertEqual(dict(img.getexif()), {})
    test.assertEqual([k for k in ('exif', 'xmp', 'XML:com.adobe.xmp', 'icc_profile', 'comment') if k in img.info], [])
    test.assertEqual([s for s in SECRETS if s in data], [])


class AHeavyPhonePhotoBecomesLight(unittest.TestCase):
    """A 12 MP phone photo (4032x3024, stored sideways with rotation tag 6, GPS in its EXIF)."""

    @classmethod
    def setUpClass(cls):
        cls.data = twelve_megapixels()
        cls.r = W.rendition(cls.data, 'image/jpeg', place='hero')

    def test_it_was_heavy_like_the_butchers(self):
        self.assertGreater(len(base64.b64encode(self.data)), 1_700_000)

    def test_it_fits_the_budget_and_the_screen(self):
        self.assertLess(self.r['bytes'], len(self.data) // 5)                   # measured: 9.3% (177,565 of 1,902,492)
        self.assertLessEqual(self.r['bytes'], W.BUDGET_BYTES)
        self.assertFalse(self.r['over_budget'])
        self.assertIn(self.r['mime'], W.OUTPUT_MIMES)
        self.assertEqual((self.r['width'], self.r['height']), (1200, 1600))      # upright, the hero's long side
        self.assertEqual(decoded(self.r).size, (1200, 1600))

    def test_the_similarity_passes_the_threshold_and_is_measured_again(self):
        self.assertTrue(self.r['threshold_met'])
        self.assertGreaterEqual(self.r['similarity'], W.THRESHOLD)
        # measured again here, against a source sized independently (a full decode, not the converter's own path)
        again = W.ssim(reference(self.data, 1600), decoded(self.r).convert('RGB'))
        self.assertGreaterEqual(again, W.THRESHOLD - 0.001, again)

    def test_nothing_of_the_file_but_the_picture_is_left(self):
        nothing_but_the_picture(self, self.r['data'])
        self.assertEqual({k: self.r['removed'][k] for k in ('exif', 'gps', 'xmp', 'icc', 'comment', 'orientation')},
                         {'exif': True, 'gps': True, 'xmp': True, 'icc': True, 'comment': True, 'orientation': 6})
        self.assertEqual(self.r['icc'], 'converted to sRGB')

    def test_a_phone_photo_stored_sideways_comes_out_upright(self):
        img = decoded(self.r).convert('RGB')
        self.assertGreater(img.height, img.width)                              # portrait now
        px = img.getpixel((img.width - img.width // 16, img.height // 16))
        self.assertTrue(px[0] > 150 and px[1] < 90, px)                         # stored top-left is shown top-right

    def test_both_digests_and_the_measure_are_recorded(self):
        self.assertEqual(self.r['original_sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(self.r['sha256'], hashlib.sha256(self.r['data']).hexdigest())
        self.assertEqual((self.r['original_bytes'], self.r['bytes']), (len(self.data), len(self.r['data'])))
        self.assertEqual(self.r['original_size'], [4032, 3024])
        self.assertGreater(self.r['ms'], 0)
        json.dumps(W.record(self.r))                                            # the build evidence takes it as is
        self.assertNotIn('data', W.record(self.r))

    def test_every_search_is_bounded(self):
        per_format = {}
        for row in self.r['candidates']:
            per_format[row['format']] = per_format.get(row['format'], 0) + 1
        self.assertTrue(all(n <= W.MAX_SEARCH_ENCODES for f, n in per_format.items() if f != 'webp-lossless'))
        self.assertLessEqual(self.r['encodes'], 2 * W.MAX_SEARCH_ENCODES + 1 + len(W.STEPS))
        self.assertEqual(self.r['encodes'], len(self.r['candidates']))

    def test_the_lowest_bytes_that_pass_are_chosen_and_the_smaller_format_wins(self):
        rows = self.r['candidates']
        self.assertLessEqual({'webp', 'jpeg'}, {r['format'] for r in rows})      # a JPEG: its clean re-encode competes
        self.assertEqual(min(r['bytes'] for r in rows if r['passed']), self.r['bytes'])
        lighter = [r for r in rows if r['bytes'] < self.r['bytes']]
        self.assertTrue(all(not r['passed'] for r in lighter), lighter)          # every lighter try looked different
        self.assertTrue(all(r['quality'] >= W.QUALITY_FLOOR for r in rows if r['quality'] is not None))


class ThePrivacyDefectIsClosed(unittest.TestCase):
    """A light phone photo (under 360,000 bytes): on main it reached the page and the export with its GPS block."""

    def carried(self, data, mime):
        img = _MainImage(data, mime, hashlib.sha256(data).hexdigest(), 'החנות', index=1, place='hero')
        repo = G._Transform(None, [img])({'index.html': f'<img src="{img.marker}" alt="החנות">'})
        with zipfile.ZipFile(io.BytesIO(zip_bytes(repo))) as zf:
            exported = zf.read(img.uri)
        return img, file_bytes(img.uri, repo[img.uri]), exported

    def test_a_light_phone_photo_reaches_the_page_and_the_export_without_its_gps(self):
        data = phone_jpeg()
        self.assertLessEqual(len(data), W.BUDGET_BYTES)                         # it used to be carried untouched
        self.assertEqual(dict(Image.open(io.BytesIO(data)).getexif().get_ifd(0x8825)), GPS)
        img, page_file, exported = self.carried(data, 'image/jpeg')
        self.assertNotEqual(page_file, data)
        self.assertEqual(page_file, img.data)
        self.assertEqual(exported, img.data)
        nothing_but_the_picture(self, page_file)
        nothing_but_the_picture(self, exported)
        self.assertTrue(img.rendition['removed']['gps'])
        self.assertEqual(img.sha256, hashlib.sha256(data).hexdigest())          # the brief's binding: the original

    def test_a_png_with_an_exif_chunk_and_text_is_cleaned_too(self):
        info = PngImagePlugin.PngInfo()
        info.add_text('Comment', 'phone comment')
        info.add_itxt('XML:com.adobe.xmp', '<x:xmpmeta xmlns:x="adobe:ns:meta/">GPSinXMP</x:xmpmeta>')
        out = io.BytesIO()
        textured((600, 400)).save(out, 'PNG', exif=phone_exif(), pnginfo=info, icc_profile=SRGB)
        data = out.getvalue()
        self.assertEqual(dict(Image.open(io.BytesIO(data)).getexif().get_ifd(0x8825)), GPS)
        img, page_file, exported = self.carried(data, 'image/png')
        nothing_but_the_picture(self, page_file)
        nothing_but_the_picture(self, exported)


class SizedForItsPlace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = io.BytesIO()
        textured((2100, 1400)).save(out, 'JPEG', quality=90)
        cls.data = out.getvalue()

    def test_each_place_has_its_long_side(self):
        for place, side in W.PLACE_SIDE.items():
            with self.subTest(place=place):
                r = W.rendition(self.data, 'image/jpeg', place=place)
                self.assertEqual(max(r['width'], r['height']), side)
                self.assertAlmostEqual(r['width'] / r['height'], 1.5, delta=0.01)

    def test_it_never_enlarges(self):
        for size in ((800, 600), (12, 9)):
            with self.subTest(size=size):
                out = io.BytesIO()
                textured(size).save(out, 'PNG')
                r = W.rendition(out.getvalue(), 'image/png', place='hero')
                self.assertEqual((r['width'], r['height']), size)
                self.assertEqual(decoded(r).size, size)
                self.assertLess(r['bytes'], len(out.getvalue()))

    def test_an_unknown_place_or_flag_raises(self):
        with self.assertRaises(ValueError):
            W.rendition(self.data, 'image/jpeg', place='footer')
        with self.assertRaises(ValueError):
            W.rendition(self.data, 'image/jpeg', keep_mime='image/png')
        with self.assertRaises(ValueError):
            W.rendition(self.data, 'image/jpeg', search=False)


class TransparencyIsKept(unittest.TestCase):
    def test_transparency_is_kept(self):
        data = alpha_png()
        r = W.rendition(data, 'image/png', place='hero')
        self.assertEqual(r['mime'], 'image/webp')
        got = decoded(r).convert('RGBA')
        self.assertEqual(got.size, (1200, 900))
        self.assertEqual(got.getpixel((5, 5))[3], 0)                            # the transparent background
        self.assertEqual(got.getpixel((960, 720))[3], 128)                       # the half-transparent disc, exactly
        self.assertEqual(got.getpixel((300, 300))[3], 255)                       # the opaque square
        self.assertLess(r['bytes'], len(data))
        self.assertIn('webp-lossless', {row['format'] for row in r['candidates']})   # a flat drawing: lossless too
        self.assertGreaterEqual(r['similarity'], W.THRESHOLD)


class NothingIsRefusedForItsWeight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = io.BytesIO()
        textured((1800, 1200)).save(out, 'JPEG', quality=95)
        cls.data = out.getvalue()

    def test_over_its_budget_it_steps_down_until_it_fits(self):
        first = W.rendition(self.data, 'image/jpeg', place='hero')
        budget = first['bytes'] // 2
        r = W.rendition(self.data, 'image/jpeg', place='hero', max_bytes=budget)
        self.assertIsNotNone(r['step'])
        self.assertIn(tuple(r['step'][1:]), {(q,) for _, q in W.STEPS})
        self.assertLessEqual(r['bytes'], budget)
        self.assertFalse(r['over_budget'])
        self.assertLessEqual(max(r['width'], r['height']), 1600)

    def test_past_the_last_step_the_last_step_is_carried_and_said(self):
        with self.assertLogs(W.__name__, level='WARNING') as logs:
            r = W.rendition(self.data, 'image/jpeg', place='hero', max_bytes=500)
        self.assertTrue(r['over_budget'])
        self.assertEqual(r['step'], [round(1600 * W.STEPS[-1][0]), W.STEPS[-1][1]])
        self.assertEqual(max(r['width'], r['height']), round(1600 * W.STEPS[-1][0]))
        self.assertTrue(any('IMAGE_WEIGHT_OVER_BUDGET' in line for line in logs.output))
        self.assertEqual(decoded(r).size, (r['width'], r['height']))           # a real, carried picture

    def test_the_budget_is_under_the_g4_unit_and_g4_cannot_see_a_carried_file(self):
        from omni_prod.skill_units.perf_inline_image_weight.probe import LIMIT
        self.assertLess(W.BUDGET_BYTES * 4 / 3, LIMIT)
        page = '<img src="assets/148ai-upload-1.webp" alt="x">'               # warehouse 118: a file, not bytes
        self.assertEqual(run_unit('perf_inline_image_weight', page)['status'], 'pass')


def png_header(width, height):
    """A PNG that only declares its size: the IHDR of a bomb and a tiny IDAT."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' * 64)) + chunk(b'IEND', b''))


class TheRefusalsAreByName(unittest.TestCase):
    def refused(self, data, mime, words):
        with self.assertRaises(W.RenditionError) as ctx:
            W.rendition(data, mime)
        self.assertIn(words, str(ctx.exception))

    def test_a_file_that_is_not_an_image(self):
        self.refused(b'\xff\xd8\xff' + b'x' * 5000, 'image/jpeg', 'could not be read')

    def test_an_animated_image_is_refused(self):
        frames = [textured((300, 300), seed) for seed in range(3)]
        for fmt, mime in (('GIF', 'image/gif'), ('WEBP', 'image/webp'), ('PNG', 'image/png')):
            with self.subTest(fmt=fmt):
                out = io.BytesIO()
                frames[0].save(out, fmt, save_all=True, append_images=frames[1:])
                self.refused(out.getvalue(), mime, 'animated')

    def test_a_decompression_bomb_is_refused_before_it_is_decoded(self):
        self.refused(png_header(8000, 8000), 'image/png', 'decompression bomb')       # ours: over 60,000,000 pixels
        self.refused(png_header(30000, 30000), 'image/png', 'decompression bomb')     # and Pillow's own bound

    def test_bytes_that_are_not_the_type_they_say(self):
        self.refused(phone_jpeg((60, 40)), 'image/png', 'says image/png but its bytes are image/jpeg')

    def test_a_phone_jpeg_with_a_second_picture_is_a_still_photo(self):
        out = io.BytesIO()
        textured((800, 600)).save(out, 'MPO', save_all=True, append_images=[textured((400, 300), 2)])
        self.assertEqual(Image.open(io.BytesIO(out.getvalue())).format, 'MPO')
        r = W.rendition(out.getvalue(), 'image/jpeg', place='hero')
        self.assertEqual((r['width'], r['height']), (800, 600))                  # the first picture


def ssim_by_hand(a, b):
    """The same definition in plain Python: luma, 8x8 windows at stride 4, population moments."""
    x, y = a.convert('L'), b.convert('L')
    w, h = (x.width // 4) * 4, (x.height // 4) * 4
    px, py = x.load(), y.load()
    c1, c2, total, n = (0.01 * 255) ** 2, (0.03 * 255) ** 2, 0.0, 0
    for top in range(0, h - 7, 4):
        for left in range(0, w - 7, 4):
            xs = [px[i, j] for j in range(top, top + 8) for i in range(left, left + 8)]
            ys = [py[i, j] for j in range(top, top + 8) for i in range(left, left + 8)]
            mx, my = sum(xs) / 64, sum(ys) / 64
            vx = sum((v - mx) ** 2 for v in xs) / 64
            vy = sum((v - my) ** 2 for v in ys) / 64
            cxy = sum((p - mx) * (q - my) for p, q in zip(xs, ys)) / 64
            total += ((2 * mx * my + c1) * (2 * cxy + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))
            n += 1
    return total / n


class TheSimilarityMeasure(unittest.TestCase):
    def webp(self, img, q):
        out = io.BytesIO()
        img.save(out, 'WEBP', quality=q)
        return Image.open(io.BytesIO(out.getvalue())).convert('RGB')

    def test_it_is_the_definition_computed_by_hand(self):
        src = textured((48, 40))
        worse = self.webp(src, 20)
        self.assertAlmostEqual(W.ssim(src, worse), ssim_by_hand(src, worse), places=4)
        self.assertEqual(W.ssim(src, src), 1.0)

    def test_more_loss_scores_lower(self):
        src = textured((400, 300))
        self.assertLess(W.ssim(src, self.webp(src, 10)), W.ssim(src, self.webp(src, 90)))

    def test_a_change_one_background_hides_is_seen_on_the_other(self):
        white_square = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(white_square).rectangle((16, 16, 47, 47), fill=(255, 255, 255, 255))
        gone = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        self.assertLess(W.ssim(white_square, gone), 0.9)                       # on black the square is plain to see

    def test_different_sizes_raise(self):
        with self.assertRaises(ValueError):
            W.ssim(Image.new('RGB', (10, 10)), Image.new('RGB', (10, 11)))


class AGeneratedImageGoesTheSameWay(unittest.TestCase):
    """The butcher's 1.7 MB hero was a GENERATED image: the platform's own picture goes through the same conversion."""

    def test_the_real_collect_path_carries_the_light_rendition_and_keeps_the_verified_digest(self):
        out = io.BytesIO()
        textured((1920, 1080)).save(out, 'PNG')
        data = out.getvalue()
        self.assertGreater(len(base64.b64encode(data)), 1_700_000)
        digest = hashlib.sha256(data).hexdigest()
        with self.assertLogs(G.__name__, level='INFO') as logs, self.assertLogs(W.__name__, level='INFO') as weight:
            (img,) = G.collect(plan=plan(), evidence=evidence(digest), store=SimpleNamespace(get_bytes=lambda k: data),
                               prompt='אטליז')
        self.assertEqual(img.sha256, digest)
        self.assertIn(img.mime, W.OUTPUT_MIMES)
        self.assertLessEqual(len(img.data), W.BUDGET_BYTES)
        self.assertEqual((img.width, img.height), (1600, 900))
        self.assertEqual(img.source, (data, 'image/png'))
        self.assertEqual(img.rendition['original_sha256'], digest)
        self.assertIn('GENERATED_IMAGE index=1 changed=True', logs.output[0])
        self.assertTrue(any(f'original_sha256={digest}' in line and f'sha256={img.rendition["sha256"]}' in line
                            for line in weight.output))
        self.assertEqual(G.placement({'index.html': f'<img src="{img.marker}" alt="בשר">'}, img), 'ok')

    def test_an_icon_is_made_for_the_header(self):
        out = io.BytesIO()
        textured((1024, 1024)).save(out, 'PNG')
        data = out.getvalue()
        (img,) = G.collect(plan=plan('Product icon / logo'), evidence=evidence(hashlib.sha256(data).hexdigest()),
                           store=SimpleNamespace(get_bytes=lambda k: data), prompt='לוגו לאטליז')
        self.assertEqual((img.width, img.height, img.rendition['place']), (512, 512, 'icon'))


def plan(purpose='hero/brand visual'):
    return SimpleNamespace(requirements=[SimpleNamespace(id='r1', key=G.IMAGE_CAPABILITY, purpose=purpose,
                                                         constraints={'subject': 'נתחי בקר טריים'})])


def evidence(digest):
    return {'requirements': [{'requirement_id': 'r1', 'capability_key': G.IMAGE_CAPABILITY, 'status': 'VERIFIED',
                              'verification': {'artifacts': [{'artifact_key': 'k1', 'sha256': digest}]}}]}


class ThePageFit(unittest.TestCase):
    """fit_page: the page's images together within a budget (a4.PAGE_IMAGE_BUDGET_BYTES), each made again from its
    original, in its own file -- the transforms installed before carry the new bytes."""

    def photos(self):
        images = []
        for n, place in enumerate(('hero', 'story', 'gallery'), start=1):
            out = io.BytesIO()
            textured((1500, 1000), n).save(out, 'JPEG', quality=92)
            data = out.getvalue()
            images.append(_MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), f'צילום {n}', index=n,
                                     place=place))
        return images

    def page(self, images):
        return {'index.html': ''.join(f'<img src="{i.marker}" alt="{i.alt}">' for i in images)}

    def test_the_page_fits_its_budget_and_every_file_is_the_new_bytes(self):
        images = self.photos()
        transform = G._Transform(None, images)                                  # built before the fit, as in the worker
        uris, mimes = [i.uri for i in images], [i.mime for i in images]
        total = sum(len(i.data) for i in images)
        budget = total * 6 // 10
        with self.assertLogs(W.__name__, level='INFO') as logs:
            fit = W.fit_page(images, budget=budget)
        self.assertTrue(fit['fits'])
        self.assertEqual(fit['bytes_before'], total)
        self.assertLessEqual(sum(len(i.data) for i in images), budget)
        self.assertEqual([i.uri for i in images], uris)                        # same files: same paths, same types
        self.assertEqual([i.mime for i in images], mimes)
        repo = transform(self.page(images))
        for img in images:
            self.assertEqual(file_bytes(img.uri, repo[img.uri]), img.data)
            self.assertEqual(img.rendition['sha256'], hashlib.sha256(img.data).hexdigest())
            self.assertIsNotNone(img.rendition['step'])
            self.assertEqual(img.rendition['original_sha256'], img.sha256)
        self.assertEqual(len(fit['images']), 3)
        self.assertTrue(any('IMAGE_PAGE_FIT' in line and 'fits=True' in line for line in logs.output))

    def test_a_generated_picture_the_plan_puts_in_the_gallery_is_made_for_the_gallery(self):
        out = io.BytesIO()
        textured((2400, 1600)).save(out, 'PNG')
        data = out.getvalue()
        (img,) = G.collect(plan=plan(), evidence=evidence(hashlib.sha256(data).hexdigest()),
                           store=SimpleNamespace(get_bytes=lambda k: data), prompt='אטליז')
        self.assertEqual(img.width, 1600)
        transform = G._Transform(None, [img])
        fit = W.fit_page([img], budget=10_000_000, places={img.marker: 'gallery'})
        self.assertEqual((img.width, img.height, img.rendition['place']), (1024, 683, 'gallery'))
        self.assertEqual(fit['images'][0]['why'], 'made for hero, shown as gallery')
        repo = transform({'index.html': f'<img src="{img.marker}" alt="x">'})
        self.assertEqual(file_bytes(img.uri, repo[img.uri]), img.data)

    def test_a_budget_that_cannot_be_met_is_said_not_refused(self):
        images = self.photos()
        with self.assertLogs(W.__name__, level='WARNING') as logs:
            fit = W.fit_page(images, budget=1_000)
        self.assertFalse(fit['fits'])
        self.assertTrue(any('IMAGE_PAGE_FIT' in line and 'fits=False' in line for line in logs.output))
        self.assertTrue(all(i.rendition['over_budget'] for i in images))

    def test_what_it_cannot_read_raises(self):
        images = self.photos()[:1]
        with self.assertRaises(ValueError):
            W.fit_page(images, budget=100_000, places={'148ai-asset://upload/9': 'gallery'})
        with self.assertRaises(ValueError):
            W.fit_page(images, budget=100_000, places={images[0].marker: 'footer'})
        with self.assertRaises(ValueError):
            W.fit_page(images, budget=0)
        made_elsewhere = G.GeneratedImage(index=1, requirement_id='r', purpose='hero', mime='image/webp', width=1,
                                          height=1, sha256='0' * 64, alt='x', data=b'RIFF')   # no source, no record
        with self.assertRaises(ValueError) as ctx:
            W.fit_page([made_elsewhere], budget=100_000)
        self.assertIn('no original or no conversion record', str(ctx.exception))


class TheEvidence(unittest.TestCase):
    def test_the_build_evidence_has_every_image_with_both_digests_and_the_measure(self):
        data = phone_jpeg()
        up = _MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), 'x', index=1, place='story')
        core = SimpleNamespace(uploaded_images=[up], generated_images=None, image_fit={'fits': True})
        report = W.report(SimpleNamespace(core=core))
        [row] = report['images']
        for key in ('original_bytes', 'original_sha256', 'bytes', 'sha256', 'format', 'width', 'height', 'quality',
                    'similarity', 'threshold', 'place', 'removed', 'ms'):
            self.assertIn(key, row)
        self.assertEqual((row['kind'], row['index'], row['file'], row['original_sha256']),
                         ('upload', 1, up.uri, up.sha256))
        self.assertEqual(report['page_fit'], {'fits': True})
        self.assertNotIn(data, json.dumps(report).encode('latin-1', 'replace'))
        self.assertEqual(W.report(SimpleNamespace(core=SimpleNamespace()))['images'], [])

    def test_the_worker_writes_it_into_the_build_evidence(self):
        src = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertIn("evidence['image_weight'] = image_weight_report(engine)", src)
        self.assertLess(src.index("evidence['asset_plan'] = asset_plan_report(engine)"),
                        src.index("evidence['image_weight'] = image_weight_report(engine)"))

    def test_the_page_passes_the_unit_that_failed_on_the_butcher(self):
        data = twelve_megapixels()
        img = _MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), 'דלתות פנים', 4032, 3024)
        heavy = 'data:image/jpeg;base64,' + base64.b64encode(data).decode('ascii')
        self.assertEqual(run_unit('perf_inline_image_weight', f'<img src="{heavy}" alt="x">')['status'], 'fail')
        light = f'data:{img.mime};base64,' + base64.b64encode(img.data).decode('ascii')
        self.assertEqual(run_unit('perf_inline_image_weight', f'<img src="{light}" alt="x">')['status'], 'pass')
        self.assertEqual(img.sha256, hashlib.sha256(data).hexdigest())       # the brief's binding is the original's
        self.assertTrue(img.rendition['changed'])


class TheWorkerImage(unittest.TestCase):
    def test_the_worker_image_installs_the_same_pillow_the_tests_use(self):
        prod = (ROOT / 'requirements-production.txt').read_text(encoding='utf-8').split()
        test = (ROOT / 'requirements-test.txt').read_text(encoding='utf-8').split()
        pin = [line for line in test if line.lower().startswith('pillow==')]
        self.assertEqual(len(pin), 1)
        self.assertIn(pin[0], prod)

    def test_this_pillow_encodes_webp(self):
        from PIL import features
        self.assertTrue(features.check('webp'))


if __name__ == '__main__':
    unittest.main()
