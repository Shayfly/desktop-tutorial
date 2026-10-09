"""Internal QA / staging budget: explicit entitlement, capped, never in production,
and fully separate from the customer plan (founder decisions 2026-10-07 #23, #24)."""
import unittest
from decimal import Decimal

from omni_prod.qa_budget import QABudgetDenied, QABudgetPolicy, active_entitlement, authorize_qa_build

ENV = {"OMNI_ENV": "staging", "OMNI_QA_BUILD_MAX_USD": "0.50", "OMNI_QA_BUDGET_TOTAL_USD": "10"}


class _Cur:
    """Scripted cursor: fetchone() returns the queued rows in order."""

    def __init__(self, *rows):
        self.rows, self.calls = list(rows), []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


GRANT = ("ent_1", "2026-10-07 02:00:00+00")


class PolicyTests(unittest.TestCase):
    def test_enabled_only_in_staging(self):
        self.assertTrue(QABudgetPolicy.from_env(ENV).enabled)
        for env in ({**ENV, "OMNI_ENV": ""}, {**ENV, "OMNI_ENV": "development"}):
            p = QABudgetPolicy.from_env(env)
            self.assertFalse(p.enabled)
            self.assertIn("OMNI_ENV=staging", p.reason)

    def test_disabled_in_production_even_if_mislabelled(self):
        for env in ({**ENV, "OMNI_ENV": "production"}, {**ENV, "VERCEL_ENV": "production"}):
            self.assertFalse(QABudgetPolicy.from_env(env).enabled)

    def test_missing_or_invalid_caps_disable(self):
        for bad in ({"OMNI_QA_BUILD_MAX_USD": ""}, {"OMNI_QA_BUDGET_TOTAL_USD": "-1"},
                    {"OMNI_QA_BUDGET_TOTAL_USD": "abc"}, {"OMNI_QA_BUILD_MAX_USD": "30"}):
            self.assertFalse(QABudgetPolicy.from_env({**ENV, **bad}).enabled, bad)

    def test_no_email_based_membership_exists(self):
        p = QABudgetPolicy.from_env({**ENV, "OMNI_QA_ACCOUNT_EMAILS": "qa@example.com"})
        self.assertFalse(hasattr(p, "applies_to"))
        self.assertFalse(hasattr(p, "account_emails"))


class SinceNeedsEvidenceTests(unittest.TestCase):
    """Directive 2026-10-09 §15: no date filter without free-tier proof."""
    base = {"OMNI_ENV": "staging", "OMNI_QA_BUILD_MAX_USD": "0.50", "OMNI_QA_BUDGET_TOTAL_USD": "10",
            "OMNI_QA_BUDGET_SINCE": "2026-10-08T17:12:00Z"}

    def test_date_without_evidence_is_ignored_and_reported(self):
        p = QABudgetPolicy.from_env(self.base)
        self.assertTrue(p.enabled)
        self.assertIsNone(p.since)
        self.assertEqual(p.since_ignored, "2026-10-08T17:12:00Z")
        self.assertIn("ignored", p.reason)
        self.assertEqual(p.evidence()["qa_since_ignored_no_evidence"], "2026-10-08T17:12:00Z")

    def test_date_with_evidence_is_used(self):
        p = QABudgetPolicy.from_env({**self.base, "OMNI_QA_FREE_TIER_EVIDENCE": "billing export 2026-10-09"})
        self.assertEqual(p.since, "2026-10-08T17:12:00Z")
        self.assertIsNone(p.since_ignored)


class EntitlementLookupTests(unittest.TestCase):
    def test_lookup_by_account_id_and_scope(self):
        cur = _Cur(GRANT)
        self.assertEqual(active_entitlement(cur, QABudgetPolicy.from_env(ENV), "acc_1")["entitlement_id"], "ent_1")
        sql, params = cur.calls[0]
        self.assertIn("revoked_at IS NULL", sql)
        self.assertEqual(params, ("acc_1", "INTERNAL_QA", "staging"))

    def test_disabled_policy_never_queries(self):
        cur = _Cur(GRANT)
        self.assertIsNone(active_entitlement(cur, QABudgetPolicy.from_env({**ENV, "OMNI_ENV": "production"}), "acc_1"))
        self.assertEqual(cur.calls, [])


