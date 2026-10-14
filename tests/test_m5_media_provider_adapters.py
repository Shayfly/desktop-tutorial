"""M5 Task 9: minimal real image provider adapter (contract level).

The HTTP API used here is an in-test double that follows the configured
prediction-job protocol. Passing these tests proves the adapter's contract
behaviour; it is not evidence that any real image provider was called.
"""
from __future__ import annotations

import hashlib
import json
import struct
import unittest
import zlib
from decimal import Decimal
from pathlib import Path

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_verification import verify_capability_artifact
from omni_prod.provider_contracts import CapabilityArtifact, CapabilityProvider
from omni_prod.safe_fetch import SafeFetcher
from omni_prod.providers.image_provider import (
    AmbiguousSubmission,
    ImageProviderConfig,
    MemorySubmissionJournal,
    PostgresSubmissionJournal,
    PredictionImageProvider,
    ProviderRateLimited,
    build_image_capability_stage,
    image_provider_readiness,
)


def _png(width=4, height=3) -> bytes:
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


ENV = {
    "OMNI_IMAGE_PROVIDER_NAME": "image-predictions",
    "OMNI_IMAGE_PROVIDER_BASE_URL": "https://images.example/v1",
    "OMNI_IMAGE_PROVIDER_API_KEY_REF": "env:IMAGE_KEY",
    "IMAGE_KEY": "img-secret-key",
    "OMNI_IMAGE_PROVIDER_MODEL": "acme/brand-image-model",
    "OMNI_IMAGE_PROVIDER_ESTIMATED_USD_PER_IMAGE": "0.003",
    "OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE": "0.01",
    "OMNI_IMAGE_PROVIDER_PRICE_SOURCE": "https://images.example/pricing#2026-10-01",
    "OMNI_IMAGE_PROVIDER_COMMERCIAL_USE": "true",
    "OMNI_IMAGE_PROVIDER_LICENSE": "provider terms 2026-09: outputs owned by customer",
}


class FakePredictionAPI:
    """Prediction-job HTTP double: POST /predictions, GET /predictions/{id}, POST .../cancel, GET output."""

    def __init__(self, *, image=None, honor_idempotency=False, fail=False, rate_limit_once=False):
        self.image = image if image is not None else _png()
        self.honor_idempotency = honor_idempotency
        self.fail = fail
        self.rate_limit_once = rate_limit_once
        self.created: list[dict] = []
        self.by_key: dict[str, str] = {}
        self.polls = 0
        self.cancelled: list[str] = []
        self.auth_headers: list[str] = []
        self.idempotency_headers: list[str | None] = []

    def __call__(self, req, timeout):
        url, method = req.full_url, req.get_method()
        self.auth_headers.append(req.headers.get("Authorization", ""))
        if url.endswith("/predictions") and method == "POST":
            if self.rate_limit_once:
                self.rate_limit_once = False
                return _Resp({"detail": "slow down"}, status=429, headers={"Retry-After": "2"})
            key = req.headers.get("Idempotency-key")
            self.idempotency_headers.append(key)
            if self.honor_idempotency and key in self.by_key:
                return _Resp(self._prediction(self.by_key[key], "starting"), status=201)
            pid = f"pred_{len(self.created) + 1}"
            body = json.loads(req.data.decode())
            self.created.append({"id": pid, "body": body})
            if key:
                self.by_key[key] = pid
            return _Resp(self._prediction(pid, "starting"), status=201)
        if "/predictions/" in url and url.endswith("/cancel"):
            self.cancelled.append(url.split("/")[-2])
            return _Resp(self._prediction(url.split("/")[-2], "canceled"))
        if "/predictions/" in url:
            self.polls += 1
            pid = url.rsplit("/", 1)[-1]
            if self.fail:
                return _Resp({**self._prediction(pid, "failed"), "error": "NSFW filter triggered"})
            status = "processing" if self.polls == 1 else "succeeded"
            return _Resp(self._prediction(pid, status))
        if url.startswith("https://delivery.images.example/"):
            return _Resp(self.image, raw=True, headers={"Content-Type": "image/png"})
        raise AssertionError(f"unexpected request {method} {url}")

    def _prediction(self, pid, status):
        data = {"id": pid, "status": status, "created_at": "2026-10-04T10:00:00Z",
                "model": "acme/brand-image-model", "metrics": {"predict_time": 1.25}}
        if status == "succeeded":
            data["output"] = [f"https://delivery.images.example/{pid}/out.png"]
            data["completed_at"] = "2026-10-04T10:00:03Z"
        return data


