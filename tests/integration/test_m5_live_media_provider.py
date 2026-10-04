"""M5 Task 9 gated integration: one real paid image generation.

SKIPs unless M5_LIVE_IMAGE=1 and the OMNI_IMAGE_PROVIDER_* configuration
(base URL, API key reference, model, maximum price, price source) is present.
It generates exactly one image, verifies checksum/format/provenance through
the real CapabilityExecutor path and records the cost evidence it received.
"""
from __future__ import annotations

import hashlib
import os
import unittest
from decimal import Decimal


def _skip_reason() -> str | None:
    if os.environ.get("M5_LIVE_IMAGE") != "1":
        return "M5_LIVE_IMAGE=1 not set (no real image provider supplied)"
    from omni_prod.providers.image_provider import image_provider_readiness
    readiness = image_provider_readiness()
    if readiness["status"] != "PARTIAL":
        return f"image provider {readiness['status']}: {readiness['reason']}"
    return None


_SKIP = _skip_reason()


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class LiveImageProviderTests(unittest.TestCase):
    def test_real_image_is_generated_stored_and_verified(self):
        from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
        from omni_prod.capability_repository import MemoryCapabilityRepository
        from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_capability_stage

        class Store:
            def __init__(self): self.objects = {}
            def put_bytes(self, key, data):
                self.objects[key] = bytes(data)
                return type("Stored", (), {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})()
            def get_bytes(self, key, *, verify=True): return self.objects[key]

        store = Store()
        stage = build_image_capability_stage(env=os.environ, repository=MemoryCapabilityRepository(),
                                             artifact_store=store, journal=MemorySubmissionJournal(),
                                             worker_id="m5-live")
        requirement = CapabilityRequirement(
            id="cap-media-image-generate", key="media.image.generate", purpose="product icon", required=True,
            constraints={"prompt": "Minimal geometric app icon, single color, no text"})
        evidence = stage.prepare(build_id="bld_live_image", project_id="prj_live_image",
                                 plan=CapabilityPlan(requirements=(requirement,), target_keys=()),
                                 authorized_maximum_usd=Decimal("0.25"), now=0.0)
        row = evidence["requirements"][0]
        self.assertEqual(row["status"], "VERIFIED")
        data = store.objects[row["artifact_key"]]
        self.assertEqual(row["verification"]["artifacts"][0]["sha256"], hashlib.sha256(data).hexdigest())
        usage = evidence["usage"][0]
        self.assertIsNotNone(usage["maximum_cost_usd"])
        print("LIVE_IMAGE_EVIDENCE", row["selected_provider"], row["artifact_key"], len(data),
              "actual_cost_usd=", usage["actual_cost_usd"])


if __name__ == "__main__":
    unittest.main()
