"""A4 decides how many pictures a build generates (the owner, 2026-11-17: as many as the customer wants while they
have credits; to start, up to 3 per build). The planner writes A4's answer as the image requirement's quantity --
the number the price, the provider call (num_outputs) and the page all read."""
import unittest

from omni_prod import a4
from omni_prod.universal_brain import OmniUniversalBrain

IMAGE = 'media.image.generate'


def requirement(prompt):
    plan = OmniUniversalBrain().decide(prompt).capabilities
    found = [r for r in plan.requirements if r.key == IMAGE]
    return found[0] if found else None


class Pictures(unittest.TestCase):
    def test_no_number_is_one(self):
        self.assertEqual(a4.pictures('אתר לקפה עם תמונה ראשית של כוס קפה'), {'asked': 1, 'uploaded': 0, 'count': 1})

    def test_digits_and_words(self):
        self.assertEqual(a4.pictures('אתר למסעדה עם 2 תמונות של המנות')['count'], 2)
        self.assertEqual(a4.pictures('אתר למסעדה עם שלוש תמונות של המנות')['count'], 3)
        self.assertEqual(a4.pictures('A cafe site with two images of the place')['count'], 2)

    def test_past_the_cap_is_cut_to_it(self):
        got = a4.pictures('תפריט עם 8 תמונות של מנות')
        self.assertEqual((got['asked'], got['count']), (8, a4.FIRST_CAP))
        self.assertEqual(a4.FIRST_CAP, 3)

    def test_the_customers_photos_fill_places_first(self):
        prompt = 'אתר עם 5 תמונות\nsrc 148ai-asset://upload/1 and 148ai-asset://upload/2 and 148ai-asset://upload/1'
        self.assertEqual(a4.pictures(prompt), {'asked': 5, 'uploaded': 2, 'count': 3})
        self.assertEqual(a4.pictures('אתר עם 3 תמונות 148ai-asset://upload/1 148ai-asset://upload/2')['count'], 1)

    def test_never_below_one(self):
        self.assertEqual(a4.pictures('2 תמונות 148ai-asset://upload/1 148ai-asset://upload/2 '
                                     '148ai-asset://upload/3')['count'], 1)

    def test_a_number_that_is_not_a_count_of_pictures(self):
        self.assertEqual(a4.pictures('מסעדה עם 40 מקומות ותמונה ראשית')['asked'], 1)
        self.assertEqual(a4.pictures('גרסה 2.5 תמונות')['asked'], 1)      # "2.5" is not five pictures

    def test_only_the_customers_request_is_read(self):
        prompt = 'אתר עם תמונה ראשית\n--- Approved project brief\nPages: 7 images of the team'
        self.assertEqual(a4.pictures(prompt)['asked'], 1)


class PlannerAsksA4(unittest.TestCase):
    def test_quantity_is_what_a4_decided(self):
        self.assertEqual(requirement('אתר למסעדה עם תמונה ראשית ועוד, סך הכל 3 תמונות של המנות').quantity, 3)
        self.assertEqual(requirement('אתר לקפה עם תמונה ראשית של כוס קפה').quantity, 1)

    def test_a_cut_is_written_on_the_requirement(self):
        with self.assertLogs('omni_prod.capability_planner', 'WARNING') as logs:
            r = requirement('אתר למסעדה עם באנר ו-8 תמונות של מנות')
        self.assertEqual((r.quantity, r.constraints['pictures_asked']), (3, 8))
        self.assertIn('PICTURES_CUT asked=8 uploaded=0 generated=3', logs.output[0])
        self.assertNotIn('pictures_asked', requirement('אתר עם באנר ו-2 תמונות').constraints)

    def test_a_number_alone_generates_nothing(self):
        """Founder decision 2026-10-07 #28: bare "pictures" usually means the customer's uploads. A4 says how many,
        never whether."""
        self.assertIsNone(requirement('אתר למסעדה עם 3 תמונות'))

    def test_an_icon_is_one(self):
        r = requirement('אתר עם לוגו ו-4 תמונות')
        self.assertEqual((r.purpose, r.quantity), ('product icon', 1))


if __name__ == '__main__':
    unittest.main()
