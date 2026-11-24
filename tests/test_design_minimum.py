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
