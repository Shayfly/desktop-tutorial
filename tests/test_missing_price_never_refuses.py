"""The owner, 2026-11-26 10:20 UTC: "לא מחייב אם אין לנו את כל הנתונים זה לא אמור כרגע מבחינתנו לכשל בבניה, אבל לעדכן".

A provider that IS configured but has no price no longer refuses the build quote: the capability runs, its cost is
unknown by name (never 0), and the settlement leaves it out of the measured sum instead of settling the reservation.
What cannot run at all (a required capability with no provider) is still refused -- that is not a price question.
The founder's change requests get the safety bounds instead of the worker's $0.50 / 150 calls."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from types import SimpleNamespace

from omni_prod.build_cost_plan import CostQuoteUnknown, build_economics_quote, collect_build_cost_inputs
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.providers.image_provider import build_image_quote_resolver

ENV = {"OMNI_IMAGE_PROVIDER_NAME": "image-predictions", "OMNI_IMAGE_PROVIDER_BASE_URL": "https://images.example/v1",
       "OMNI_IMAGE_PROVIDER_API_KEY_REF": "env:IMAGE_KEY", "IMAGE_KEY": "img-secret-key",
       "OMNI_IMAGE_PROVIDER_MODEL": "acme/brand-image-model", "OMNI_IMAGE_PROVIDER_COMMERCIAL_USE": "true"}
PRICE = {"OMNI_IMAGE_PROVIDER_ESTIMATED_USD_PER_IMAGE": "0.003", "OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE": "0.01",
         "OMNI_IMAGE_PROVIDER_PRICE_SOURCE": "https://images.example/pricing#2026-10-01"}
REQ = CapabilityRequirement(id="cap-media-image-generate", key="media.image.generate", purpose="hero", required=True,
                            constraints={"prompt": "An original blue door"})


def _contract(*reqs):
    return SimpleNamespace(capability_plan=CapabilityPlan(requirements=tuple(reqs), target_keys=(), notes=()),
                           infrastructure=())


def _inputs(env, *reqs):
    contract = _contract(*reqs)
    return collect_build_cost_inputs(contract, capability_assignments=build_image_quote_resolver(env)(
        contract.capability_plan), infrastructure_quotes=(), require_capability_quotes=True,
        require_infrastructure_quotes=True)


class TheQuote(unittest.TestCase):
    def test_the_quote_no_longer_refuses_an_unpriced_capability(self):
        inputs = _inputs(ENV, REQ)                      # configured, no price: before 2026-11-26 a CostQuoteUnknown (402)
        self.assertEqual([k for _, k, _ in inputs.capability_quotes], ["media.image.generate"])
        self.assertEqual([(m["kind"], m["name"], m["gap"]) for m in inputs.price_missing],
                         [("capability", "media.image.generate", "price_missing")])
        quote, components = build_economics_quote(
            llm_quotes=(), cost_inputs=inputs, platform_infrastructure_estimated_usd=Decimal("0"),
            platform_infrastructure_maximum_usd=Decimal("0"), retry_reserve_usd=Decimal("0"), revenue_usd=None,
            minimum_margin=None)
        cap, = components["capabilities"]
        self.assertIsNone(cap["maximum_cost_usd"])     # unknown, never a 0 price
        self.assertFalse(cap["price_known"])
        self.assertEqual(components["cost_data_missing"][0]["name"], "media.image.generate")

    def test_a_priced_capability_is_unchanged(self):
        inputs = _inputs({**ENV, **PRICE}, REQ)
        self.assertEqual(inputs.price_missing, ())
        self.assertEqual(inputs.capability_maximum_usd, Decimal("0.01"))

    def test_a_required_capability_with_no_provider_is_still_refused(self):
        with self.assertRaises(CostQuoteUnknown):       # it cannot run at all: not a price question
            _inputs({}, REQ)


class TheSettlement(unittest.TestCase):
    def test_a_capability_without_a_number_is_named_not_settled_at_the_reservation(self):
        from omni_prod.worker_tasks import computed_provider_cost
        usage = [{"requirement_id": "cap-1", "provider": "replicate", "pricing_version": "unpriced:operator-config",
                  "estimated_cost_usd": Decimal("0"), "maximum_cost_usd": Decimal("0"), "actual_cost_usd": None}]
        total, basis = computed_provider_cost(llm_actual=Decimal("0.40"), gateway_spend=Decimal("0.40"), prior=None,
                                              capability_evidence={"usage": usage}, infra_max=Decimal("0"))
        self.assertEqual(total, Decimal("0.40"))        # the measured part; the image is not $0, it is named
        self.assertEqual(basis["cost_data_missing"], ["capability:cap-1"])
        self.assertNotIn("missing", basis)

    def test_an_unknown_earlier_call_without_exposure_still_settles_at_the_reservation(self):
        from omni_prod.worker_tasks import computed_provider_cost
        total, basis = computed_provider_cost(llm_actual=None, gateway_spend=Decimal("0.1"),
                                              prior={"metered_usd": 0, "unknown_calls": 1, "unknown_exposure_usd": 0},
                                              capability_evidence=None, infra_max=Decimal("0"))
        self.assertIsNone(total)
        self.assertEqual(basis["missing"], ["earlier_worker_unknown_call_without_exposure"])


class TheFoundersChangeRequests(unittest.TestCase):
    def _gw(self):
        from omni_prod.model_catalog import parse_model_catalog
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.routed_gateway import RoutedModelGateway
        cat = parse_model_catalog(json.dumps([{"name": "m", "provider": "p", "base_url": "https://a.example/v1",
                                               "model": "m", "api_key_env": "K1X", "quality": 90,
                                               "input_per_million": "1", "output_per_million": "2"}]), {"K1X": "k"})
        return RoutedModelGateway(ranked=cat, policy=ModelUsePolicy(
            zero_cost_mode=False, allow_external_fallback=True, external_budget_usd=Decimal("0.50"),
            max_external_calls_per_build=150), gateway_factory=lambda e: None)

    def test_the_founder_gets_the_safety_bounds_and_others_keep_the_worker_values(self):
        from omni_prod.worker_tasks import bind_founder_change_request
        gw = self._gw()
        ev = bind_founder_change_request(gw, {"user_id": "usr_GCWlMxENgr9vpwph"})
        self.assertEqual((gw.policy.external_budget_usd, gw.policy.max_external_calls_per_build), (Decimal("25"), 400))
        self.assertEqual((ev["worker_env_budget_usd"], ev["worker_env_calls_per_build"]), ("0.50", 150))
        other = self._gw()
        self.assertIsNone(bind_founder_change_request(other, {"user_id": "usr_other"}))
        self.assertEqual((other.policy.external_budget_usd, other.policy.max_external_calls_per_build),
                         (Decimal("0.50"), 150))

    def test_the_rule_can_be_turned_off(self):
        import os
        from unittest import mock
        from omni_prod.worker_tasks import bind_founder_change_request
        with mock.patch.dict(os.environ, {"OMNI_FOUNDER_NO_BUILD_LIMIT": "0"}):
            gw = self._gw()
            self.assertIsNone(bind_founder_change_request(gw, {"user_id": "usr_GCWlMxENgr9vpwph"}))
            self.assertEqual(gw.policy.external_budget_usd, Decimal("0.50"))


if __name__ == "__main__":
    unittest.main()
