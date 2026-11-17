"""The owner's own conversation, 2026-11-17 (prj_9GM6q4KQX-tu9A, "קצביה של שמעון"): a photo of Shimon, then "make a
caricature of him" -- a change the platform cannot make yet. The same image question came back three times, and
"do what you want" was not taken either ("גם ככה לא מקשיב"). Now: the change is said once; asked for again, or handed
over, the question's own recommendation is taken and said, and the conversation moves on.
Real path: ConversationSupervisor.turn (the in-memory stores stand in for SQL only)."""
import unittest

from omni_prod import discovery as d
from omni_prod.intake import image_answers as A
from tests.test_image_answer_loop import say, uploaded


def to_image_use():
    s, briefs = uploaded()
    say(s, 'זה שמעון, הבעלים')
    return s, briefs


def use_of(briefs):
    """The decided use: the open field, or the placed image's (an inspiration image is placed at once)."""
    b = briefs.latest('p').brief
    placed = b.assets.get('images') or []
    return (b.fields.get('image_use') or {}).get('value') or (placed[-1].get('use') if placed else None)


class TheCaricatureIsNotALoop(unittest.TestCase):
    def test_a_caricature_is_a_change(self):
        self.assertEqual(A.answers_for(d.BY_ID['image_use'], 'תעשו ממנו קריקטורה של קצב'), {'image_use': 'change'})

    def test_the_first_ask_says_it_is_not_available_and_keeps_the_question(self):
        s, briefs = to_image_use()
        t = say(s, 'תעשו ממנו קריקטורה של קצב')
        self.assertIn('עוד לא זמין', t.reply)
        self.assertIsNone(use_of(briefs))
        self.assertEqual(briefs.latest('p').brief.hints.get('image_change'), 'asked')   # heard as a change, said once

    def test_the_second_ask_takes_the_recommendation_and_says_so(self):
        s, briefs = to_image_use()
        say(s, 'תעשו ממנו קריקטורה של קצב')
        t = say(s, 'אמרתי קריקטורה')
        self.assertEqual(use_of(briefs), 'as_is')
        self.assertIn('בחרתי', t.reply)
        self.assertNotIn('ומה לעשות עם התמונה', t.reply)

    def test_handing_it_over_takes_the_recommendation(self):
        s, briefs = to_image_use()
        say(s, 'מה שאתה רוצה תעשה אתה')
        self.assertEqual(use_of(briefs), 'as_is')

    def test_a_clear_choice_still_wins(self):
        s, briefs = to_image_use()
        say(s, 'רק השראה')
        self.assertEqual(use_of(briefs), 'inspiration')


if __name__ == '__main__':
    unittest.main()