class _Resp:
    def __init__(self, payload, *, status=200, headers=None, raw=False):
        self._body = payload if raw else json.dumps(payload).encode()
        self.status = status
        self.headers = headers or {}

    def read(self, n=-1):
        return self._body if n is None or n < 0 else self._body[:n]

    def __enter__(self):
        if self.status >= 400:
            from urllib.error import HTTPError
            import io
            raise HTTPError("https://images.example", self.status, "err", self.headers, io.BytesIO(self._body))
        return self

    def __exit__(self, *a):
        return False


def public_resolver(host, port, proto=None):
    """Test DNS: every name resolves to a documentation-free public address."""
    return [(2, 1, 6, "", ("93.184.216.34", port))]


def _fetcher(api):
    return SafeFetcher(resolver=public_resolver, urlopen=api)


def _provider(api=None, env=None, journal=None, sleeps=None):
    env = dict(ENV if env is None else env)
    config = ImageProviderConfig.from_env(env)
    sleeps = sleeps if sleeps is not None else []
    api = api or FakePredictionAPI()
    return PredictionImageProvider(
        config=config, resolve_reference=lambda ref: env[ref.split(":", 1)[1]],
        journal=journal or MemorySubmissionJournal(), urlopen=api,
        sleep=sleeps.append, poll_interval_seconds=0.5, fetcher=_fetcher(api),
    )


REQ = CapabilityRequirement(id="cap-media-image-generate", key="media.image.generate",
                            purpose="product icon", required=True,
                            constraints={"prompt": "Minimal geometric logo for a travel CRM, no text"})


