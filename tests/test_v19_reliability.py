import unittest
from omni_prod.circuit_breaker import (
    CircuitBreaker, CircuitPolicy, CircuitState
)
from omni_prod.dead_letter import decide_dead_letter
from omni_prod.outbox import deterministic_dedupe_key, new_event
from omni_prod.worker_lease import Lease, can_claim, renew
from omni_prod.recovery_simulation import run_recovery_simulation

class CircuitTests(unittest.TestCase):
    def test_open_half_open_recover(self):
        c = CircuitBreaker(CircuitPolicy(2, 10))
        self.assertTrue(c.allow(0))
        c.failure(0)
        self.assertTrue(c.allow(1))
        c.failure(1)
        self.assertEqual(c.state, CircuitState.OPEN)
        self.assertFalse(c.allow(5))
        self.assertTrue(c.allow(12))
        self.assertEqual(c.state, CircuitState.HALF_OPEN)
        c.success()
        self.assertEqual(c.state, CircuitState.CLOSED)

    def test_half_open_allows_single_probe(self):
        c = CircuitBreaker(CircuitPolicy(1, 1))
        c.failure(0)
        self.assertTrue(c.allow(2))
        self.assertFalse(c.allow(2.1))

class OutboxTests(unittest.TestCase):
    def test_dedupe_is_deterministic(self):
        a = deterministic_dedupe_key(
            topic="x", aggregate_id="1", payload={"a":1, "b":2}
        )
        b = deterministic_dedupe_key(
            topic="x", aggregate_id="1", payload={"b":2, "a":1}
        )
        self.assertEqual(a, b)

    def test_new_event_unique_id_same_dedupe(self):
        a = new_event(topic="x", aggregate_id="1", payload={"a":1})
        b = new_event(topic="x", aggregate_id="1", payload={"a":1})
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(a.dedupe_key, b.dedupe_key)

class LeaseTests(unittest.TestCase):
    def test_expired_lease_can_be_reclaimed(self):
        l = Lease("w1", 10)
        self.assertFalse(can_claim(l, now=9, owner="w2"))
        self.assertTrue(can_claim(l, now=10, owner="w2"))

    def test_renew(self):
        self.assertEqual(
            renew(owner="w", now=5, ttl_seconds=10).expires_at, 15
        )

class DeadLetterTests(unittest.TestCase):
    def test_attempt_exhaustion(self):
        self.assertEqual(
            decide_dead_letter(
                attempts=3, max_attempts=3, retryable=True
            ).reason,
            "attempts_exhausted"
        )

    def test_nonretryable_goes_deadletter(self):
        self.assertTrue(
            decide_dead_letter(
                attempts=0, max_attempts=3, retryable=False
            ).dead_letter
        )

class SimulationTests(unittest.TestCase):
    def test_recovery_simulation(self):
        self.assertEqual(run_recovery_simulation()["circuit"], "closed")

if __name__ == "__main__":
    unittest.main()
