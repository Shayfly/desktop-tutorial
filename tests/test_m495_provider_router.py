import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityRequirement
from omni_prod.provider_contracts import ProviderCapability, ProviderQuote
from omni_prod.provider_registry import ProviderRegistry
from omni_prod.provider_router import (
    CapabilityProviderRouter,
    CapabilityRoutingPolicy,
    ProviderCandidate,
    ProviderQuotaCircuitManager,
    parse_retry_after_seconds,
)
from omni_prod.redis_circuit_breaker import RedisCircuitPolicy


class FakeProvider:
    def __init__(self, name, capability="media.image.generate"):
        self.name = name
        self._capability = capability
    def capabilities(self): return (ProviderCapability(self._capability, ("image/png",), True),)
    def health(self): return "HEALTHY"
    def quote(self, requirement): raise AssertionError("router selection must not call provider.quote")
    def submit(self, requirement, *, idempotency_key): raise NotImplementedError
    def poll(self, handle): raise NotImplementedError
    def collect(self, handle): raise NotImplementedError
    def cancel(self, handle): return None


class FakePipe:
    def __init__(self, redis): self.redis = redis
    def hset(self, *args, **kwargs): self.redis.hset(*args, **kwargs); return self
    def delete(self, *args, **kwargs): self.redis.delete(*args, **kwargs); return self
    def execute(self): return []


class FakeRedis:
    def __init__(self): self.h = {}; self.kv = {}
    def hgetall(self, key): return dict(self.h.get(key, {}))
    def hincrby(self, key, field, amount):
        d = self.h.setdefault(key, {})
        field = field.encode() if isinstance(field, str) else field
        value = int(d.get(field, 0)) + amount
        d[field] = value
        return value
    def hset(self, key, mapping):
        d = self.h.setdefault(key, {})
        for k, v in mapping.items():
            k = k.encode() if isinstance(k, str) else k
            d[k] = v.encode() if isinstance(v, str) else v
    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.kv: return False
        self.kv[key] = value
        return True
    def delete(self, key): self.kv.pop(key, None)
    def pipeline(self): return FakePipe(self)


def candidate(
    provider,
    *,
    cost="1.00",
    quality=90,
    latency=100,
    health="HEALTHY",
    formats=("image/png",),
    commercial=True,
):
    quote = ProviderQuote(
        provider=provider,
        capability_key="media.image.generate",
        estimated_cost_usd=Decimal(cost) / 2,
        maximum_cost_usd=Decimal(cost),
        pricing_version="2026-10-04",
        unit_name="image",
        units=Decimal("1"),
    )
    return ProviderCandidate(provider, quality, latency, quote, health, formats, commercial)


class ProviderRegistryTests(unittest.TestCase):
    def test_duplicate_provider_name_fails(self):
        registry = ProviderRegistry()
        registry.register(FakeProvider("same"))
        with self.assertRaisesRegex(ValueError, "duplicate provider"):
            registry.register(FakeProvider("same"))

    def test_lookup_by_capability_is_stable(self):
        registry = ProviderRegistry()
        registry.register(FakeProvider("zeta"))
        registry.register(FakeProvider("alpha"))
        self.assertEqual(
            tuple(p.name for p in registry.providers_for("media.image.generate")),
            ("alpha", "zeta"),
        )


