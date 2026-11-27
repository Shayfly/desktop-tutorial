"""Visual plan S0 (a): the hero photo's colour overlay is painted ABOVE the photo and UNDER the text.

Claude's bug: library.css gave `.panel--photo::before` z-index 0 and left the <img> at auto; the image is the panel's
last child in the markup, so it painted over the overlay and the panel's facts sat on the raw photo (the lawyer page
with a pure green photo read (0, 255, 0) at the panel's bottom edge, where the overlay is 94% primary).

This is the real path: section_library.page() with a solid green photo, rendered in Chromium, one page per art
direction, on a desktop and a phone viewport. Where the overlay is 94% primary the pixel must be the overlay mixed over
the photo, within 8 per channel -- not the photo's own colour."""
import base64
import copy
import io
import re
import unittest

from omni_prod import section_library as L
from omni_prod.section_library import demo_law_firm as D
from tests.test_section_library_conformance import contract_for

GREEN = (0, 255, 0)
SAMPLE = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
VIEWPORTS = {'desktop': (1440, 900), 'phone': (390, 800)}
TOLERANCE = 8


def photo_page(direction, palette):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (1200, 900), GREEN).save(buf, 'PNG')
    src = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    content = copy.deepcopy(D.CONTENT)
    content['direction'] = direction
    # the boxed panel with the picture is the `split` hero; the photo-led heroes (visual plan S1) put the facts in a strip
    # under the picture, so this overlay is only reachable when the content names `split`
    content['layout'] = {'hero': 'split'}
    content['hero']['image'] = {'src': src, 'alt': 'תמונה', 'width': 1200, 'height': 900}
    contract = contract_for(palette)
    doc, _ = L.page(content, contract)
    return re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc), contract


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class HeroOverlayStacking(unittest.TestCase):
    def test_the_overlay_is_above_the_photo_in_every_direction_and_viewport(self):
        try:
            from playwright.sync_api import sync_playwright
            from PIL import Image
        except ImportError:  # pragma: no cover
            self.skipTest('playwright and pillow are required to render the page')
        seen = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                doc, contract = photo_page(direction, palette)
                primary = hex_rgb(contract['tokens']['--color-primary'])
                # the gradient's bottom stop is 94% primary over what is under it: the photo, if the overlay is above it
                expected = tuple(round(0.94 * c + 0.06 * g) for c, g in zip(primary, GREEN))
                for name, (w, h) in VIEWPORTS.items():
                    pg = b.new_page(viewport={'width': w, 'height': h})
                    pg.set_content(doc)
                    pg.wait_for_timeout(600)
                    panel = pg.locator('.panel--photo')
                    self.assertEqual(panel.count(), 1, f'{direction}/{name}: the hero photo panel is not on the page')
                    panel.scroll_into_view_if_needed()
                    box = panel.bounding_box()
                    shot = Image.open(io.BytesIO(pg.screenshot(clip=box))).convert('RGB')
                    sw, sh = shot.size
                    got = [shot.getpixel((x, sh - 6)) for x in (6, sw // 2, sw - 6)]
                    seen[f'{direction}/{name}'] = (expected, got)
                    for px in got:
                        self.assertTrue(all(abs(a - e) <= TOLERANCE for a, e in zip(px, expected)),
                                        f'{direction}/{name}: the panel edge reads {px}, the overlay should give {expected} '
                                        f'(the photo itself is {GREEN}): the photo is painted over the overlay')
                    pg.close()
            b.close()
        self.assertEqual(len(seen), len(SAMPLE) * len(VIEWPORTS))

    def test_the_stacking_is_photo_then_overlay_then_text(self):
        css = (L.HERE / 'library.css').read_text(encoding='utf-8')
        z = lambda sel: int(re.search(re.escape(sel) + r'\s*\{[^}]*?z-index:\s*(\d+)', css).group(1))
        photo, overlay, text = z('.panel-photo'), z('.panel--photo::before'), z('.panel--photo > :not(img)')
        self.assertLess(photo, overlay)
        self.assertLess(overlay, text)

    def test_the_library_version_moved_with_the_page_bytes(self):
        self.assertEqual(L.LIBRARY_VERSION, '4')       # S0 moved it to 3, the photo-led heroes (S1) to 4


if __name__ == '__main__':
    unittest.main()
