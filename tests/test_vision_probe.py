"""The live vision probe (omni_prod.vision_probe) before it is run against paid providers: the pictures are what they
claim (decoded pixel by pixel), a blind model that guesses one fixed answer cannot pass, a provider error is a failed
probe and not a crash, the run is bounded, and a model routed for images that fails ends the run non-zero."""
from __future__ import annotations

import io
import json
import unittest
import zlib
from contextlib import redirect_stdout
from types import SimpleNamespace

from omni_prod import vision_probe as vp
from omni_prod.model_gateway import _image_mime


def pixels(png: bytes):
    assert png.startswith(b'\x89PNG\r\n\x1a\n')
    pos, idat, size = 8, b'', None
    while pos < len(png):
        n = int.from_bytes(png[pos:pos + 4], 'big'); kind = png[pos + 4:pos + 8]; data = png[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            size = int.from_bytes(data[:4], 'big')
        if kind == b'IDAT':
            idat += data
        pos += 12 + n
    raw, row = zlib.decompress(idat), 1 + 3 * size
    return size, lambda x, y: tuple(raw[y * row + 1 + 3 * x: y * row + 4 + 3 * x])


class Seeing:
    """Answers from the pixels it is sent -- a model that really looks."""
    def complete(self, *, images, **kw):
        size, px = pixels(images[0])
        colour = 'red' if px(size // 2, size // 2)[0] > 200 else 'blue'
        shape = 'triangle' if px(int(size * 0.2), int(size * 0.75)) != (255, 255, 255) and \
            px(size // 2, int(size * 0.88)) == (255, 255, 255) else 'circle'
        return json.dumps({'shape': shape, 'color': colour})


class Blind:
    def complete(self, **kw):
        return 'Here you go: {"shape": "circle", "color": "red"}'


class Down:
    def complete(self, **kw):
        raise TimeoutError('provider timed out')


def catalog(*names):
    return [SimpleNamespace(endpoint=SimpleNamespace(model=n, name=n)) for n in names]


class VisionProbe(unittest.TestCase):
    def test_the_pictures_are_real_pngs_of_what_they_claim(self):
        for name, (shape, colour) in vp.PICTURES.items():
            png = vp.picture(name)
            self.assertEqual(_image_mime(png), 'image/png')
            size, px = pixels(png)
            self.assertEqual(size, vp.SIZE)
            self.assertEqual(px(size // 2, size // 2), vp._RGB[colour])     # the shape covers the centre
            self.assertEqual(px(2, 2), (255, 255, 255))                     # white background
        self.assertNotEqual(vp.picture('red circle'), vp.picture('blue triangle'))

    def test_a_model_that_sees_passes_and_a_fixed_guess_cannot(self):
        results = vp.run(catalog('seer', 'blind', 'down'),
                         lambda ep: {'seer': Seeing(), 'blind': Blind(), 'down': Down()}[ep.model])
        by = {r['model']: r for r in results}
        self.assertTrue(by['seer']['passed'], by['seer'])
        self.assertFalse(by['blind']['passed'])
        self.assertEqual([a['ok'] for a in by['blind']['answers']], [True, False])
        self.assertFalse(by['down']['passed'])
        self.assertIn('TimeoutError', by['down']['answers'][0]['error'])

    def test_a_routed_model_that_fails_ends_the_run_non_zero_and_says_so(self):
        results = vp.run(catalog('seer', 'blind'), lambda ep: Seeing() if ep.model == 'seer' else Blind())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(vp.report(results, {'seer'}), 0)
            self.assertEqual(vp.report(results, {'seer', 'blind'}), 1)
        self.assertIn('::error title=vision probe calibration::blind is routed for images', out.getvalue())
        self.assertIn('::notice title=vision probe blind::FAIL (not routed for images)', out.getvalue())

    def test_pending_entries_do_not_consume_the_probe_bound(self):
        pending = [SimpleNamespace(endpoint=None)] * vp.MAX_MODELS
        result = vp.run(pending + catalog("seer"), lambda ep: Seeing())
        self.assertEqual([r["model"] for r in result], ["seer"])

    def test_the_run_is_bounded_and_never_empty(self):
        with self.assertRaises(SystemExit):
            vp.run([], lambda ep: Seeing())
        with self.assertRaises(SystemExit):
            vp.run(catalog(*[f'm{i}' for i in range(vp.MAX_MODELS + 1)]), lambda ep: Seeing())


if __name__ == '__main__':
    unittest.main()
