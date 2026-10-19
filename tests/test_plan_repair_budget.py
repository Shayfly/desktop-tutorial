"""Per-plan repair budget: the seam exists, it is OFF, and today's behaviour is unchanged (2026-10-19)."""
import os
import unittest
from unittest import mock

from omni_prod.autonomous_core import REPAIR_ROUNDS_HARD_MAX, AutonomousProductEngine
from omni_prod.pricing import DEFAULT_REPAIR_ROUNDS, PlanCode, repair_rounds_for_plan

from tests.test_j3_three_repair_round_policy import Architect, Generator, Repairer, Verifier


class SeamIsOffByDefault(unittest.TestCase):
    def test_every_plan_gets_three_while_the_budget_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_PLAN_REPAIR_BUDGET', None)
            for plan in (PlanCode.FREE, PlanCode.AMATEUR, PlanCode.PRO, PlanCode.STUDIO, PlanCode.ENTERPRISE, 'pro'):
                self.assertEqual(repair_rounds_for_plan(plan), 3)
            self.assertEqual(DEFAULT_REPAIR_ROUNDS, 3)

    def test_plan_values_once_switched_on(self):
        on = {p: repair_rounds_for_plan(p, enabled=True) for p in ('amateur', 'pro', 'studio', 'free', 'enterprise', 'basic', 'business', 'nope')}
        self.assertEqual(on, {'amateur': 3, 'pro': 5, 'studio': 8, 'free': 3, 'enterprise': 3, 'basic': 3, 'business': 8, 'nope': 3})
        with mock.patch.dict(os.environ, {'OMNI_PLAN_REPAIR_BUDGET': '1'}):
            self.assertEqual(repair_rounds_for_plan(PlanCode.PRO), 5)


class EngineCeiling(unittest.TestCase):
    def engine(self, rounds, **kw):
        rep, ver = Repairer(), Verifier()
        e = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=rep, executor=ver,
                                    max_repair_rounds=rounds, **kw)
        e._summary = lambda repo, failures=(): {'files': []}
        return e, rep

    def test_default_ceiling_is_still_three(self):
        e, rep = self.engine(100)
        self.assertEqual(e.max_repair_rounds, 3)
        e.build('site')
        self.assertEqual(rep.calls, 3)

    def test_a_plan_ceiling_lets_a_studio_build_use_eight_rounds(self):
        e, rep = self.engine(repair_rounds_for_plan('studio', enabled=True), repair_ceiling=8)
        e.build('site')
        self.assertEqual((e.max_repair_rounds, rep.calls), (8, 8))

    def test_the_hard_maximum_is_enforced(self):
        self.assertEqual(REPAIR_ROUNDS_HARD_MAX, 8)
        for bad in (9, -1, True, 2.5):
            with self.assertRaises(ValueError):
                self.engine(3, repair_ceiling=bad)


if __name__ == '__main__':
    unittest.main()
