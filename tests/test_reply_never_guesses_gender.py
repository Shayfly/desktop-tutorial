"""Rehearsal 44650878701 (luna, production path, 2026-11-20): the agent wrote "תרצי להציג מחירון" to a customer who
never said their gender. The reply rules now say: in Hebrew, the plural or gender-neutral wording, never a guess."""
import unittest

from omni_prod.intake.interpreter import SYSTEM


class TheReplyNeverGuessesGender(unittest.TestCase):
    def test_the_reply_rules_say_plural_or_neutral_and_never_a_guess(self):
        rules = SYSTEM[SYSTEM.index('Reply rules'):]
        self.assertIn('in Hebrew address the customer in the plural (אתם', rules)
        self.assertIn('never guess their gender', rules)


if __name__ == '__main__':
    unittest.main()
