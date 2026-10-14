"""Plan view and build admission take the same internal-QA funding decision.

Live evidence 2026-10-07 (STATUS.md): on Preview, a founder account with an
active INTERNAL_QA grant saw the plan priced as the free customer plan
(`build_authorization=NOT_AUTHORIZED`, approve button disabled), while build
admission would have funded the same build from the QA budget.
"""
import ast
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.qa_budget import (QABudgetDenied, QABudgetPolicy, entitled_account, preauthorize_qa_build)

ROOT = Path(__file__).resolve().parents[1]
ENV = {"OMNI_ENV": "staging", "OMNI_QA_BUILD_MAX_USD": "0.50", "OMNI_QA_BUDGET_TOTAL_USD": "10"}
GRANT = ("ent_1", "2026-10-07 14:00:00+00")


class _Cur:
    def __init__(self, *rows):
        self.rows, self.calls = list(rows), []

    def execute(self, sql, params=None):
        self.calls.append(" ".join(sql.split()))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Pool:
    def __init__(self, cur):
        self.cur, self.transactions, self.connections = cur, 0, 0

    def connection(self):
        pool = self
        pool.connections += 1

        class Tx:
            def __enter__(self):
                pool.transactions += 1
                return self

            def __exit__(self, *a):
                return False

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def transaction(self): return Tx()
            def cursor(self): return pool.cur
        return Conn()


class EntitledAccountTests(unittest.TestCase):
    def test_active_grant(self):
        self.assertTrue(entitled_account(_Pool(_Cur(GRANT)), QABudgetPolicy.from_env(ENV), "acc_1"))

    def test_no_grant(self):
        self.assertFalse(entitled_account(_Pool(_Cur()), QABudgetPolicy.from_env(ENV), "acc_1"))

    def test_disabled_policy_never_touches_the_store(self):
        pool = _Pool(_Cur(GRANT))
        for env in ({**ENV, "OMNI_ENV": "production"}, {**ENV, "OMNI_ENV": ""}, {**ENV, "OMNI_QA_BUILD_MAX_USD": ""}):
            self.assertFalse(entitled_account(pool, QABudgetPolicy.from_env(env), "acc_1"), env)
        self.assertEqual(pool.connections, 0)

    def test_no_pool_or_account(self):
        self.assertFalse(entitled_account(None, QABudgetPolicy.from_env(ENV), "acc_1"))
        self.assertFalse(entitled_account(_Pool(_Cur(GRANT)), QABudgetPolicy.from_env(ENV), ""))


class PreauthorizeTests(unittest.TestCase):
    def test_same_checks_as_admission_inside_a_transaction(self):
        pool = _Pool(_Cur(GRANT, (Decimal("3"),)))
        ev = preauthorize_qa_build(pool, QABudgetPolicy.from_env(ENV), account_id="acc_1", max_cost_usd=Decimal("0.50"))
        self.assertEqual(ev["funding_source"], "internal_qa")
        self.assertEqual(pool.transactions, 1)
        self.assertTrue(any("pg_advisory_xact_lock" in c for c in pool.cur.calls))
        self.assertFalse(any(c.split()[0].upper() in {"INSERT", "UPDATE", "DELETE"} for c in pool.cur.calls))

    def test_refuses_over_per_build_cap(self):
        with self.assertRaises(QABudgetDenied):
            preauthorize_qa_build(_Pool(_Cur(GRANT, (Decimal("0"),))), QABudgetPolicy.from_env(ENV),
                                  account_id="acc_1", max_cost_usd=Decimal("0.51"))

    def test_refuses_when_total_exhausted(self):
        with self.assertRaises(QABudgetDenied):
            preauthorize_qa_build(_Pool(_Cur(GRANT, (Decimal("9.80"),))), QABudgetPolicy.from_env(ENV),
                                  account_id="acc_1", max_cost_usd=Decimal("0.50"))

    def test_refuses_without_grant(self):
        with self.assertRaises(QABudgetDenied):
            preauthorize_qa_build(_Pool(_Cur()), QABudgetPolicy.from_env(ENV), account_id="acc_1",
                                  max_cost_usd=Decimal("0.10"))


class EndpointParityTests(unittest.TestCase):
    """investor_app needs FastAPI (CI only), so parity is checked on the source."""

    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / "omni_prod/investor_app.py").read_text())
        cls.funcs = {n.name: ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    def test_both_endpoints_use_the_shared_decision(self):
        for name in ("v28_build_contract_preview", "v28_build_async"):
            self.assertIn("_internal_qa_funding(account.id)", self.funcs[name], name)
            self.assertNotIn("active_entitlement(", self.funcs[name], name)

    def test_plan_view_quotes_with_qa_funding_and_checks_qa_caps(self):
        plan = self.funcs["v28_build_contract_preview"]
        self.assertIn("funding='internal_qa' if internal_qa else None", plan)
        self.assertIn("preauthorize_qa_build(", plan)

    def test_plan_exposes_prototype_remaining_from_same_spend_ledger(self):
        plan = self.funcs["v28_build_contract_preview"]
        self.assertIn("prototype_qa_budget", plan)
        self.assertIn("qa_used_usd", plan)
        # It remains display-only; the actual lock occurs during admission.
        self.assertIn("preauthorize_qa_build(", plan)

    def test_admission_still_authorizes_under_lock(self):
        self.assertIn("authorize_qa_build(cur, qa_policy", self.funcs["v28_build_async"])


if __name__ == "__main__":
    unittest.main()
