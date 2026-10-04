"""M5 Task 9: one real, configurable image provider behind ``media.image.generate``.

Deliberately minimal: image generation only (product icon / logo / brand
visual for a generated Web/SaaS product). Audio, voice and 3D remain
NOT_CONFIGURED here; no media factory is built.

Protocol: a prediction-job HTTP API (as used by several hosted inference
services):

  POST {base}{submit_path}            {"input": {...}, "model"|"version": ...} -> {"id", "status"}
  GET  {base}/predictions/{id}        -> {"status", "output", "error", "metrics", ...}
  POST {base}/predictions/{id}/cancel

Provider identity, endpoint, model, price and licence live only in
configuration; the canonical capability key stays vendor-neutral.

Durability and spend safety:

* ``quote`` uses operator-configured per-image estimate/maximum prices with a
  named price source. No price -> NOT_CONFIGURED (never a guessed price).
* A durable submission journal records INTENT before the paid POST and the
  provider task id right after. Resubmitting the same idempotency key returns
  the recorded task. If a crash left INTENT without a task id, the adapter
  either resubmits with a provider-honoured idempotency header (only when the
  operator declares one) or raises ``AmbiguousSubmission`` -- it never blindly
  pays twice.
* Results are retrievable by provider task id from a fresh process.
* Output bytes are size-limited, MIME-sniffed (PNG/JPEG/WebP), checksummed and
  carry provenance; the executor re-verifies before storing.
* ``actual_cost_usd`` is the provider's explicit cost field or None.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import os
import struct
import time
from typing import Any, Callable, Mapping
from urllib import error, parse, request

from ..capabilities import CapabilityRequirement
from ..infrastructure_contracts import validate_secret_reference
from ..provider_contracts import (
    ProviderArtifactPayload,
    ProviderCapability,
    ProviderExecutionResult,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)
from ..provider_router import parse_retry_after_seconds
from ..provider_usage import _cost
from ..safe_fetch import SafeFetcher, UnsafeURL

CAPABILITY_KEY = "media.image.generate"
OPTIONAL_MEDIA_KEYS = ("media.audio.tts", "media.audio.sfx", "media.audio.music", "media.3d.mesh.generate")
_FORMATS = {"png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg", "webp": "image/webp"}
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


class ProviderRateLimited(RuntimeError):
    def __init__(self, message: str, *, retry_after_seconds: int | None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AmbiguousSubmission(RuntimeError):
    """A previous paid submit may have reached the provider; refusing to pay twice."""


def _clean(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name, "") or "").strip()


def _decimal(value: str) -> Decimal | None:
    try:
        amount = Decimal(value)
    except Exception:
        return None
    return amount if amount.is_finite() and amount >= 0 else None


@dataclass(frozen=True)
class ImageProviderConfig:
    name: str = "image-provider"
    base_url: str = ""
    api_key_ref: str = ""
    model: str = ""
    version: str = ""
    submit_path: str = "/predictions"
    output_format: str = "png"
    idempotency_header: str = ""
    commercial_use: bool = False
    license: str = ""
    estimated_usd_per_image: Decimal | None = None
    maximum_usd_per_image: Decimal | None = None
    price_source: str = ""
    max_bytes: int = 20 * 1024 * 1024
    timeout_seconds: float = 60.0
    output_hosts: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ImageProviderConfig":
        env = os.environ if env is None else env
        fmt = (_clean(env, "OMNI_IMAGE_PROVIDER_OUTPUT_FORMAT") or "png").lower()
        return cls(
            name=_clean(env, "OMNI_IMAGE_PROVIDER_NAME") or "image-provider",
            base_url=_clean(env, "OMNI_IMAGE_PROVIDER_BASE_URL").rstrip("/"),
            api_key_ref=_clean(env, "OMNI_IMAGE_PROVIDER_API_KEY_REF"),
            model=_clean(env, "OMNI_IMAGE_PROVIDER_MODEL"),
            version=_clean(env, "OMNI_IMAGE_PROVIDER_VERSION"),
            submit_path=_clean(env, "OMNI_IMAGE_PROVIDER_SUBMIT_PATH") or "/predictions",
            output_format=fmt if fmt in _FORMATS else "png",
            idempotency_header=_clean(env, "OMNI_IMAGE_PROVIDER_IDEMPOTENCY_HEADER"),
            commercial_use=_clean(env, "OMNI_IMAGE_PROVIDER_COMMERCIAL_USE").lower() in {"1", "true", "yes"},
            license=_clean(env, "OMNI_IMAGE_PROVIDER_LICENSE"),
            estimated_usd_per_image=_decimal(_clean(env, "OMNI_IMAGE_PROVIDER_ESTIMATED_USD_PER_IMAGE")),
            maximum_usd_per_image=_decimal(_clean(env, "OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE")),
            price_source=_clean(env, "OMNI_IMAGE_PROVIDER_PRICE_SOURCE"),
            max_bytes=int(_clean(env, "OMNI_IMAGE_PROVIDER_MAX_BYTES") or 20 * 1024 * 1024),
            output_hosts=tuple(h.strip().lower() for h in _clean(env, "OMNI_IMAGE_PROVIDER_OUTPUT_HOSTS").split(",") if h.strip()),
        )

    def status(self) -> tuple[str, str]:
        missing = [name for name, value in (
            ("OMNI_IMAGE_PROVIDER_BASE_URL", self.base_url),
            ("OMNI_IMAGE_PROVIDER_API_KEY_REF", self.api_key_ref),
            ("OMNI_IMAGE_PROVIDER_MODEL", self.model),
            ("OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE", self.maximum_usd_per_image),
            ("OMNI_IMAGE_PROVIDER_PRICE_SOURCE", self.price_source),
        ) if not value]
        if missing:
            return "NOT_CONFIGURED", "missing " + ", ".join(missing)
        try:
            validate_secret_reference(self.api_key_ref)
        except ValueError:
            return "BLOCKED", "OMNI_IMAGE_PROVIDER_API_KEY_REF must be an env:/vault: reference, not a key"
        if not self.base_url.startswith("https://"):
            return "BLOCKED", "OMNI_IMAGE_PROVIDER_BASE_URL must be https"
        estimated = self.estimated_usd_per_image if self.estimated_usd_per_image is not None else self.maximum_usd_per_image
        if estimated > self.maximum_usd_per_image:
            return "BLOCKED", "estimated price exceeds maximum price"
        return "PARTIAL", "configured; LIVE only after a real generation produced a verified artifact"


# --------------------------------------------------------------------------
# Durable submission journal
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SubmissionRecord:
    idempotency_key: str
    provider: str
    state: str
    provider_task_id: str | None
    preexisting: bool


class MemorySubmissionJournal:
    """Process-local journal (tests only). Production uses PostgresSubmissionJournal."""

    durable = False

    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def begin(self, idempotency_key: str, *, provider: str) -> SubmissionRecord:
        row = self._rows.get(idempotency_key)
        if row is None:
            self._rows[idempotency_key] = {"provider": provider, "state": "INTENT", "provider_task_id": None}
            return SubmissionRecord(idempotency_key, provider, "INTENT", None, False)
        if row["provider"] != provider:
            raise RuntimeError("idempotency key already used by another provider")
        return SubmissionRecord(idempotency_key, row["provider"], row["state"], row["provider_task_id"], True)

    def record_task(self, idempotency_key: str, provider_task_id: str) -> None:
        row = self._rows[idempotency_key]
        if row["provider_task_id"] not in (None, provider_task_id):
            raise RuntimeError("submission already bound to a different provider task")
        row.update(state="SUBMITTED", provider_task_id=provider_task_id)

    def clear(self, idempotency_key: str) -> None:
        row = self._rows.get(idempotency_key)
        if row is not None and row["provider_task_id"] is None:
            del self._rows[idempotency_key]


class PostgresSubmissionJournal:
    """Durable journal (migration 026)."""

    durable = True

    def __init__(self, pool) -> None:
        self._pool = pool

    def begin(self, idempotency_key: str, *, provider: str) -> SubmissionRecord:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO media_provider_submissions(idempotency_key, provider, state) "
                        "VALUES(%s,%s,'INTENT') ON CONFLICT (idempotency_key) DO NOTHING "
                        "RETURNING idempotency_key, provider, state, provider_task_id",
                        (idempotency_key, provider),
                    )
                    row = cur.fetchone()
                    preexisting = False
                    if row is None:
                        preexisting = True
                        cur.execute(
                            "SELECT idempotency_key, provider, state, provider_task_id "
                            "FROM media_provider_submissions WHERE idempotency_key=%s FOR UPDATE",
                            (idempotency_key,),
                        )
                        row = cur.fetchone()
        if row is None:
            raise RuntimeError("submission journal row vanished")
        if row[1] != provider:
            raise RuntimeError("idempotency key already used by another provider")
        return SubmissionRecord(row[0], row[1], row[2], row[3], preexisting)

    def record_task(self, idempotency_key: str, provider_task_id: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE media_provider_submissions SET state='SUBMITTED', provider_task_id=%s, updated_at=now() "
                        "WHERE idempotency_key=%s AND (provider_task_id IS NULL OR provider_task_id=%s)",
                        (provider_task_id, idempotency_key, provider_task_id),
                    )
                    if getattr(cur, "rowcount", 1) != 1:
                        raise RuntimeError("submission already bound to a different provider task")

    def clear(self, idempotency_key: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM media_provider_submissions "
                        "WHERE idempotency_key=%s AND state='INTENT' AND provider_task_id IS NULL",
                        (idempotency_key,),
                    )


# --------------------------------------------------------------------------
# Image sniffing
# --------------------------------------------------------------------------

def sniff_image(data: bytes) -> tuple[str, int | None, int | None]:
    """Return (mime, width, height) from magic bytes, or raise ValueError."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) >= 24 and data[12:16] == b"IHDR":
            width, height = struct.unpack(">II", data[16:24])
            return "image/png", width, height
        return "image/png", None, None
    if data.startswith(b"\xff\xd8\xff"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return "image/jpeg", width, height
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + length
        return "image/jpeg", None, None
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", None, None
    raise ValueError("provider output is not a PNG, JPEG or WebP image")


# --------------------------------------------------------------------------
# Provider
# --------------------------------------------------------------------------

class PredictionImageProvider:
    paid_external = True

    def __init__(self, *, config: ImageProviderConfig, resolve_reference: Callable[[str], str], journal,
                 urlopen=None, sleep: Callable[[float], None] | None = None, poll_interval_seconds: float = 2.0,
                 max_rate_limit_wait_seconds: float = 30.0, fetcher: SafeFetcher | None = None) -> None:
        status, reason = config.status()
        if status != "PARTIAL":
            raise ValueError(f"image provider is {status}: {reason}")
        self.config = config
        self.name = config.name
        self.resolve_reference = resolve_reference
        self.journal = journal
        self.urlopen = urlopen or request.urlopen
        # Provider-returned output URLs are untrusted: SSRF-guarded fetch with an
        # optional host allowlist (configured output hosts + the API host).
        api_host = (parse.urlsplit(config.base_url).hostname or "").lower()
        allow = tuple(config.output_hosts) + ((api_host,) if config.output_hosts and api_host else ())
        self.fetcher = fetcher or SafeFetcher(allowed_hosts=allow, max_bytes=config.max_bytes,
                                              timeout_seconds=config.timeout_seconds)
        self.sleep = sleep or time.sleep
        self.poll_interval_seconds = poll_interval_seconds
        self.max_rate_limit_wait_seconds = max_rate_limit_wait_seconds
        # Fail-closed journal + provider-side retrieval by task id.
        self.durable_idempotency = True
        self.durable_result_retrieval = True
        self._predictions: dict[str, dict] = {}
        self._submitted_prompts: dict[str, str] = {}

    # -- protocol -----------------------------------------------------------
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        formats = (_FORMATS[self.config.output_format],) + tuple(
            m for m in ("image/png", "image/jpeg", "image/webp") if m != _FORMATS[self.config.output_format])
        return (ProviderCapability(CAPABILITY_KEY, formats, self.config.commercial_use),)

    def health(self) -> str:
        return "HEALTHY"

    def quote(self, requirement: CapabilityRequirement) -> ProviderQuote:
        if requirement.key != CAPABILITY_KEY:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        units = Decimal(requirement.quantity)
        maximum = self.config.maximum_usd_per_image
        estimated = self.config.estimated_usd_per_image if self.config.estimated_usd_per_image is not None else maximum
        return ProviderQuote(
            provider=self.name, capability_key=requirement.key,
            estimated_cost_usd=estimated * units, maximum_cost_usd=maximum * units,
            pricing_version=f"operator-config:{self.config.price_source}", unit_name="image", units=units,
        )

    def _prompt(self, requirement: CapabilityRequirement) -> str:
        explicit = str(requirement.constraints.get("prompt") or "").strip()
        if explicit:
            return explicit
        return (f"Original {requirement.purpose} for a modern web product. Clean, simple, distinctive; "
                "no text, no third-party logos, trademarks or characters.")

    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.resolve_reference(self.config.api_key_ref)}",
                   "Content-Type": "application/json"}
        if idempotency_key and self.config.idempotency_header:
            headers[self.config.idempotency_header] = idempotency_key
        return headers

    def _json(self, method: str, url: str, *, body: dict | None = None, idempotency_key: str | None = None) -> dict:
        req = request.Request(url, method=method, headers=self._headers(idempotency_key=idempotency_key),
                              data=None if body is None else json.dumps(body).encode())
        with self.urlopen(req, timeout=self.config.timeout_seconds) as resp:
            return json.loads(resp.read().decode() or "{}")

    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
        if requirement.key != CAPABILITY_KEY:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        record = self.journal.begin(idempotency_key, provider=self.name)
        if record.provider_task_id:
            return ProviderTaskHandle(self.name, record.provider_task_id, requirement.id, idempotency_key)
        if record.preexisting and not self.config.idempotency_header:
            raise AmbiguousSubmission(
                f"{self.name}: a previous submit for {idempotency_key} may have reached the provider and the "
                "provider has no declared idempotency header; manual reconciliation required")
        body: dict[str, Any] = {"input": {"prompt": self._prompt(requirement),
                                          "output_format": self.config.output_format,
                                          "num_outputs": int(requirement.quantity)}}
        if self.config.version:
            body["version"] = self.config.version
        else:
            body["model"] = self.config.model
        try:
            prediction = self._json("POST", self.config.base_url + self.config.submit_path, body=body,
                                    idempotency_key=idempotency_key)
        except error.HTTPError as exc:
            if exc.code == 429:
                self.journal.clear(idempotency_key)  # rejected before creation: safe to retry later
                raise ProviderRateLimited(f"{self.name} rate limited submit",
                                          retry_after_seconds=parse_retry_after_seconds(exc.headers.get("Retry-After"))) from None
            if 400 <= exc.code < 500:
                self.journal.clear(idempotency_key)  # definite rejection: nothing was created
                raise RuntimeError(f"{self.name} rejected submit: HTTP {exc.code}") from None
            raise RuntimeError(f"{self.name} submit outcome unknown: HTTP {exc.code}") from None  # keep INTENT
        task_id = str(prediction.get("id") or "").strip()
        if not task_id:
            raise RuntimeError(f"{self.name} submit returned no task id")
        self.journal.record_task(idempotency_key, task_id)
        self._predictions[task_id] = prediction
        self._submitted_prompts[task_id] = body["input"]["prompt"]
        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)

    def _task_url(self, task_id: str) -> str:
        return f"{self.config.base_url}/predictions/{parse.quote(task_id, safe='')}"

    def poll(self, handle: ProviderTaskHandle) -> ProviderTaskState:
        self.sleep(self.poll_interval_seconds)
        try:
            prediction = self._json("GET", self._task_url(handle.provider_task_id))
        except error.HTTPError as exc:
            if exc.code == 429:
                wait = parse_retry_after_seconds(exc.headers.get("Retry-After")) or self.poll_interval_seconds
                self.sleep(min(float(wait), self.max_rate_limit_wait_seconds))
                return ProviderTaskState("RUNNING", None)
            raise
        self._predictions[handle.provider_task_id] = prediction
        status = str(prediction.get("status") or "").lower()
        if status == "succeeded":
            return ProviderTaskState("SUCCEEDED", 1.0)
        if status == "failed":
            return ProviderTaskState("FAILED", None, "provider_failed", str(prediction.get("error") or "")[:500])
        if status in {"canceled", "cancelled"}:
            return ProviderTaskState("CANCELLED", None)
        if status in {"starting", "queued"}:
            return ProviderTaskState("QUEUED", 0.0)
        return ProviderTaskState("RUNNING", None)

    def _download(self, url: str) -> bytes:
        parsed = parse.urlsplit(url)
        headers = {}
        if parsed.netloc == parse.urlsplit(self.config.base_url).netloc:
            headers = {"Authorization": self._headers()["Authorization"]}  # never sent to other hosts
        try:
            data, _ = self.fetcher.get(url, headers=headers)
        except UnsafeURL as exc:
            raise ValueError(f"provider output URL rejected: {exc}") from None
        return data

    def collect(self, handle: ProviderTaskHandle) -> ProviderExecutionResult:
        prediction = self._predictions.get(handle.provider_task_id)
        if not prediction or str(prediction.get("status")).lower() != "succeeded":
            prediction = self._json("GET", self._task_url(handle.provider_task_id))
        if str(prediction.get("status")).lower() != "succeeded":
            raise RuntimeError(f"{self.name} task {handle.provider_task_id} is not succeeded")
        output = prediction.get("output")
        urls = [output] if isinstance(output, str) else [u for u in (output or []) if isinstance(u, str)]
        if not urls:
            raise RuntimeError(f"{self.name} task {handle.provider_task_id} returned no output")
        payloads = []
        for index, url in enumerate(urls):
            data = self._download(url)
            mime, width, height = sniff_image(data)
            digest = hashlib.sha256(data).hexdigest()
            # The provider's echoed input wins; otherwise the prompt this process
            # submitted. After a crash with no echo the hash is honestly unknown.
            prompt = (str((prediction.get("input") or {}).get("prompt") or "")
                      or self._submitted_prompts.get(handle.provider_task_id, ""))
            payloads.append(ProviderArtifactPayload(
                mime_type=mime, data=data,
                filename=f"{handle.capability_requirement_id}-{index + 1}.{_EXT[mime]}",
                metadata={"width": width, "height": height, "commercial_use": self.config.commercial_use,
                          "license": self.config.license or "not declared", "output_format": _EXT[mime]},
                provenance={
                    "provider": self.name, "model": prediction.get("model") or self.config.model,
                    "version": prediction.get("version") or self.config.version or None,
                    "provider_task_id": handle.provider_task_id, "idempotency_key": handle.idempotency_key,
                    "created_at": prediction.get("created_at"), "completed_at": prediction.get("completed_at"),
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest() if prompt else None,
                    "sha256": digest, "output_host": parse.urlsplit(url).netloc,
                },
            ))
        metrics = prediction.get("metrics") or {}
        return ProviderExecutionResult(
            artifacts=(), actual_cost_usd=_cost(prediction.get("cost_usd")),
            usage={"predict_time_seconds": metrics.get("predict_time"), "outputs": len(payloads),
                   "provider_status": prediction.get("status")},
            evidence={"adapter": "PredictionImageProvider", "provider_task_id": handle.provider_task_id,
                      "commercial_use": self.config.commercial_use},
            payloads=tuple(payloads),
        )

    def cancel(self, handle: ProviderTaskHandle) -> None:
        self._json("POST", self._task_url(handle.provider_task_id) + "/cancel")
        self._predictions.pop(handle.provider_task_id, None)