class AuthorizeTests(unittest.TestCase):
    def test_within_caps_returns_evidence(self):
        cur = _Cur(GRANT, (Decimal("3.00"),))
        ev = authorize_qa_build(cur, QABudgetPolicy.from_env(ENV), account_id="acc_1", max_cost_usd=Decimal("0.50"))
        self.assertEqual((ev["funding_source"], ev["entitlement"], ev["environment"]), ("internal_qa", "INTERNAL_QA", "staging"))
        self.assertEqual((ev["entitlement_id"], ev["qa_used_before_usd"]), ("ent_1", "3.00"))
        self.assertIn("pg_advisory_xact_lock", cur.calls[0][0])            # lock before reading the grant
        self.assertIn("internal_entitlements", cur.calls[1][0])
        total_sql = cur.calls[2][0]
        self.assertIn("funding_source = 'internal_qa'", total_sql)
        self.assertNotIn("creator_accounts", total_sql)                    # not tied to the customer track

    def test_per_build_cap_denies_before_any_query(self):
        cur = _Cur(GRANT, (Decimal("0"),))
        with self.assertRaises(QABudgetDenied):
            authorize_qa_build(cur, QABudgetPolicy.from_env(ENV), account_id="acc_1", max_cost_usd=Decimal("0.51"))
        self.assertEqual(cur.calls, [])

    def test_no_active_entitlement_denies(self):
        with self.assertRaisesRegex(QABudgetDenied, "no active INTERNAL_QA entitlement"):
            authorize_qa_build(_Cur(None, (Decimal("0"),)), QABudgetPolicy.from_env(ENV),
                               account_id="acc_1", max_cost_usd=Decimal("0.10"))

    def test_total_cap(self):
        with self.assertRaisesRegex(QABudgetDenied, "total budget exhausted"):
            authorize_qa_build(_Cur(GRANT, (Decimal("9.60"),)), QABudgetPolicy.from_env(ENV),
                               account_id="acc_1", max_cost_usd=Decimal("0.50"))

    def test_disabled_policy_denies(self):
        with self.assertRaises(QABudgetDenied):
            authorize_qa_build(_Cur(GRANT, (Decimal("0"),)), QABudgetPolicy.from_env({**ENV, "OMNI_ENV": "production"}),
                               account_id="acc_1", max_cost_usd=Decimal("0.10"))


def _service(pool=None):
    from omni_prod.subscription_store import PostgresSubscriptionService
    return PostgresSubscriptionService(pool=pool)


class _Pool:
    def __init__(self, cur):
        self.cur = cur

    def connection(self):
        pool = self

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def transaction(self): return self
            def cursor(self): return pool.cur
        return Conn()


class ReservationSeparationTests(unittest.TestCase):
    def test_internal_qa_reservation_never_touches_the_customer_plan(self):
        cur = _Cur()
        decision = _service().reserve(cur, build_id="bld_qa", user_id="u1", project_id="p", cost_class="standard",
                                      credits=60, estimated_provider_cost_usd=Decimal("0.40"), internal_qa=True)
        self.assertTrue(decision.allowed)
        self.assertEqual((decision.plan, decision.credits, decision.user_billable), ("internal_qa", 0, False))
        self.assertEqual(len(cur.calls), 1)
        sql, params = cur.calls[0]
        self.assertIn("INSERT INTO credit_reservations", sql)
        self.assertIn("funding_source", sql)
        self.assertEqual(params, ("bld_qa", "u1", "p", 0, Decimal("0.40"), "internal_qa"))
        self.assertFalse(any("creator_subscriptions" in s for s, _ in cur.calls))

    def test_free_plan_without_qa_is_still_refused(self):
        svc = _service()
        decision = svc.reserve(_Cur(("free", svc._cycle_now(), 0, Decimal("0"))), build_id="b", user_id="u",
                               project_id="p", cost_class="standard", credits=50,
                               estimated_provider_cost_usd=Decimal("0.40"))
        self.assertFalse(decision.allowed)

    def test_customer_reservation_sql_is_unchanged(self):
        svc = _service()
        cur = _Cur(("pro", svc._cycle_now(), 0, Decimal("0")))
        svc.reserve(cur, build_id="b", user_id="u", project_id="p", cost_class="standard", credits=1,
                    estimated_provider_cost_usd=Decimal("0.10"))
        insert = [s for s, _ in cur.calls if "INSERT INTO credit_reservations" in s][0]
        self.assertNotIn("funding_source", insert)   # works before migration 029 is applied

    def test_qa_settlement_below_estimate_does_not_refund_the_customer_plan(self):
        cur = _Cur(("u1", "RESERVED", Decimal("0.40"), "internal_qa"))
        result = _service(_Pool(cur)).settle(build_id="bld_qa", actual_provider_cost_usd=Decimal("0.10"))
        self.assertEqual(result["settled_provider_cost_usd"], Decimal("0.10"))
        self.assertFalse(any("creator_subscriptions" in s for s, _ in cur.calls))

    def test_qa_settlement_above_estimate_is_recorded_not_charged_to_the_plan(self):
        cur = _Cur(("u1", "RESERVED", Decimal("0.40"), "internal_qa"))
        result = _service(_Pool(cur)).settle(build_id="bld_qa", actual_provider_cost_usd=Decimal("0.45"))
        self.assertEqual(result["settled_provider_cost_usd"], Decimal("0.45"))   # counts against the QA cap
        self.assertFalse(any("creator_subscriptions" in s for s, _ in cur.calls))

    def test_qa_release_does_not_touch_the_customer_plan(self):
        cur = _Cur(("u1", "RESERVED", 0, Decimal("0.40"), "internal_qa"))
        _service(_Pool(cur)).release(build_id="bld_qa")
        self.assertTrue(any("SET status='RELEASED'" in s for s, _ in cur.calls))
        self.assertFalse(any("creator_subscriptions" in s for s, _ in cur.calls))

    def test_customer_release_still_restores_plan_counters(self):
        cur = _Cur(("u1", "RESERVED", 60, Decimal("0.40"), "customer_plan"))
        _service(_Pool(cur)).release(build_id="b")
        self.assertTrue(any("UPDATE creator_subscriptions" in s for s, _ in cur.calls))


if __name__ == "__main__":
    unittest.main()
