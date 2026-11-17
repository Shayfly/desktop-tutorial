"""The conversation rehearsal (phase 4) runs the real supervisor with an injected interpreter; here a scripted model
stands in for the live one, so the harness itself -- the scripted customer, the bounds and the acceptance -- is
tested before it costs a model call."""
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.intake.interpreter import DeterministicInterpreter


class Scripted:
    """Deterministic answers, reported as a model's, with a cost: the harness must count both."""
    name = 'model'

    def __init__(self):
        self.gateway = type('G', (), {'task': 'conversation'})()
        self.inner = DeterministicInterpreter()

    def interpret(self, message, brief=None):
        out = self.inner.interpret(message, brief)
        object.__setattr__(out, 'interpreter', 'model:scripted') if hasattr(out, '__dataclass_fields__') else None
        return out


class TheHarness(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_every_scenario_runs_bounded_with_no_card_and_keeps_its_facts(self):
        for name in R.SCENARIOS:
            r = R.run_scenario(name, Scripted())
            self.assertLessEqual(r['turns'], R.MAX_TURNS, name)
            self.assertEqual(r['cards'], 0, name)
            self.assertEqual(r['facts_missing'], [], (name, r['transcript'][-1]))
            self.assertTrue(r['approval'], (name, [t['agent'][:80] for t in r['transcript']]))

    def test_rules_alone_do_not_pass(self):
        r = R.run_scenario('butcher', DeterministicInterpreter())
        self.assertFalse(r['passed'])                             # no model wrote a reply
        self.assertTrue(all(not m.startswith('model') for m in r['models']))

    def test_each_acceptance_condition_fails_on_its_own(self):
        ok = dict(cards=0, reached=True, missing=[], models={'model:x'})
        self.assertTrue(R.accepted(**ok))
        for bad in ({'cards': 1}, {'reached': False}, {'missing': ['03-5550000']}, {'models': {'deterministic'}}):
            self.assertFalse(R.accepted(**{**ok, **bad}), bad)

    def test_a_card_fails_the_scenario(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '0'}):          # cards come back without the agent
            r = R.run_scenario('butcher', Scripted())
        self.assertGreater(r['cards'], 0)
        self.assertFalse(r['passed'])

    def test_turns_are_bounded(self):
        with mock.patch.object(R, 'MAX_TURNS', 2):
            r = R.run_scenario('doors', Scripted())
        self.assertEqual(r['turns'], 2)
        self.assertFalse(r['approval'])

    def test_an_unknown_scenario_is_an_error(self):
        with self.assertRaises(SystemExit):
            with mock.patch('omni_prod.investor_app._live_components', side_effect=AssertionError('not reached')):
                R.main(['nope'])


if __name__ == '__main__':
    unittest.main()
