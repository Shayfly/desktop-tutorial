"""Customer-facing pricing and subscription responses never expose internal unit
economics (founder decision 2026-10-07 #29).

Closed world: a public plan may carry only PUBLIC_PLAN_FIELDS, and no key or
value anywhere in a customer response may look like provider cost, budget,
margin, subsidy, markup, credit valuation or the internal QA budget. Adding a
public field means adding it to the allowlist on purpose.
"""
import importlib.util
import re
import unittest

from omni_prod.pricing import PLAN_CATALOG, PUBLIC_PLAN_FIELDS, PlanCode, catalog_payload, customer_usage_view
from omni_prod.v28_platform import V28Platform

FORBIDDEN = re.compile(r"provider|margin|subsid|markup|valuation|budget|internal|qa_|cost_usd|expected_cost|"
                       r"hard_cost|cost_ceiling|spend", re.I)
CUSTOMER_USAGE_FIELDS = {"plan", "credits_used", "credits_remaining", "cycle"}


def _walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}", k
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def _assert_no_internal_keys(case, payload):
    leaked = [p for p, k in _walk(payload) if FORBIDDEN.search(str(k))]
    case.assertEqual(leaked, [], "internal economics field in a customer response")


def _assert_public_plan(case, plan):
    case.assertLessEqual(set(plan), set(PUBLIC_PLAN_FIELDS), sorted(set(plan) - set(PUBLIC_PLAN_FIELDS)))


def _assert_customer_usage(case, view):
    case.assertEqual(set(view), CUSTOMER_USAGE_FIELDS)
    _assert_public_plan(case, view["plan"])
    _assert_no_internal_keys(case, view)


class CatalogTests(unittest.TestCase):
    def test_public_catalog_has_only_customer_fields(self):
        payload = catalog_payload()
        self.assertEqual(len(payload["plans"]), 5)
        for plan in payload["plans"]:
            _assert_public_plan(self, plan)
        _assert_no_internal_keys(self, payload)

    def test_internal_values_do_not_appear_even_under_other_names(self):
        payload = repr(catalog_payload())
        for code in (PlanCode.BASIC, PlanCode.PRO, PlanCode.BUSINESS):
            plan = PLAN_CATALOG[code]
            self.assertNotIn(f"'{plan.paid_provider_budget_usd}'", payload)
            self.assertNotIn(f"'{plan.variable_margin_floor()}'", payload)

    def test_internal_view_still_holds_the_economics(self):
        full = PLAN_CATALOG[PlanCode.PRO].to_dict()
        self.assertIn("paid_provider_budget_usd", full)
        self.assertIn("variable_margin_floor", full)


class CustomerUsageTests(unittest.TestCase):
    def setUp(self):
        self.p = V28Platform(token_secret="x" * 48)
        self.reg = self.p.register(email="public-pricing@example.com", password="Passw0rd!Passw0rd")

    def test_registration_and_subscription_views(self):
        _assert_customer_usage(self, self.reg["subscription"])
        _assert_customer_usage(self, self.p.subscription(token=self.reg["token"]))

    def test_build_response_subscription_view(self):
        project = self.p.create_project(token=self.reg["token"], title="Pricing view")
        out = self.p.build(token=self.reg["token"], project_id=project["id"], prompt="Build a simple notes app",
                           target_markets=("US",))
        _assert_customer_usage(self, out["subscription"])

    def test_view_from_internal_snapshot(self):
        uid = self.reg["user"]["id"]
        internal = self.p.subscriptions.snapshot(uid)
        self.assertIn("provider_spend_usd", internal)          # kept internally
        _assert_customer_usage(self, customer_usage_view(internal))


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI not installed")
class HTTPTests(unittest.TestCase):
    def test_public_pricing_endpoint(self):
        from fastapi.testclient import TestClient
        from omni_prod.investor_app import app
        client = TestClient(app)
        r = client.get("/api/v28/pricing")
        self.assertEqual(r.status_code, 200)
        for plan in r.json()["plans"]:
            _assert_public_plan(self, plan)
        _assert_no_internal_keys(self, r.json())

    def test_registration_endpoint_subscription(self):
        import uuid
        from fastapi.testclient import TestClient
        from omni_prod.investor_app import app
        client = TestClient(app)
        r = client.post("/api/v28/auth/register",
                        json={"email": f"pp-{uuid.uuid4().hex[:10]}@example.com", "password": "Passw0rd!Passw0rd"})
        self.assertEqual(r.status_code, 200, r.text)
        _assert_customer_usage(self, r.json()["subscription"])


if __name__ == "__main__":
    unittest.main()