class ContractTests(unittest.TestCase):
    def test_satisfies_capability_provider_protocol_and_is_paid_durable(self):
        provider = _provider()
        self.assertIsInstance(provider, CapabilityProvider)
        self.assertTrue(provider.paid_external)
        self.assertTrue(provider.durable_idempotency)
        self.assertTrue(provider.durable_result_retrieval)
        self.assertEqual(provider.name, "image-predictions")
        caps = provider.capabilities()
        self.assertEqual([c.capability_key for c in caps], ["media.image.generate"])
        self.assertTrue(caps[0].commercial_use)
        self.assertIn("image/png", caps[0].output_formats)

    def test_quote_units_come_from_configured_price_source(self):
        quote = _provider().quote(REQ)
        self.assertEqual((quote.estimated_cost_usd, quote.maximum_cost_usd), (Decimal("0.003"), Decimal("0.01")))
        self.assertEqual((quote.unit_name, quote.units), ("image", Decimal("1")))
        self.assertIn("images.example/pricing", quote.pricing_version)
        double = CapabilityRequirement(id="x", key="media.image.generate", purpose="p", required=True, quantity=2)
        self.assertEqual(_provider().quote(double).maximum_cost_usd, Decimal("0.02"))

    def test_full_lifecycle_produces_verified_image_with_provenance(self):
        api = FakePredictionAPI()
        provider = _provider(api)
        handle = provider.submit(REQ, idempotency_key="cap_abc")
        self.assertEqual(handle.provider_task_id, "pred_1")
        self.assertEqual(api.created[0]["body"]["input"]["prompt"], REQ.constraints["prompt"])
        states = [provider.poll(handle).status for _ in range(2)]
        self.assertEqual(states, ["RUNNING", "SUCCEEDED"])
        result = provider.collect(handle)
        self.assertEqual(len(result.payloads), 1)
        payload = result.payloads[0]
        self.assertEqual(payload.mime_type, "image/png")
        self.assertTrue(payload.data.startswith(b"\x89PNG"))
        self.assertEqual(payload.metadata["width"], 4)
        self.assertEqual(payload.metadata["height"], 3)
        self.assertTrue(payload.metadata["commercial_use"])
        self.assertIn("customer", payload.metadata["license"])
        prov = payload.provenance
        self.assertEqual(prov["provider_task_id"], "pred_1")
        self.assertEqual(prov["model"], "acme/brand-image-model")
        self.assertEqual(prov["prompt_sha256"], hashlib.sha256(REQ.constraints["prompt"].encode()).hexdigest())
        self.assertEqual(prov["sha256"], hashlib.sha256(payload.data).hexdigest())
        self.assertIsNone(result.actual_cost_usd)  # provider reported no cost: unknown, not the estimate
        self.assertEqual(result.usage["predict_time_seconds"], 1.25)
        # executor-side verification accepts the bytes
        artifact = CapabilityArtifact("k", payload.mime_type, hashlib.sha256(payload.data).hexdigest(),
                                      len(payload.data), provider.name, REQ.key)
        self.assertIn("png-signature", verify_capability_artifact(artifact, payload.data).checks)
        # the API key never appears in evidence
        self.assertNotIn("img-secret-key", json.dumps({**result.usage, **result.evidence, **prov}))
        self.assertTrue(all(h == "Bearer img-secret-key" for h in api.auth_headers[:1]))

    def test_provider_reported_cost_is_used_only_when_present(self):
        api = FakePredictionAPI()
        original = api._prediction
        api._prediction = lambda pid, status: {**original(pid, status), "cost_usd": 0.0042}
        provider = _provider(api)
        handle = provider.submit(REQ, idempotency_key="cap_cost")
        while not provider.poll(handle).terminal:
            pass
        self.assertEqual(provider.collect(handle).actual_cost_usd, Decimal("0.0042"))

    def test_output_format_is_validated(self):
        api = FakePredictionAPI(image=b"<html>not an image</html>")
        provider = _provider(api)
        handle = provider.submit(REQ, idempotency_key="cap_bad")
        while not provider.poll(handle).terminal:
            pass
        with self.assertRaises(ValueError):
            provider.collect(handle)

    def test_failed_prediction_is_explicit(self):
        provider = _provider(FakePredictionAPI(fail=True))
        handle = provider.submit(REQ, idempotency_key="cap_fail")
        state = provider.poll(handle)
        self.assertEqual(state.status, "FAILED")
        self.assertIn("NSFW", state.error_message)

    def test_cancel_reaches_provider(self):
        api = FakePredictionAPI()
        provider = _provider(api)
        handle = provider.submit(REQ, idempotency_key="cap_cancel")
        provider.cancel(handle)
        self.assertEqual(api.cancelled, ["pred_1"])


class IdempotencyAndResumeTests(unittest.TestCase):
    def test_resubmit_with_same_key_reuses_recorded_task(self):
        api = FakePredictionAPI()
        journal = MemorySubmissionJournal()
        first = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_same")
        second = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_same")
        self.assertEqual(first.provider_task_id, second.provider_task_id)
        self.assertEqual(len(api.created), 1)

    def test_crash_resume_by_task_id_in_a_new_process(self):
        api = FakePredictionAPI()
        journal = MemorySubmissionJournal()
        handle = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_resume")
        fresh = _provider(api, journal=journal)  # no in-process state carried over
        while not fresh.poll(handle).terminal:
            pass
        self.assertTrue(fresh.collect(handle).payloads[0].data.startswith(b"\x89PNG"))

    def test_ambiguous_crash_window_fails_closed_without_idempotency_support(self):
        api = FakePredictionAPI()
        journal = MemorySubmissionJournal()
        journal.begin("cap_window", provider="image-predictions")  # crashed after intent, before task id
        with self.assertRaises(AmbiguousSubmission):
            _provider(api, journal=journal).submit(REQ, idempotency_key="cap_window")
        self.assertEqual(api.created, [])  # never a blind duplicate paid submit

    def test_ambiguous_window_resubmits_when_provider_honors_idempotency(self):
        api = FakePredictionAPI(honor_idempotency=True)
        api.by_key["cap_window2"] = "pred_existing"
        env = dict(ENV, OMNI_IMAGE_PROVIDER_IDEMPOTENCY_HEADER="Idempotency-Key")
        journal = MemorySubmissionJournal()
        journal.begin("cap_window2", provider="image-predictions")
        handle = _provider(api, env=env, journal=journal).submit(REQ, idempotency_key="cap_window2")
        self.assertEqual(handle.provider_task_id, "pred_existing")
        self.assertEqual(api.created, [])
        self.assertEqual(api.idempotency_headers, ["cap_window2"])

    def test_rate_limit_is_explicit_with_retry_after(self):
        api = FakePredictionAPI(rate_limit_once=True)
        provider = _provider(api)
        with self.assertRaises(ProviderRateLimited) as ctx:
            provider.submit(REQ, idempotency_key="cap_429")
        self.assertEqual(ctx.exception.retry_after_seconds, 2)
        # the intent was journaled before the 429; a later retry is safe only
        # because the 429 proves nothing was created -> journal cleared
        handle = provider.submit(REQ, idempotency_key="cap_429")
        self.assertEqual(handle.provider_task_id, "pred_1")

    def test_poll_waits_between_requests(self):
        sleeps = []
        provider = _provider(sleeps=sleeps)
        handle = provider.submit(REQ, idempotency_key="cap_sleep")
        provider.poll(handle)
        provider.poll(handle)
        self.assertEqual(sleeps, [0.5, 0.5])


