from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_executor import CapabilityExecutionAssignment, CapabilityExecutor
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.media_gateway import HTTPMediaGateway, MediaEndpoint
from omni_prod.provider_pricing import PriceStatus, ProviderPriceCatalog, ProviderPriceEntry
from omni_prod.provider_registry import ProviderRegistry
from omni_prod.providers.http_media_provider import HTTPMediaCapabilityProvider
from omni_prod.storage import StoredObject


PNG = b"\x89PNG\r\n\x1a\n" + b"http-provider-real-bytes"


class _ProviderHandler(BaseHTTPRequestHandler):
    seen: list[dict] = []

    def do_POST(self):  # noqa: N802 - stdlib callback name
        if self.path != "/v1/assets/generate":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).seen.append(payload)
        body = json.dumps({
            "content_base64": base64.b64encode(PNG).decode("ascii"),
            "mime_type": "image/png",
            "metadata": {"usage_units": 1, "request_id": "fake-http-1"},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: A003 - stdlib API
        return


class _LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / key

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise KeyError(key)
        payload = bytes(data)
        path.write_bytes(payload)
        return StoredObject(key, hashlib.sha256(payload).hexdigest(), len(payload))

    def get_bytes(self, key: str, *, verify: bool = True) -> bytes:
        return self._path(key).read_bytes()

    def iter_bytes(self, key: str, *, chunk_size: int = 7, **kwargs):
        with self._path(key).open("rb") as source:
            while True:
                chunk = source.read(chunk_size)
                if not chunk:
                    break
                yield chunk


class M495ProviderHTTPIntegrationTests(unittest.TestCase):
    def setUp(self):
        _ProviderHandler.seen = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_real_http_bytes_flow_through_provider_contract_executor_verification_and_cost_evidence(self):
        endpoint = MediaEndpoint(
            name="fake-http-media",
            base_url=f"http://127.0.0.1:{self.server.server_port}",
            external=False,
            timeout_seconds=5,
        )
        gateway = HTTPMediaGateway(endpoint)
        catalog = ProviderPriceCatalog(
            version="fake-http-price-v1",
            entries=(ProviderPriceEntry(
                provider="fake-http-media",
                capability_key="media.image.generate",
                operation="generate",
                unit_name="image",
                estimated_unit_cost_usd=Decimal("0.03"),
                maximum_unit_cost_usd=Decimal("0.05"),
                status=PriceStatus.PUBLIC_LIST_PRICE,
                effective_from="2026-10-04",
            ),),
        )
        requirement = CapabilityRequirement(
            "r-http-image", "media.image.generate", "hero", True,
            constraints={"prompt": "original delivery game hero image"},
        )
        quote = catalog.quote(
            provider="fake-http-media", requirement=requirement, operation="generate"
        )
        provider = HTTPMediaCapabilityProvider(
            gateway=gateway,
            capability_keys=("media.image.generate",),
            output_formats=("image/png",),
            quote_factory=lambda req: catalog.quote(
                provider="fake-http-media", requirement=req, operation="generate"
            ),
            durable_idempotency=True,
            paid_external=False,
        )
        repo = MemoryCapabilityRepository()
        plan = CapabilityPlan((requirement,), ("target.web",))
        repo.create_plan(build_id="build-http", plan=plan)

        with tempfile.TemporaryDirectory() as td:
            store = _LocalArtifactStore(Path(td))
            executor = CapabilityExecutor(
                provider_registry=ProviderRegistry((provider,)),
                repository=repo,
                artifact_store=store,
                worker_id="integration-worker",
                max_polls=3,
            )
            summary = executor.execute_plan(
                build_id="build-http",
                project_id="project-http",
                plan=plan,
                assignments={
                    requirement.id: CapabilityExecutionAssignment(provider.name, quote)
                },
                now=100.0,
            )

        self.assertEqual(summary.status, "VERIFIED")
        self.assertEqual(len(_ProviderHandler.seen), 1)
        request = _ProviderHandler.seen[0]
        self.assertEqual(request["id"], requirement.id)
        self.assertTrue(request["idempotency_key"].startswith("cap_"))
        self.assertEqual(repo.requirements(build_id="build-http")[0]["status"], "VERIFIED")
        usage = repo.usage_for_build(build_id="build-http")
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]["estimated_cost_usd"], Decimal("0.03"))
        self.assertEqual(usage[0]["maximum_cost_usd"], Decimal("0.05"))
        self.assertIsNone(usage[0]["actual_cost_usd"])
        self.assertEqual(summary.artifacts[0].sha256, hashlib.sha256(PNG).hexdigest())


if __name__ == "__main__":
    unittest.main()
