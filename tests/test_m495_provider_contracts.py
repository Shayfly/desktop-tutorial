import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityRequirement
from omni_prod.provider_contracts import (
    CapabilityArtifact,
    CapabilityProvider,
    ProviderCapability,
    ProviderExecutionResult, ProviderArtifactPayload,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)


class ProviderContractTests(unittest.TestCase):
    def test_quote_rejects_negative_or_inverted_costs(self):
        with self.assertRaisesRegex(ValueError, "estimated_cost_usd"):
            ProviderQuote("p", "media.image.generate", Decimal("-0.01"), Decimal("1"), "v1", "image", Decimal("1"))
        with self.assertRaisesRegex(ValueError, "maximum_cost_usd"):
            ProviderQuote("p", "media.image.generate", Decimal("1"), Decimal("0.99"), "v1", "image", Decimal("1"))

    def test_quote_requires_stable_pricing_identity_and_nonnegative_units(self):
        with self.assertRaisesRegex(ValueError, "pricing_version"):
            ProviderQuote("p", "software.code.generate", Decimal("0"), Decimal("0"), "", "token", Decimal("0"))
        with self.assertRaisesRegex(ValueError, "units"):
            ProviderQuote("p", "software.code.generate", Decimal("0"), Decimal("0"), "v1", "token", Decimal("-1"))

    def test_provider_task_handle_is_persistable_and_round_trips(self):
        handle = ProviderTaskHandle(
            provider="meshy",
            provider_task_id="task-123",
            capability_requirement_id="cap-media-3d-mesh-generate",
            idempotency_key="build-1:cap-media-3d-mesh-generate:meshy:v1",
        )
        self.assertEqual(ProviderTaskHandle.from_dict(handle.to_dict()), handle)

    def test_handle_rejects_empty_durable_identifiers(self):
        with self.assertRaisesRegex(ValueError, "provider_task_id"):
            ProviderTaskHandle("p", "", "r", "idem")
        with self.assertRaisesRegex(ValueError, "idempotency_key"):
            ProviderTaskHandle("p", "task", "r", "")

    def test_task_state_rejects_unknown_status_and_invalid_progress(self):
        with self.assertRaisesRegex(ValueError, "status"):
            ProviderTaskState("MAYBE")
        with self.assertRaisesRegex(ValueError, "progress"):
            ProviderTaskState("RUNNING", 1.1)
        self.assertFalse(ProviderTaskState("RUNNING", 0.5).terminal)
        self.assertTrue(ProviderTaskState("SUCCEEDED", 1.0).terminal)
        self.assertTrue(ProviderTaskState("FAILED", error_code="provider_error").terminal)

    def test_artifact_contract_rejects_bad_size_or_sha_metadata(self):
        with self.assertRaisesRegex(ValueError, "size_bytes"):
            CapabilityArtifact("a", "model/gltf-binary", "a" * 64, -1, "p", "media.3d.mesh.generate", {}, {})
        with self.assertRaisesRegex(ValueError, "sha256"):
            CapabilityArtifact("a", "model/gltf-binary", "not-a-hash", 1, "p", "media.3d.mesh.generate", {}, {})

    def test_artifact_payload_supports_exactly_one_memory_or_file_source(self):
        memory = ProviderArtifactPayload("image/png", b"bytes", filename="x.png")
        self.assertEqual(memory.data, b"bytes")
        self.assertIsNone(memory.file_path)
        file_backed = ProviderArtifactPayload(
            "video/mp4", None, filename="clip.mp4", file_path="/tmp/clip.mp4"
        )
        self.assertEqual(file_backed.file_path, "/tmp/clip.mp4")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            ProviderArtifactPayload("image/png", None, filename="x.png")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            ProviderArtifactPayload(
                "image/png", b"bytes", filename="x.png", file_path="/tmp/x.png"
            )

    def test_execution_result_never_turns_unknown_actual_into_estimate(self):
        result = ProviderExecutionResult(artifacts=(), actual_cost_usd=None, usage={}, evidence={})
        self.assertIsNone(result.actual_cost_usd)
        with self.assertRaisesRegex(ValueError, "actual_cost_usd"):
            ProviderExecutionResult(artifacts=(), actual_cost_usd=Decimal("-0.01"), usage={}, evidence={})

    def test_provider_capability_validates_concurrency(self):
        with self.assertRaisesRegex(ValueError, "max_concurrency"):
            ProviderCapability("media.video.generate", ("video/mp4",), True, max_concurrency=0)

    def test_protocol_surface_accepts_async_safe_provider_shape(self):
        class FakeProvider:
            name = "fake"
            def capabilities(self): return (ProviderCapability("software.code.generate", ("application/zip",), True),)
            def health(self): return "HEALTHY"
            def quote(self, requirement): return ProviderQuote("fake", requirement.key, Decimal("0"), Decimal("0"), "v1", "request", Decimal("1"))
            def submit(self, requirement, *, idempotency_key): return ProviderTaskHandle("fake", "t1", requirement.id, idempotency_key)
            def poll(self, handle): return ProviderTaskState("SUCCEEDED", 1.0)
            def collect(self, handle): return ProviderExecutionResult((), None, {}, {})
            def cancel(self, handle): return None
        provider: CapabilityProvider = FakeProvider()
        req = CapabilityRequirement("r1", "software.code.generate", "code", True)
        handle = provider.submit(req, idempotency_key="idem")
        self.assertEqual(provider.poll(handle).status, "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
