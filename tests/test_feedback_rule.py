"""The browser check's second-round decision, browser-free (the same source runs inside PROBE in the sandbox).
Production 2026-11-17 (bld_d36b3b4e, "148 doors"): a lead form that kept its success line and rewrote it per save
was failed as "feedback_disappears"; these cases run in every CI job, the real-browser ones in
tests/test_browser_probe.py where Chromium exists."""
import inspect
import unittest

from omni_prod.browser_probe import PROBE, feedback_missing


class TheFeedbackRule(unittest.TestCase):
    """The decision of the second round, browser-free (the same source runs inside PROBE). Rounds as PROBE records
    them; the first one of each case is the production lead form of bld_d36b3b4e."""
    FIRST = {'revealed': ['הפנייה עבור בדיקה 1 נשמרה בהצלחה'], 'ok_write': True}

    def test_a_visible_message_rewritten_by_the_second_save_is_feedback(self):
        second = {'revealed': [], 'updated': ['הפנייה עבור בדיקה 2 נשמרה בהצלחה'], 'ok_write': True}
        self.assertFalse(feedback_missing(self.FIRST, second))

    def test_nothing_revealed_and_nothing_rewritten_is_missing_feedback(self):
        self.assertTrue(feedback_missing(self.FIRST, {'revealed': [], 'updated': [], 'ok_write': True}))

    def test_a_revealed_message_is_feedback(self):
        self.assertFalse(feedback_missing(self.FIRST, {'revealed': ['נשמר'], 'updated': [], 'ok_write': True}))

    def test_a_failed_second_save_is_not_judged(self):
        self.assertFalse(feedback_missing(self.FIRST, {'revealed': [], 'updated': [], 'ok_write': False}))

    def test_the_sandbox_runs_this_same_rule(self):
        self.assertIn(inspect.getsource(feedback_missing), PROBE)
        self.assertIn('elif feedback_missing(first, second):', PROBE)


if __name__ == '__main__':
    unittest.main()
