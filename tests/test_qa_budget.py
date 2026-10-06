"""Internal QA / staging budget: explicit, capped, never in production."""
import unittest
from decimal import Decimal

from omni_prod.qa_budget import QABudgetDenied, QABudgetPolicy, authorize_qa_build

ENV = {"OMNI_QA_ACCOUNT_EMAILS": "QA@Example.com, ops@example.com",
       "OMNI_QA_BUILD_MAX_USD": "0.50", "OMNI_QA_BUDGET_TOTAL_USD": "20"}


class _Cur:
    def __init__(self, used):
        self.used, self.calls = used, []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return (self.used,)


class PolicyTests(unittest.TestCase):
    def test_enabled_and_case_insensitive_membership(self):
        p = QABudgetPolicy.from_env(ENV)
        self.assertTrue(p.enabled)
        self.assertTrue(p.applies_to("qa@example.com"))
        self.assertFalse(p.applies_to("customer@example.com"))
        self.assertFalse(p.applies_to(None))

    def test_disabled_in_production(self):
        for extra in ({"OMNI_ENV": "production"}, {"VERCEL_ENV": "production"}):
            p = QABudgetPolicy.from_env({**ENV, **extra})
            self.assertFalse(p.enabled)
            self.assertFalse(p.applies_to("qa@example.com"))

    def test_missing_or_invalid_caps_disable(self):
        for bad in ({"OMNI_QA_BUILD_MAX_USD": ""}, {"OMNI_QA_BUDGET_TOTAL_USD": "-1"},
                    {"OMNI_QA_BUDGET_TOTAL_USD": "abc"}, {"OMNI_QA_BUILD_MAX_USD": "30"}):
            self.assertFalse(QABudgetPolicy.from_env({**ENV, **bad}).enabled, bad)

    def test_no_accounts_disables(self):
        self.assertFalse(QABudgetPolicy.from_env({**ENV, "OMNI_QA_ACCOUNT_EMAILS": " , "}).enabled)


class AuthorizeTests(unittest.TestCase):
    def test_within_caps_returns_evidence_and_locks(self):
        cur = _Cur(Decimal("3.00"))
        ev = authorize_qa_build(cur, QABudgetPolicy.from_env(ENV), max_cost_usd=Decimal("0.50"))
        self.assertEqual(ev["funding_source"], "internal_qa")
        self.assertEqual(ev["qa_used_before_usd"], "3.00")
        self.assertIn("pg_advisory_xact_lock", cur.calls[0][0])
        self.assertEqual(cur.calls[1][1], (["ops@example.com", "qa@example.com"],))

    def test_per_build_cap(self):
        with self.assertRaises(QABudgetDenied):
            authorize_qa_build(_Cur(0), QABudgetPolicy.from_env(ENV), max_cost_usd=Decimal("0.51"))

    def test_total_cap(self):
        with self.assertRaises(QABudgetDenied):
            authorize_qa_build(_Cur(Decimal("19.60")), QABudgetPolicy.from_env(ENV), max_cost_usd=Decimal("0.50"))

    def test_disabled_policy_denies(self):
        with self.assertRaises(QABudgetDenied):
            authorize_qa_build(_Cur(0), QABudgetPolicy.from_env({**ENV, "OMNI_ENV": "production"}),
                               max_cost_usd=Decimal("0.10"))


class ReserveQATests(unittest.TestCase):
    def test_internal_qa_reservation_skips_plan_limits_and_charges_no_credits(self):
        from omni_prod.subscription_store import PostgresSubscriptionService

        svc = PostgresSubscriptionService.__new__(PostgresSubscriptionService)

        class Cur:
            def __init__(self):
                self.sql = []
                self.rowcount = 1

            def execute(self, sql, params=None):
                self.sql.append((sql, params))

            def fetchone(self):
                return ("free", svc._cycle_now(), 0, Decimal("0"))

        cur = Cur()
        decision = svc.reserve(cur, build_id="bld_qa", user_id="u1", project_id="p", cost_class="standard",
                               credits=50, estimated_provider_cost_usd=Decimal("0.40"), internal_qa=True)
        self.assertTrue(decision.allowed)
        insert = [p for s, p in cur.sql if "INSERT INTO credit_reservations" in s][0]
        self.assertEqual(insert[3], 0)                    # no plan credits charged
        self.assertEqual(insert[4], Decimal("0.40"))      # maximum authorized cost recorded
        self.assertFalse(any("UPDATE creator_subscriptions SET credits_used" in s for s, _ in cur.sql))

    def test_free_plan_without_qa_is_still_refused(self):
        from omni_prod.subscription_store import PostgresSubscriptionService
        svc = PostgresSubscriptionService.__new__(PostgresSubscriptionService)

        class Cur:
            rowcount = 1
            def execute(self, sql, params=None): pass
            def fetchone(self): return ("free", svc._cycle_now(), 0, Decimal("0"))

        decision = svc.reserve(Cur(), build_id="b", user_id="u", project_id="p", cost_class="standard",
                               credits=50, estimated_provider_cost_usd=Decimal("0.40"))
        self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()
