import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from omni_prod.idempotency import request_fingerprint, validate_key
from omni_prod.limits import Limit, check_limit
from omni_prod.model_router import ModelOption, RoutingPolicy, select_model
from omni_prod.rollback import DeploymentSnapshot, choose_rollback_target
from omni_prod.worker_health import WorkerHeartbeat, is_stale

class IdempotencyTests(unittest.TestCase):
    def test_fingerprint_stable_across_key_order(self):
        a = request_fingerprint({"x": 1, "y": 2})
        b = request_fingerprint({"y": 2, "x": 1})
        self.assertEqual(a, b)

    def test_bad_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_key("../bad")

class LimitTests(unittest.TestCase):
    def test_hard_cap(self):
        decision = check_limit(
            used=Decimal("90"),
            requested=Decimal("11"),
            limit=Limit("build_minutes", Decimal("100")),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.remaining_after, Decimal("0"))

class RouterTests(unittest.TestCase):
    def test_cheapest_model_above_quality_floor(self):
        options = [
            ModelOption("a", "strong", 95, 800, Decimal("4"), Decimal("12")),
            ModelOption("b", "fast", 80, 300, Decimal("1"), Decimal("3")),
            ModelOption("c", "weak", 50, 200, Decimal("0.2"), Decimal("0.5")),
        ]
        chosen = select_model(
            options,
            policy=RoutingPolicy(minimum_quality=75, prefer_cost=True),
            input_tokens=100_000,
            output_tokens=20_000,
        )
        self.assertEqual(chosen.model, "fast")

class RollbackTests(unittest.TestCase):
    def test_select_previous_deployment(self):
        history = [
            DeploymentSnapshot("d3","p","v3","b3","production","a3"),
            DeploymentSnapshot("d2","p","v2","b2","production","a2"),
            DeploymentSnapshot("d1","p","v1","b1","production","a1"),
        ]
        target = choose_rollback_target(history, current_deployment_id="d3")
        self.assertEqual(target.version_id, "v2")

class WorkerHealthTests(unittest.TestCase):
    def test_stale_worker(self):
        now = datetime.now(timezone.utc)
        hb = WorkerHeartbeat("w1", now - timedelta(seconds=61))
        self.assertTrue(is_stale(hb, now=now, max_age_seconds=60))

if __name__ == "__main__":
    unittest.main()
