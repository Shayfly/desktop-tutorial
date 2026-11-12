"""Attempt Ledger: per-attempt routing evidence, versions and cost truth layers."""
import json
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.attempt_ledger import (
    AttemptRecord, AttemptRecorder, RecordingExecutor, TaskTaggedGateway, _COLUMNS,
    classify_execution, content_version, ledger_rows, persist_attempts)
from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.provider_usage import ProviderUsage
from omni_prod.routed_gateway import RoutedModelGateway

ROOT = Path(__file__).resolve().parents[1]
CATALOG = [
    {"name": "cheap", "provider": "p1", "base_url": "https://a.example/v1", "model": "m-cheap",
     "api_key_env": "KEY_ONE", "quality": 80, "input_per_million": "1", "output_per_million": "2"},
    {"name": "strong", "provider": "p2", "base_url": "https://b.example/v1", "model": "m-strong",
     "api_key_env": "KEY_TWO", "quality": 95, "input_per_million": "10", "output_per_million": "20"},
]
POLICY = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                        external_budget_usd=Decimal("5"), max_external_calls_per_build=50)



def setUpModule():
    # These tests check ledger counting with a cheap/strong catalog under
    # cost-first routing. Task quality floors (codegen/repair prefer the
    # stronger model, 2026-10-08) are covered in test_task_quality_routing.
    import os
    from unittest import mock
    global _ENV_PATCH
    _ENV_PATCH = mock.patch.dict(os.environ, {'OMNI_MODEL_TASK_MIN_QUALITY': '{"codegen": 0, "repair": 0, "modification": 0}'})
    _ENV_PATCH.start()


def tearDownModule():
    _ENV_PATCH.stop()

class _Fake:
    behaviour = {}

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.last_usage = None
        self.last_response_model = None

    def complete(self, **kw):
        mode = _Fake.behaviour.get(self.endpoint.name, "ok")
        if mode == "timeout":
            raise ModelGatewayError("model request failed") from TimeoutError("timed out")
        if mode == "error":
            self.last_usage = None
            raise ModelGatewayError("model request failed: 500")
        self.last_response_model = self.endpoint.model + "-2026-09"
        self.last_usage = ProviderUsage(
            provider=self.endpoint.name, model=self.endpoint.model, external=True, request_id="req-" + self.endpoint.name,
            request_id_source="header", response_id=None, input_tokens=1000, output_tokens=500, cached_tokens=None,
            provider_reported_cost_usd=Decimal("0.0019"), usage_reported=True)
        return "ok"

    def complete_json(self, **kw):
        return {"v": self.complete(**kw)}


def _gw():
    _Fake.behaviour = {}
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {"KEY_ONE": "secret-a", "KEY_TWO": "secret-b"}),
                              routing_policy=RoutingPolicy(minimum_quality=70), policy=POLICY,
                              gateway_factory=_Fake)


class GatewayAttemptTests(unittest.TestCase):
    def test_task_tag_versions_and_cost_layers(self):
        gw = _gw()
        # Wave A: 'architecture' now prefers the quality-85 model (task_policy);
        # this test is about the ledger record, so it uses a cheap task class.
        TaskTaggedGateway(gw, "classification").complete(system="SYS", user="u", max_tokens=600)
        (r,) = gw.recorder.records
        self.assertEqual((r.task_type, r.kind, r.outcome, r.provider, r.model), ("classification", "provider_call", "ok", "cheap", "m-cheap"))
        self.assertEqual(r.model_version, "m-cheap-2026-09")
        self.assertEqual(r.provider_request_id, "req-cheap")
        self.assertEqual(r.fallback_rank, 0)
        self.assertEqual([c["name"] for c in r.candidate_set], ["cheap", "strong"])
        self.assertIn("cheapest", r.selection_reason)
        for v in (r.policy_version, r.routing_policy_version, r.prompt_version, r.price_catalog_version):
            self.assertRegex(v, r"^[0-9a-f]{12}$")
        # three cost layers, never merged
        self.assertGreater(r.authorized_cost_usd, 0)
        self.assertEqual(r.metered_cost_usd, (Decimal(1000) * 1 + Decimal(500) * 2) / Decimal(1_000_000))
        self.assertEqual(r.provider_reported_cost_usd, Decimal("0.0019"))
        self.assertIsNone(r.expected_cost_usd)

    def test_prompt_version_tracks_prompt_text(self):
        gw = _gw()
        gw.complete(system="A", user="u")
        gw.complete(system="B", user="u")
        a, b = gw.recorder.records
        self.assertNotEqual(a.prompt_version, b.prompt_version)

    def test_timeout_is_unknown_and_fallback_is_recorded(self):
        gw = _gw()
        _Fake.behaviour = {"cheap": "timeout"}
        gw.complete(system="s", user="u", max_tokens=100)
        first, second = gw.recorder.records
        self.assertEqual((first.outcome, first.fallback_rank), ("unknown", 0))
        self.assertIsNone(first.metered_cost_usd)
        self.assertEqual((second.outcome, second.fallback_rank, second.provider), ("ok", 1, "strong"))
        # an unknown outcome still counts its full authorized cost against the budget
        self.assertEqual(gw.state.external_spend_usd, first.authorized_cost_usd + second.authorized_cost_usd)

    def test_plain_error_is_error(self):
        gw = _gw()
        _Fake.behaviour = {"cheap": "error"}
        gw.complete(system="s", user="u")
        self.assertEqual(gw.recorder.records[0].outcome, "error")

    def test_tagged_wrapper_passes_through_to_untagged_gateway(self):
        class Plain:
            def complete(self, **kw):
                assert "task" not in kw
                return "x"
        self.assertEqual(TaskTaggedGateway(Plain(), "codegen").complete(system="s", user="u"), "x")


