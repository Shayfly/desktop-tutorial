"""A4 decides how many pictures a build generates (the owner, 2026-11-17: as many as the customer wants while they
have credits; 2026-11-26: "אין דבר כזה תקרת תמונות לבטל מיד" -- the first "up to 3 per build" is gone). The planner
plans A4's answer as that many picture requirements, one picture each -- the number the price, the provider calls and
the page all read, with no provider batch (num_outputs) to bound it."""
import unittest

from omni_prod import a4
from omni_prod.universal_brain import OmniUniversalBrain

IMAGE = 'media.image.generate'


def requirements(prompt):
    plan = OmniUniversalBrain().decide(prompt).capabilities
    return [r for r in plan.requirements if r.key == IMAGE]


def requirement(prompt):
    found = requirements(prompt)
    return found[0] if found else None


class Pictures(unittest.TestCase):
    def test_no_number_is_one(self):
        self.assertEqual(a4.pictures('אתר לקפה עם תמונה ראשית של כוס קפה'), {'asked': 1, 'uploaded': 0, 'count': 1})

    def test_digits_and_words(self):
        self.assertEqual(a4.pictures('אתר למסעדה עם 2 תמונות של המנות')['count'], 2)
        self.assertEqual(a4.pictures('אתר למסעדה עם שלוש תמונות של המנות')['count'], 3)
        self.assertEqual(a4.pictures('A cafe site with two images of the place')['count'], 2)

    def test_there_is_no_cap(self):
        """The owner, 2026-11-26: there is no image cap. Eight asked are eight; thirty are thirty."""
        self.assertEqual(a4.pictures('תפריט עם 8 תמונות של מנות'), {'asked': 8, 'uploaded': 0, 'count': 8})
        self.assertEqual(a4.pictures('גלריה עם 30 תמונות של העבודות')['count'], 30)
        self.assertFalse(hasattr(a4, 'FIRST_CAP'))

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
    def test_the_number_of_pictures_is_what_a4_decided(self):
        three = requirements('אתר למסעדה עם תמונה ראשית ועוד, סך הכל 3 תמונות של המנות')
        self.assertEqual([r.id for r in three],
                         ['cap-media-image-generate', 'cap-media-image-generate-2', 'cap-media-image-generate-3'])
        self.assertEqual({r.quantity for r in three}, {1})                 # one picture per requirement
        self.assertEqual(len({r.constraints['subject'] for r in three}), 1)  # a number of pictures shares one subject
        self.assertEqual([r.quantity for r in requirements('אתר לקפה עם תמונה ראשית של כוס קפה')], [1])

    def test_nothing_is_cut(self):
        with self.assertNoLogs('omni_prod.capability_planner', 'WARNING'):
            eight = requirements('אתר למסעדה עם באנר ו-8 תמונות של מנות')
        self.assertEqual(len(eight), 8)
        self.assertEqual({r.quantity for r in eight}, {1})
        self.assertFalse(any('pictures_asked' in r.constraints for r in eight))

    def test_a_number_alone_generates_nothing(self):
        """Founder decision 2026-10-07 #28: bare "pictures" usually means the customer's uploads. A4 says how many,
        never whether."""
        self.assertIsNone(requirement('אתר למסעדה עם 3 תמונות'))

    def test_an_icon_is_one(self):
        # one requirement per picture: an icon is ONE requirement, whatever number of pictures the request states
        self.assertEqual([(r.purpose, r.quantity) for r in requirements('אתר עם לוגו ו-4 תמונות')],
                         [('product icon', 1)])


if __name__ == '__main__':
    unittest.main()
