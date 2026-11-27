"""The owner, 2026-11-19, on the law-firm build bld_b0eb47a5: "רמה נמוכה ... אני רוצה מקצועיות". The PRO gate
(skill_units/design_minimum) judges a business page against a professional minimum. It enters at warn (rule 4) and
blocks only after three calibration builds. The ok fixture is the real butcher production page; the broken fixture is
the shape of the owner's law-firm build."""
import os
import unittest
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.skill_units import gate as G
from omni_prod.skills_runtime import LANDING_CONVERSION

CTA = '<a href="tel:035551234">התקשרו</a>'


def page(sections=4, h1=1, visual=True, cta=2):
    body = ''.join(f'<h1>כותרת</h1>' for _ in range(h1))
    body += ''.join(f'<section><h2>חלק {i}</h2><p>תוכן</p></section>' for i in range(sections))
    body += '<img src="/assets/hero.webp" alt="משרד">' if visual else ''
    body += CTA * cta
    return f'<html><body>{body}</body></html>'


class DesignMinimum(unittest.TestCase):
    def test_the_real_business_page_passes_and_the_bare_one_falls(self):
        for name, html, _ in U.fixtures('design_minimum', 'ok'):
            self.assertEqual(U.run('design_minimum', html), {'status': 'pass'}, name)
        broken = U.fixtures('design_minimum', 'broken')
        self.assertTrue(broken)
        for name, html, expected in broken:
            self.assertEqual(U.run('design_minimum', html)['code'], expected['code'], name)

    def test_each_rule_alone_fails_the_page(self):
        self.assertEqual(U.run('design_minimum', page()), {'status': 'pass'})
        for kw, why in ((dict(sections=3), 'sections'), (dict(h1=0), 'heading'), (dict(h1=2), 'heading'),
                        (dict(visual=False), 'visual'), (dict(cta=1), 'once')):
            with self.subTest(kw):
                r = U.run('design_minimum', page(**kw))
                self.assertEqual(r['code'], 'DESIGN_TOO_BASIC')
                self.assertEqual(len(r['findings']), 1, r)
                self.assertIn(why, r['findings'][0]['why'])

    def test_a_css_background_image_is_a_visual(self):
        html = page(visual=False).replace('<body>', '<body><div style="background-image:url(/assets/hero.webp)"></div>')
        self.assertEqual(U.run('design_minimum', html), {'status': 'pass'})

    def test_an_icon_is_not_a_visual(self):
        # visual plan S0 (2026-11-27): the gate counted the phone, WhatsApp and menu icons as the page's visual
        icon = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M3 5h18v2H3z"/></svg>'
        controls = (f'<button type="button">{icon}</button><a href="tel:035551234">{icon}</a>'
                    f'<details><summary>{icon}תפריט</summary></details>')
        icons_only = page(visual=False).replace('<body>', f'<body>{controls}')
        r = U.run('design_minimum', icons_only)
        self.assertEqual(r['code'], 'DESIGN_TOO_BASIC')
        self.assertEqual(len(r['findings']), 1, r)
        self.assertIn('visual', r['findings'][0]['why'])
        loose_icon = page(visual=False).replace('<body>', f'<body>{icon}')
        self.assertEqual(U.run('design_minimum', loose_icon)['code'], 'DESIGN_TOO_BASIC',
                         'an icon-sized svg is an icon wherever it sits')

    def test_an_svg_inside_a_control_is_not_a_visual_whatever_its_size(self):
        big = '<svg viewBox="0 0 600 400" role="img"><rect width="600" height="400"/></svg>'
        in_link = page(visual=False).replace('<body>', f'<body><a href="/x">{big}</a>')
        self.assertEqual(U.run('design_minimum', in_link)['code'], 'DESIGN_TOO_BASIC')

    def test_an_icon_sized_img_is_not_a_visual_and_a_real_one_is(self):
        tiny = page(visual=False).replace('<body>', '<body><img src="/i/phone.png" width="24" height="24" alt="">')
        self.assertEqual(U.run('design_minimum', tiny)['code'], 'DESIGN_TOO_BASIC')
        for real in ('<img src="/assets/hero.webp" width="1200" height="800" alt="משרד">',
                     '<img src="/assets/hero.webp" alt="משרד">',
                     '<picture><source srcset="/a.webp"><img src="/a.jpg" alt="x" width="320"></picture>',
                     '<video src="/a.mp4"></video>',
                     '<svg viewBox="0 0 600 400" role="img"><rect width="600" height="400"/></svg>'):
            with self.subTest(real):
                self.assertEqual(U.run('design_minimum', page(visual=False).replace('<body>', f'<body>{real}')),
                                 {'status': 'pass'})

    def test_the_real_library_pages_keep_their_verdict(self):
        # the real path: section_library renders. A page with a photo or the panel's drawing passes; the barest shape,
        # whose only svg are icons in the header and the action bar, falls on the visual finding alone.
        from omni_prod import section_library as L
        from tests.test_section_library_conformance import contract_for, shapes
        verdicts = {}
        for name in ('full', 'photo_hero', 'minimal'):
            doc, _ = L.page(dict(shapes()[name], direction='formal'), contract_for('counsel'))
            r = U.run('design_minimum', doc)
            verdicts[name] = r['status'] if r['status'] == 'pass' else [f['why'][:27] for f in r['findings']]
        self.assertEqual(verdicts, {'full': 'pass', 'photo_hero': 'pass', 'minimal': ['no image or visual anywhere']})

    def test_a_page_with_no_contact_action_is_not_judged(self):
        self.assertEqual(U.run('design_minimum', '<html><body><canvas></canvas></body></html>'), {'status': 'pass'})

    def test_the_gate_is_the_unit_and_warns_until_calibrated(self):
        self.assertEqual(G.gate_units('PRO'), ['design_minimum'])
        self.assertIn('PRO', G.CALIBRATING)
        self.assertIn('PRO', G.WORKER_GATES)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_PRO', None)
            self.assertEqual(G.mode('PRO'), 'warn')

    def test_the_generator_is_told_the_professional_shape(self):
        self.assertIn('at least four separate <section> blocks', LANDING_CONVERSION.guidance)
        self.assertIn('a grid of cards', LANDING_CONVERSION.guidance)


if __name__ == '__main__':
    unittest.main()