class ConfigurationTruthTests(unittest.TestCase):
    def test_not_configured_without_credentials_or_price(self):
        for missing in ("OMNI_IMAGE_PROVIDER_BASE_URL", "OMNI_IMAGE_PROVIDER_API_KEY_REF",
                        "OMNI_IMAGE_PROVIDER_MODEL", "OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE"):
            env = {k: v for k, v in ENV.items() if k != missing}
            readiness = image_provider_readiness(env)
            self.assertEqual(readiness["status"], "NOT_CONFIGURED", missing)
            self.assertIn(missing, readiness["reason"])
        self.assertEqual(image_provider_readiness(ENV)["status"], "PARTIAL")
        self.assertEqual(image_provider_readiness({})["optional_media"]["media.audio.tts"], "NOT_CONFIGURED")
        self.assertEqual(image_provider_readiness({})["optional_media"]["media.3d.mesh.generate"], "NOT_CONFIGURED")

    def test_commercial_use_must_be_declared(self):
        env = dict(ENV, OMNI_IMAGE_PROVIDER_COMMERCIAL_USE="false")
        self.assertFalse(_provider(env=env).capabilities()[0].commercial_use)

    def test_api_key_must_be_a_reference(self):
        env = dict(ENV, OMNI_IMAGE_PROVIDER_API_KEY_REF="sk-live-plaintext")
        self.assertEqual(image_provider_readiness(env)["status"], "BLOCKED")

    def test_capability_stage_assigns_image_requirement_when_configured(self):
        class _Repo:  # minimal capability repository double
            def __init__(self): self.rows = {}
            def create_plan(self, *, build_id, plan):
                for r in plan.requirements:
                    self.rows[r.id] = {"requirement_id": r.id, "capability_key": r.key,
                                       "required": r.required, "status": "PLANNED"}
            def requirements(self, *, build_id): return list(self.rows.values())
            def transition(self, *, build_id, requirement_id, expected, target, **kw):
                self.rows[requirement_id]["status"] = target
                return True

        plan = CapabilityPlan(requirements=(REQ,), target_keys=())
        stage = build_image_capability_stage(env=ENV, repository=_Repo(), artifact_store=object(),
                                             journal=MemorySubmissionJournal(), worker_id="w1")
        assignments = stage.assignments_resolver(plan)
        self.assertEqual(assignments[REQ.id].provider, "image-predictions")
        self.assertEqual(assignments[REQ.id].quote.maximum_cost_usd, Decimal("0.01"))
        self.assertIsNotNone(stage.executor)

        empty = build_image_capability_stage(env={}, repository=_Repo(), artifact_store=object(),
                                             journal=MemorySubmissionJournal(), worker_id="w1")
        self.assertIsNone(empty.executor)
        self.assertEqual(empty.assignments_resolver(plan), {})

        noncommercial = build_image_capability_stage(
            env=dict(ENV, OMNI_IMAGE_PROVIDER_COMMERCIAL_USE="false"), repository=_Repo(),
            artifact_store=object(), journal=MemorySubmissionJournal(), worker_id="w1")
        self.assertEqual(noncommercial.assignments_resolver(plan), {})  # never routed for commercial builds