class CounterTests(unittest.TestCase):
    def test_build_counters_per_attempt(self):
        gw = _gw()
        TaskTaggedGateway(gw, "architecture").complete(system="s", user="u")
        TaskTaggedGateway(gw, "codegen").complete(system="s", user="u")
        _Fake.behaviour = {"cheap": "timeout"}           # repair #1 falls back to the second candidate
        TaskTaggedGateway(gw, "repair").complete(system="s", user="u")
        _Fake.behaviour = {}
        TaskTaggedGateway(gw, "repair").complete(system="s", user="u")
        TaskTaggedGateway(gw, "codegen").complete(system="s", user="u")   # a regeneration
        rows = [(r.task_type, r.retry_count, r.repair_count, r.regenerate_count, r.fallback_count, r.escalation_count)
                for r in gw.recorder.records]
        self.assertEqual(rows, [
            ("architecture", 0, 0, 0, 0, 0),
            ("codegen", 0, 0, 0, 0, 0),
            ("repair", 0, 1, 0, 0, 0),      # first try timed out
            ("repair", 1, 1, 0, 1, 0),      # same logical call, retried on fallback
            ("repair", 0, 2, 0, 1, 0),
            ("codegen", 0, 2, 1, 1, 0),
        ])
        summary = gw.recorder.summary()
        self.assertEqual((summary["repairs"], summary["regenerations"], summary["escalations"]), (2, 1, 0))

    def test_verification_attempts_carry_counters(self):
        rec = AttemptRecorder()
        rec.add(AttemptRecord(task_type="repair", attempt_seq=0, kind="provider_call", outcome="ok", fallback_rank=0))
        v = rec.add(AttemptRecord(task_type="verification", attempt_seq=1, kind="verification", outcome="ok",
                                  verification_class="PASS"))
        self.assertEqual((v.retry_count, v.repair_count, v.escalation_count), (0, 1, 0))


class VerificationRecordingTests(unittest.TestCase):
    def test_classes(self):
        class Rep:
            def __init__(self, passed, failures=()):
                self.passed, self.failures = passed, list(failures)

        class F:
            acceptance_id, message = "A1", "boom"

        class Exec:
            def __init__(self, outcomes):
                self.outcomes = list(outcomes)

            def execute(self, *, repository, spec):
                o = self.outcomes.pop(0)
                if isinstance(o, Exception):
                    raise o
                return o

        rec = AttemptRecorder()
        ex = RecordingExecutor(Exec([Rep(True), Rep(False, [F()]), RuntimeError("sandbox down")]), rec)
        ex.execute(repository={}, spec=None)
        ex.execute(repository={}, spec=None)
        with self.assertRaises(RuntimeError):
            ex.execute(repository={}, spec=None)
        self.assertEqual([r.verification_class for r in rec.records], ["PASS", "REPAIRABLE_FAIL", "RETRYABLE_FAIL"])
        self.assertIn("A1: boom", rec.records[1].failure_reason)
        self.assertEqual(rec.records[2].outcome, "error")
        self.assertEqual([r.attempt_seq for r in rec.records], [0, 1, 2])

    def test_classify_execution(self):
        self.assertEqual(classify_execution(error=TimeoutError()), "RETRYABLE_FAIL")

    def test_invalid_values_rejected(self):
        with self.assertRaises(ValueError):
            AttemptRecord(task_type="x", attempt_seq=0, kind="provider_call", outcome="maybe")
        with self.assertRaises(ValueError):
            AttemptRecord(task_type="x", attempt_seq=0, kind="verification", outcome="ok", verification_class="GOOD")


class PersistenceTests(unittest.TestCase):
    def test_rows_match_migration_columns(self):
        sql = (ROOT / "infra/postgres/027_task_attempts.sql").read_text()
        sql += (ROOT / "infra/postgres/028_task_attempt_counters.sql").read_text()
        for column in _COLUMNS:
            self.assertRegex(sql, rf"(\n    |ADD COLUMN IF NOT EXISTS ){column}\s", column)

    def test_rows_and_insert(self):
        gw = _gw()
        TaskTaggedGateway(gw, "codegen").complete(system="s", user="u")
        rows = ledger_rows(gw.recorder.records, build_id="bld_1", tenant_id="t", project_id="p",
                           reservation_id="bld_1", final_outcome="READY")
        row = dict(zip(_COLUMNS, rows[0]))
        self.assertEqual((row["task_id"], row["final_outcome"]), ("bld_1:codegen", "READY"))
        # T5: codegen's mandatory floor is 85, so the quality-85 model is the only candidate (the cheap one is below)
        self.assertEqual([c["name"] for c in json.loads(row["candidate_set"])], ["strong"])
        self.assertNotIn("secret-", json.dumps(row, default=str))  # key values never reach the ledger

        executed = {}

        class Cur:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def executemany(self, sql, rows): executed.update(sql=sql, rows=rows)

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def transaction(self): return self
            def cursor(self): return Cur()

        class Pool:
            def connection(self): return Conn()

        n = persist_attempts(Pool(), gw.recorder.records, build_id="bld_1", final_outcome="READY")
        self.assertEqual(n, 1)
        self.assertIn("ON CONFLICT (attempt_id) DO UPDATE SET final_outcome", executed["sql"])
        self.assertIn("%s::jsonb", executed["sql"])

    def test_content_version_is_stable(self):
        self.assertEqual(content_version("a", 1), content_version("a", 1))
        self.assertNotEqual(content_version("a", 1), content_version("a", 2))


if __name__ == "__main__":
    unittest.main()