# --------------------------------------------------------------------------
# Readiness + build-stage wiring
# --------------------------------------------------------------------------

def image_provider_readiness(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    config = ImageProviderConfig.from_env(os.environ if env is None else env)
    status, reason = config.status()
    return {
        "capability_key": CAPABILITY_KEY,
        "provider": config.name if config.base_url else None,
        "status": status,
        "reason": reason,
        "commercial_use": config.commercial_use,
        "optional_media": {key: "NOT_CONFIGURED" for key in OPTIONAL_MEDIA_KEYS},
        "truth_note": "Configuration is at most PARTIAL; LIVE needs a real generated, verified artifact.",
    }


def build_image_provider(env: Mapping[str, str] | None = None, *, journal, urlopen=None, fetcher=None):
    env = os.environ if env is None else env
    config = ImageProviderConfig.from_env(env)
    if config.status()[0] != "PARTIAL":
        return None

    def resolve(reference: str) -> str:
        if reference.startswith("env:"):
            value = _clean(env, reference[4:])
            if not value:
                raise RuntimeError("image provider key not configured")
            return value
        from ..secrets_manager import VaultHttpConfig, VaultHttpSecretResolver
        base = _clean(env, "OMNI_VAULT_ADDR")
        if not base:
            raise RuntimeError("vault reference used but OMNI_VAULT_ADDR is not configured")
        return VaultHttpSecretResolver(VaultHttpConfig(base_url=base)).resolve(reference)

    return PredictionImageProvider(config=config, resolve_reference=resolve, journal=journal, urlopen=urlopen,
                                   fetcher=fetcher)


def build_image_capability_stage(*, env: Mapping[str, str] | None, repository, artifact_store, journal,
                                 worker_id: str, urlopen=None, fetcher=None):
    """DurableCapabilityBuildStage with the configured image provider (or none)."""
    from ..capability_executor import CapabilityExecutor
    from ..capability_worker import DurableCapabilityBuildStage
    from ..provider_registry import ProviderRegistry

    provider = build_image_provider(env, journal=journal, urlopen=urlopen, fetcher=fetcher)
    if provider is None:
        return DurableCapabilityBuildStage(repository=repository, assignments_resolver=lambda plan: {})
    registry = ProviderRegistry([provider])
    executor = None
    if artifact_store is not None:
        executor = CapabilityExecutor(provider_registry=registry, repository=repository,
                                      artifact_store=artifact_store, worker_id=worker_id)
    return DurableCapabilityBuildStage(repository=repository, executor=executor,
                                       assignments_resolver=capability_assignments_resolver(registry))


def build_image_quote_resolver(env: Mapping[str, str] | None = None):
    """Pricing-only resolver for the API process: identical routing to the
    worker stage, no journal writes, no network calls."""
    from ..provider_registry import ProviderRegistry

    provider = build_image_provider(env, journal=MemorySubmissionJournal())
    if provider is None:
        return lambda plan: {}
    return capability_assignments_resolver(ProviderRegistry([provider]))


def capability_assignments_resolver(registry):
    """Shared by pricing (API) and execution (worker) so they can never diverge."""
    from ..capability_executor import CapabilityExecutionAssignment
    from ..provider_router import CapabilityProviderRouter, CapabilityRoutingPolicy, ProviderCandidate

    router = CapabilityProviderRouter()

    def resolve(plan) -> dict:
        assignments = {}
        for requirement in plan.requirements:
            candidates = []
            for candidate_provider in registry.providers_for(requirement.key):
                capability = next(c for c in candidate_provider.capabilities() if c.capability_key == requirement.key)
                candidates.append(ProviderCandidate(
                    provider=candidate_provider.name, quality=50, latency_ms=0,
                    quote=candidate_provider.quote(requirement), health=candidate_provider.health(),
                    output_formats=capability.output_formats, commercial_use=capability.commercial_use))
            if not candidates:
                continue
            try:
                selection = router.select(requirement=requirement, candidates=candidates,
                                          policy=CapabilityRoutingPolicy(require_commercial_use=True))
            except LookupError:
                continue  # e.g. provider not cleared for commercial use: stays NOT_CONFIGURED
            assignments[requirement.id] = CapabilityExecutionAssignment(
                provider=selection.candidate.provider, quote=selection.candidate.quote)
        return assignments

    return resolve