class ProviderRouterTests(unittest.TestCase):
    def setUp(self):
        self.req = CapabilityRequirement("r1", "media.image.generate", "hero", True)
        self.router = CapabilityProviderRouter()

    def test_lowest_conservative_cost_wins_then_quality_latency_name(self):
        selection = self.router.select(
            requirement=self.req,
            candidates=(candidate("z", cost="1", quality=99), candidate("a", cost="1", quality=99)),
            policy=CapabilityRoutingPolicy(minimum_quality=80),
        )
        self.assertEqual(selection.candidate.provider, "a")

    def test_hard_filters_cover_health_cost_quality_latency_format_rights_and_lists(self):
        candidates = (
            candidate("failed", health="FAILED"),
            candidate("expensive", cost="5"),
            candidate("lowq", quality=20),
            candidate("slow", latency=5000),
            candidate("wrongformat", formats=("image/jpeg",)),
            candidate("norights", commercial=False),
            candidate("denied"),
            candidate("ok", cost="0.8", quality=95, latency=80),
        )
        selection = self.router.select(
            requirement=self.req,
            candidates=candidates,
            policy=CapabilityRoutingPolicy(
                minimum_quality=80,
                maximum_cost_usd=Decimal("1"),
                maximum_latency_ms=500,
                required_formats=("image/png",),
                require_commercial_use=True,
                denied_providers=("denied",),
            ),
        )
        self.assertEqual(selection.candidate.provider, "ok")
        rejected = {item["provider"]: item["reason"] for item in selection.rejected}
        self.assertIn("health", rejected["failed"])
        self.assertIn("cost", rejected["expensive"])
        self.assertIn("quality", rejected["lowq"])
        self.assertIn("latency", rejected["slow"])
        self.assertIn("format", rejected["wrongformat"])
        self.assertIn("commercial", rejected["norights"])
        self.assertIn("denied", rejected["denied"])

    def test_allowed_provider_list_is_hard_constraint(self):
        selection = self.router.select(
            requirement=self.req,
            candidates=(candidate("a"), candidate("b", cost="0.1")),
            policy=CapabilityRoutingPolicy(allowed_providers=("a",)),
        )
        self.assertEqual(selection.candidate.provider, "a")

    def test_no_candidates_fails_explicitly(self):
        with self.assertRaisesRegex(LookupError, "no eligible provider"):
            self.router.select(
                requirement=self.req,
                candidates=(candidate("p", health="RATE_LIMITED"),),
                policy=CapabilityRoutingPolicy(),
            )

    def test_router_rejects_quote_for_wrong_capability_or_provider(self):
        wrong = candidate("p")
        object.__setattr__(wrong.quote, "capability_key", "media.video.generate")
        with self.assertRaisesRegex(ValueError, "quote capability"):
            self.router.select(requirement=self.req, candidates=(wrong,), policy=CapabilityRoutingPolicy())


class ProviderQuotaCircuitTests(unittest.TestCase):
    def test_retry_after_parser_supports_seconds_and_rejects_bad_values(self):
        self.assertEqual(parse_retry_after_seconds("17"), 17)
        self.assertIsNone(parse_retry_after_seconds("nonsense"))
        self.assertIsNone(parse_retry_after_seconds(None))

    def test_429_opens_provider_capability_specific_distributed_cooldown(self):
        redis = FakeRedis()
        manager = ProviderQuotaCircuitManager(
            redis,
            circuit_policy=RedisCircuitPolicy(failure_threshold=3, recovery_seconds=10),
            default_rate_limit_seconds=30,
        )
        manager.record_http_result(
            provider="meshy",
            capability_key="media.3d.mesh.generate",
            status_code=429,
            headers={"Retry-After": "120"},
            error_code="rate_limit",
            now=1000,
        )
        self.assertFalse(manager.allow("meshy", "media.3d.mesh.generate", now=1119))
        self.assertTrue(manager.allow("meshy", "media.3d.mesh.generate", now=1120))
        # Other capability/provider circuit is independent.
        self.assertTrue(manager.allow("meshy", "media.image.generate", now=1001))
        self.assertTrue(manager.allow("other", "media.3d.mesh.generate", now=1001))

    def test_quota_exhaustion_uses_longer_cooldown_without_global_outage(self):
        redis = FakeRedis()
        manager = ProviderQuotaCircuitManager(
            redis,
            circuit_policy=RedisCircuitPolicy(failure_threshold=3, recovery_seconds=10),
            default_quota_seconds=3600,
        )
        manager.record_http_result(
            provider="runway",
            capability_key="media.video.generate",
            status_code=402,
            headers={},
            error_code="quota_exhausted",
            now=10,
        )
        self.assertFalse(manager.allow("runway", "media.video.generate", now=3000))
        self.assertTrue(manager.allow("runway", "media.video.generate", now=3610))

    def test_success_resets_provider_specific_breaker(self):
        redis = FakeRedis()
        manager = ProviderQuotaCircuitManager(redis)
        manager.record_http_result(
            provider="p", capability_key="media.image.generate", status_code=500,
            headers={}, error_code="server_error", now=0,
        )
        manager.record_http_result(
            provider="p", capability_key="media.image.generate", status_code=200,
            headers={}, error_code=None, now=1,
        )
        self.assertTrue(manager.allow("p", "media.image.generate", now=2))


if __name__ == "__main__":
    unittest.main()
