"""D5 on the path a real build takes (found 2026-11-22, Claude's bug): the build contract plans media from the customer's
own words, without the approved brief, so the content-site line D5 reads never reached it -- every production build
since D5 (#442, 2026-11-17) planned no image (32 builds, media.image.generate NOT_REQUIRED). test_default_hero.py tested
CreativeDirector on the full prompt and passed while production failed; this test goes through ProductArchitect.compile,
the contract the worker builds from (worker_tasks: capability_plan = build_contract.capability_plan)."""
import unittest

from omni_prod.product_architect import ProductArchitect
from omni_prod.rehearsal import approved_prompt

ANSWERS = {"content_only": "yes", "personal_data": "no", "login": "none"}


def media(request, answers=ANSWERS):
    result = ProductArchitect().compile(approved_prompt(request, answers), project_id='prj_test', contract_version=1)
    contract = getattr(result, 'contract', result)
    return [(q.key, q.required) for q in contract.capability_plan.requirements if q.key.startswith('media.')]


class D5OnTheContract(unittest.TestCase):
    def test_a_content_site_without_a_photo_gets_an_optional_main_image(self):
        self.assertEqual(media('אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456.'),
                         [('media.image.generate', False)])

    def test_no_pictures_means_no_image(self):
        self.assertEqual(media('אתר לאטליז "בשר השכונה" בחיפה. טלפון 04-8123456. בלי תמונות.'), [])

    def test_an_explicit_main_image_stays_required(self):
        self.assertEqual(media('אתר לאטליז "בשר השכונה" בחיפה. טלפון 04-8123456. תמונה ראשית: דלפק בשר.'),
                         [('media.image.generate', True)])

    def test_an_app_gets_no_default_image(self):
        self.assertEqual(media('מערכת לניהול תורים למספרה עם התחברות לקוחות',
                               {"content_only": "no", "personal_data": "yes", "login": "simple"}), [])


if __name__ == '__main__':
    unittest.main()