class JournalMigrationTests(unittest.TestCase):
    def test_migration_026_defines_durable_submission_journal(self):
        sql = (Path(__file__).resolve().parents[1] / "infra/postgres/026_media_provider_submissions.sql").read_text().lower()
        self.assertIn("create table if not exists media_provider_submissions", sql)
        self.assertIn("idempotency_key text primary key", sql)
        self.assertIn("state in ('intent','submitted')", sql)

    def test_postgres_journal_uses_insert_on_conflict_do_nothing(self):
        calls = []

        class _Cur:
            def execute(self, sql, params=None): calls.append(" ".join(sql.split()))
            def fetchone(self): return ("cap_x", "image-predictions", "INTENT", None)
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _Conn:
            def cursor(self): return _Cur()
            def transaction(self): return self
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _Pool:
            def connection(self): return _Conn()

        record = PostgresSubmissionJournal(_Pool()).begin("cap_x", provider="image-predictions")
        self.assertFalse(record.preexisting)  # INSERT ... RETURNING produced the row
        self.assertEqual(record.state, "INTENT")
        self.assertTrue(any("ON CONFLICT (idempotency_key) DO NOTHING" in c for c in calls))


if __name__ == "__main__":
    unittest.main()


class GoldenImageEndToEndTests(unittest.TestCase):
    """Stage -> router -> real CapabilityExecutor -> adapter -> stored, verified logo."""

    def test_golden_web_saas_logo_is_generated_stored_and_verified(self):
        from omni_prod.capability_repository import MemoryCapabilityRepository

        class Store:
            def __init__(self): self.objects = {}
            def put_bytes(self, key, data):
                if key in self.objects:
                    raise KeyError(key)
                self.objects[key] = bytes(data)
                return type("Stored", (), {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})()
            def get_bytes(self, key, *, verify=True): return self.objects[key]

        api = FakePredictionAPI()
        store = Store()
        repo = MemoryCapabilityRepository()
        stage = build_image_capability_stage(env=ENV, repository=repo, artifact_store=store,
                                             journal=MemorySubmissionJournal(), worker_id="w1", urlopen=api,
                                             fetcher=_fetcher(api))
        stage.executor.provider_registry.get("image-predictions").sleep = lambda s: None
        plan = CapabilityPlan(requirements=(REQ,), target_keys=())
        evidence = stage.prepare(build_id="bld_logo", project_id="prj_crm", plan=plan,
                                 authorized_maximum_usd=Decimal("0.05"), now=1000.0)
        row = evidence["requirements"][0]
        self.assertEqual(row["status"], "VERIFIED")
        self.assertEqual(row["selected_provider"], "image-predictions")
        stored = store.objects[row["artifact_key"]]
        self.assertTrue(stored.startswith(b"\x89PNG"))
        checks = row["verification"]["artifacts"][0]["checks"]
        self.assertIn("png-signature", checks)
        self.assertIn("sha256", checks)
        usage = evidence["usage"][0]
        self.assertEqual(usage["estimated_cost_usd"], Decimal("0.003"))
        self.assertIsNone(usage["actual_cost_usd"])  # unknown stays unknown
        self.assertEqual(len(api.created), 1)

    def test_authorization_ceiling_blocks_paid_image_before_submit(self):
        from omni_prod.capability_repository import MemoryCapabilityRepository
        from omni_prod.capability_worker import CapabilityStageBlocked

        api = FakePredictionAPI()
        stage = build_image_capability_stage(env=ENV, repository=MemoryCapabilityRepository(), artifact_store=object(),
                                             journal=MemorySubmissionJournal(), worker_id="w1", urlopen=api)
        with self.assertRaises(CapabilityStageBlocked):
            stage.prepare(build_id="bld_cap", project_id="p", plan=CapabilityPlan(requirements=(REQ,), target_keys=()),
                          authorized_maximum_usd=Decimal("0.001"), now=1.0)
        self.assertEqual(api.created, [])
