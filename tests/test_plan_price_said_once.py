"""One price, said once (the owner, 2026-11-16: the chat said "45-200" and the panel said 500; one of them was false).

The price of a build is set by the customer's plan alone (pricing.m5_build_terms). When the plan is known the chat says
that number from gate 1; a range is said only when no plan is known. The real supervisor, architect and verifier run."""
import unittest
from pathlib import Path

from omni_prod.intake import approval_flow as AF
from omni_prod.pricing import M5_CLASS_BUILD_CREDITS, CostClass
from tests import test_venice_live_wiring as _W


class PlanPriceSaidOnce(unittest.TestCase):
    # the real two-gate harness, borrowed without re-running its tests here
    make, say, to_gate1, approve = (_W.TwoGates.make, _W.TwoGates.say, _W.TwoGates.to_gate1, _W.TwoGates.approve)

    def make_plan_known(self, credits):
        self.make(credits=credits)
        self.sup.plan_credits = None
        self.sup.__init__(briefs=self.briefs, store=self.store, architect=self.arch, credits=credits,
                          credits_from_plan=True)

    def test_a_known_plan_is_one_number_at_gate1_never_a_range(self):
        heavy = M5_CLASS_BUILD_CREDITS[CostClass.HEAVY]
        self.make_plan_known(heavy)
        t = self.to_gate1()
        self.assertIn(f'This build takes {heavy} from your balance.', t.reply)
        self.assertNotIn('Estimate:', t.reply)
        self.assertNotIn('45', t.reply)
        self.assertEqual(t.venice['cost_range_credits'], [heavy, heavy])

    def test_gate2_repeats_the_same_number_and_flags_nothing(self):
        heavy = M5_CLASS_BUILD_CREDITS[CostClass.HEAVY]
        self.make_plan_known(heavy)
        r = self.approve(self.to_gate1())
        self.assertEqual(r.plan['spec_gate']['cost'], {'range': [heavy, heavy], 'exact': heavy, 'outside_range': None})
        self.assertIn(f'The price: {heavy} from your balance, as I said.', r.reply)
        self.assertNotIn('more than I said', r.reply)
        self.assertNotIn('earlier I said', r.reply)

    def test_asking_the_cost_before_approval_gives_the_plan_number(self):
        self.make_plan_known(500)
        self.to_gate1()
        r = self.say('how much will it cost?')
        self.assertIn('This build takes 500 from your balance.', r.reply)
        self.assertNotIn('45–200', r.reply)

    def test_hebrew_says_the_plan_number(self):
        self.make_plan_known(500)
        t = self.to_gate1('אני צריך כלי פנימי פשוט לצוות למעקב אחרי השאלת ציוד, בלי התחברות ובלי מידע אישי', lang='he')
        self.assertIn('הבנייה הזו תוריד 500 מהיתרה שלכם.', t.reply)
        self.assertNotIn('הערכה:', t.reply)

    def test_a_default_is_not_a_price_and_keeps_the_estimate(self):
        self.make(credits=60)                          # investor_app's default when no plan could be read
        t = self.to_gate1()
        self.assertIsNone(self.sup.plan_credits)
        self.assertIn('Estimate: this build takes between 45 and 200 from your balance.', t.reply)

    def test_a_plan_price_that_is_not_a_number_is_refused(self):
        for bad in (True, -1, '500', 5.0):
            with self.assertRaises(ValueError, msg=repr(bad)):
                AF.cost_range(None, bad)

    def test_every_language_has_both_lines(self):
        for lang, t in AF.TEXT.items():
            self.assertIn('{c}', t['price'], lang)
            self.assertIn('{exact}', t['exact_same'], lang)

    def test_the_live_supervisor_marks_the_plan_price_only_after_the_plan_was_read(self):
        whole = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        start = whole.index('def _supervisor(key: str')          # read as text: this container has no fastapi
        src = whole[start:whole.index('\ndef ', start + 1)]
        self.assertIn('credits_from_plan=credits_from_plan', src)
        set_true, terms = src.index('credits_from_plan = True'), src.index('m5_build_terms(plan.code)')
        self.assertGreater(set_true, terms)
        self.assertLess(src.index('credits_from_plan = False'), src.index('try:'))


if __name__ == '__main__':
    unittest.main()
