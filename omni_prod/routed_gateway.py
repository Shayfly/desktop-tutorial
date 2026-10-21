from __future__ import annotations
import json
import dataclasses
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Any
import time

from .model_gateway import (ModelEndpoint, OpenAICompatibleGateway, ModelGatewayError, ModelHTTPError,
                            ProviderQuotaUnavailable, quota_exhausted, provider_quota_depleted)
from .model_policy import ModelUsePolicy, ModelUseState, authorize_model_call
from .provider_usage import ProviderUsageLedger
from .model_router import RoutingPolicy, estimated_cost
from .attempt_ledger import AttemptLedgerUnavailable, AttemptRecord, AttemptRecorder, content_version, metered_cost
import os


@dataclass(frozen=True)
class ProviderRoute:
    endpoint: ModelEndpoint
    max_estimated_cost_usd: Decimal = Decimal('0')

    def __post_init__(self):
        if self.max_estimated_cost_usd < 0:
            raise ValueError('max_estimated_cost_usd cannot be negative')


@dataclass(frozen=True)
class RouteEvent:
    provider: str
    external: bool
    ok: bool
    elapsed_ms: int
    error: str = ''
    request_id: str | None = None
    # Routing-decision evidence (strings so build evidence stays JSON-safe).
    model: str = ''
    call: str = ''
    max_estimated_cost_usd: str = ''
    reason: str = ''


class RoutedModelGateway:
    """OpenAI-compatible model gateway: local primary and/or priced catalog routes.

    External routes are never used unless ModelUsePolicy explicitly permits them
    and the conservative per-call cost cap fits the build budget. Every call is
    recorded as an AttemptRecord (task, candidates, selection reason, versions,
    authorized / metered / provider-reported cost).
    """

    accepts_task_tag = True

    def __init__(
        self,
        *,
        primary: ProviderRoute | None = None,
        fallback: tuple[ProviderRoute, ...] = (),
        ranked: tuple = (),
        routing_policy: RoutingPolicy | None = None,
        policy: ModelUsePolicy | None = None,
        state: ModelUseState | None = None,
        gateway_factory: Callable[[ModelEndpoint], Any] = OpenAICompatibleGateway,
        on_event: Callable[[RouteEvent], None] | None = None,
        recorder: AttemptRecorder | None = None,
        transient_retries: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        health=None,
    ):
        if primary is not None and primary.endpoint.external:
            raise ValueError('primary route must be local/self-hosted')
        # ranked: CatalogModel entries (omni_prod.model_catalog). Only configured
        # entries are routable; order is chosen per call by price and quality.
        self.ranked = tuple(m for m in ranked if getattr(m, 'endpoint', None) is not None)
        # Diagnostics only (rehearsal per provider): restrict routing to the
        # named catalog entries. Unset in the worker's normal environment.
        only = {n.strip() for n in os.getenv('OMNI_MODEL_ONLY', '').split(',') if n.strip()}
        if only:
            self.ranked = tuple(m for m in self.ranked if m.endpoint.name in only)
        # Autonomous completion §19: DEV_ONLY / BLOCKED models never take work.
        from .agent_os.providers import filter_routable
        self.ranked = filter_routable(self.ranked)
        self.routing_policy = routing_policy or RoutingPolicy()
        if primary is None and not self.ranked and not fallback:
            raise ValueError('no model route is configured')
        self.primary = primary
        self.fallback = fallback
        self.policy = policy or ModelUsePolicy()
        self.state = state or ModelUseState()
        self.gateway_factory = gateway_factory
        self.on_event = on_event
        # Bounded retries of the SAME route on provider overload (HTTP 429/5xx)
        # before escalating to the next route: each retry is a separate,
        # recorded and budget-checked attempt.
        self.transient_retries = (int(os.getenv('OMNI_MODEL_TRANSIENT_RETRIES', '2'))
                                  if transient_retries is None else int(transient_retries))
        if self.transient_retries < 0:
            raise ValueError('transient_retries cannot be negative')
        self.retry_delays = (2.0, 6.0, 12.0)
        self.max_retry_delay = 20.0
        self.sleep = sleep
        self.events: list[RouteEvent] = []
        # Routes that answered "quota spent" / "key rejected": skipped for the
        # rest of this gateway's life (one build or modification).
        self.unavailable: dict[str, str] = {}
        self.depleted_routes: set[str] = set()  # Named, provider-confirmed quota/credit failures.
        # Wave A: durable provider health (intelligence.health). Without a
        # store it is per-gateway memory, i.e. the previous behaviour.
        from .intelligence.health import HealthBook
        self.health = health if health is not None else HealthBook()
        # Which catalog routes served which task in this build, so the QA
        # reviewer can prefer a model other than the one that wrote the code.
        self.models_by_task: dict[str, set[str]] = {}
        # T3: every rejected JSON answer, raw and diagnosed (bounded: the last 10, each up to 200k characters).
        self.rejected_json: list[dict] = []
        self.rejected_json_manifest: list[dict] = []   # every rejection of the build (no raw text): the evidence row
        # M5 Task 8: provider-reported usage for every attempt that got a response.
        self.usage = ProviderUsageLedger()
        self.recorder = recorder or AttemptRecorder()
        catalog_public = [m.to_public_dict() for m in ranked if hasattr(m, 'to_public_dict')]
        self.price_catalog_version = content_version(catalog_public) if catalog_public else None
        p = self.policy
        self.policy_version = content_version('model-use', p.zero_cost_mode, p.allow_external_fallback,
                                              str(p.external_budget_usd), p.max_external_calls_per_build)
        rp = self.routing_policy
        self.routing_policy_version = (os.getenv('OMNI_ROUTING_POLICY_VERSION', '').strip() or
                                       content_version('routing', rp.minimum_quality, rp.maximum_latency_ms,
                                                       rp.prefer_cost, self.price_catalog_version,
                                                       None if primary is None else primary.endpoint.name,
                                                       [r.endpoint.name for r in fallback]))

    def restrict_to_cost_class(self, cost_class) -> dict:
        """CEO 2026-10-19: a build may route only to models its class admits
        (pricing.M5_CLASS_MAX_OUTPUT_PER_MILLION). Narrows, never widens, the
        catalog; an empty result leaves no external route (fail closed)."""
        from .pricing import m5_model_allowed
        before = [m.endpoint.name for m in self.ranked]
        self.ranked = tuple(m for m in self.ranked if m5_model_allowed(cost_class, m.option.output_per_million))
        kept = [m.endpoint.name for m in self.ranked]
        return {'cost_class': getattr(cost_class, 'value', str(cost_class)), 'allowed_models': kept,
                'excluded_models': [n for n in before if n not in kept]}

    def bind_budget(self, ceiling_usd: Decimal) -> dict:
        """Set the whole-build external budget to what was reserved for this
        build at admission (CEO 2026-10-19: the build's class budget decides).

        The reservation is the durable, margin-checked authorization, so it is
        the effective budget in both directions:
        * worker env above it  -> lowered to the reservation (as before);
        * worker env below it  -> raised to the reservation, with a WARNING
          (WORKER_BUDGET_BELOW_CLASS) instead of silently starving the tier.
        Kill switches are unaffected: zero_cost_mode, allow_external_fallback
        and the per-build call limit still apply (model_policy.authorize_model_call)."""
        ceiling = Decimal(str(ceiling_usd))
        if ceiling < 0:
            raise ValueError('budget ceiling cannot be negative')
        before = self.policy.external_budget_usd
        effective = ceiling
        env_below = before < ceiling
        if env_below:
            import logging
            logging.getLogger(__name__).warning(
                'WORKER_BUDGET_BELOW_CLASS worker OMNI_EXTERNAL_BUDGET_USD=%s < reserved class budget=%s; '
                'using the reserved budget', before, ceiling)
        if effective != before:
            self.policy = dataclasses.replace(self.policy, external_budget_usd=effective)
            p = self.policy
            self.policy_version = content_version('model-use', p.zero_cost_mode, p.allow_external_fallback,
                                                  str(p.external_budget_usd), p.max_external_calls_per_build)
        return {'worker_env_budget_usd': str(before), 'reserved_llm_usd': str(ceiling),
                'effective_budget_usd': str(effective), 'worker_env_below_reservation': env_below,
                'policy_version': self.policy_version}

    @property
    def last_usage(self):
        return self.usage.last

    def _record(self, event: RouteEvent) -> None:
        self.events.append(event)
        if self.on_event:
            self.on_event(event)

    @staticmethod
    def _outcome_of(exc: BaseException) -> str:
        """'unknown' when the request may have reached the provider without an answer."""
        seen = exc
        for _ in range(5):
            if seen is None:
                break
            if isinstance(seen, TimeoutError) or 'timed out' in str(seen).lower():
                return 'unknown'
            seen = seen.__cause__ or seen.__context__
        return 'error'

    def _attempt(self, route: ProviderRoute, method: str, kwargs: dict, reason: str = '', *,
                 task: str = 'general', option=None, rank: int | None = None, candidate_set=None):
        authorize_model_call(
            endpoint=route.endpoint,
            policy=self.policy,
            state=self.state,
            estimated_cost_usd=route.max_estimated_cost_usd,
        )
        started = time.monotonic()
        gateway = None
        record = AttemptRecord(
            task_type=task or 'general', attempt_seq=self.recorder.next_seq(), kind='provider_call',
            outcome='unknown', provider=route.endpoint.name, model=route.endpoint.model,
            policy_version=self.policy_version, routing_policy_version=self.routing_policy_version,
            prompt_version=content_version('prompt', kwargs.get('system', '')),
            price_catalog_version=self.price_catalog_version if option is not None else None,
            selection_reason=reason, selected_candidate=route.endpoint.name, candidate_set=candidate_set,
            fallback_rank=rank, authorized_cost_usd=route.max_estimated_cost_usd)
        # Write-ahead: the attempt exists (outcome 'unknown', authorized worst
        # case) before the provider is contacted, and is flushed to the ledger.
        self.recorder.add(record)
        if self.on_attempt_start is not None:
            try:
                self.on_attempt_start()
            except Exception as exc:
                # No provider was contacted. Undo only this admission and stop
                # every fallback rather than spending without financial proof.
                if route.endpoint.external:
                    self.state.external_calls -= 1
                    self.state.external_spend_usd -= route.max_estimated_cost_usd
                record.outcome = 'error'
                record.metered_cost_usd = Decimal('0')
                record.failure_reason = 'attempt ledger unavailable before provider dispatch'
                raise AttemptLedgerUnavailable(record.failure_reason) from exc
        try:
            gateway = self.gateway_factory(route.endpoint)
            value = getattr(gateway, method)(**kwargs)
        except Exception as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            usage = getattr(gateway, 'last_usage', None) if gateway is not None else None
            self.usage.record(usage)
            self._fill(record, gateway, usage, option, elapsed)
            self._settle(route, record)
            if usage is None and isinstance(exc, ModelHTTPError):
                self._release_rejected(route, record)
            record.outcome = 'error' if usage is not None else self._outcome_of(exc)
            record.failure_reason = f'{type(exc).__name__}: {exc}'[:500]
            if hasattr(exc, 'raw') and hasattr(exc, 'diagnostic'):          # ModelJSONRejected: keep what was said
                import hashlib
                raw = exc.raw or ''
                entry = {'model': route.endpoint.name, 'provider_model': route.endpoint.model,
                         'attempt_seq': record.attempt_seq, 'task': task or 'general', 'diagnostic': dict(exc.diagnostic),
                         'raw_sha256': hashlib.sha256(raw.encode('utf-8', 'replace')).hexdigest(),
                         'raw_chars': len(raw), 'raw': raw[:200_000], 'raw_truncated': len(raw) > 200_000}
                # Matt on #105: memory is not evidence. A durable sink (the worker: object storage, per build) gets
                # the FULL raw answer at the moment it is rejected, so it survives the build crashing later.
                sink = getattr(self, 'rejected_json_sink', None)
                if sink is not None:
                    try:
                        entry['key'] = sink(entry, raw)
                    except Exception as sink_exc:            # recorded, never silent: the evidence is then NOT durable
                        entry['store_error'] = f'{type(sink_exc).__name__}: {sink_exc}'[:300]
                self.rejected_json = (self.rejected_json + [entry])[-10:]
                self.rejected_json_manifest.append({k: v for k, v in entry.items() if k != 'raw'})   # all, without raw
            self._record(RouteEvent(route.endpoint.name, route.endpoint.external, False, elapsed, str(exc)[:300],
                                    request_id=getattr(usage, 'request_id', None), **self._decision(route, method, reason)))
            if isinstance(exc, ModelGatewayError):
                raise
            raise ModelGatewayError(f'{route.endpoint.name} failed: {exc}') from exc
        elapsed = int((time.monotonic() - started) * 1000)
        usage = getattr(gateway, 'last_usage', None)
        self.usage.record(usage)
        self._fill(record, gateway, usage, option, elapsed)
        self._settle(route, record)
        record.outcome = 'ok'
        if route.endpoint.external:
            self.health.record_success(route.endpoint.name)
        self.models_by_task.setdefault(task or 'general', set()).add(route.endpoint.name)
        self._record(RouteEvent(route.endpoint.name, route.endpoint.external, True, elapsed,
                                request_id=getattr(usage, 'request_id', None), **self._decision(route, method, reason)))
        return value

    def _settle(self, route: ProviderRoute, record: AttemptRecord) -> None:
        """Lower this call's reservation to its metered cost.

        Rehearsal 2026-10-08: each call reserved its worst case (max_tokens
        output) and never gave the difference back, so a build that preferred
        the stronger model hit 'external model budget exceeded' after 13 calls.
        When the provider reported tokens, the authorization becomes usage x
        catalog price; without reported usage the worst case stays reserved.
        """
        metered = record.metered_cost_usd
        if not route.endpoint.external or metered is None:
            return
        release = route.max_estimated_cost_usd - metered
        if release > 0:
            self.state.external_spend_usd -= release

    def _release_rejected(self, route: ProviderRoute, record: AttemptRecord) -> None:
        """The provider answered with an HTTP error status: the request was
        refused, not served, and no tokens are billed. Return its whole
        reservation. bld_ccd38bd0 (2026-10-08): ten ~250 ms HTTP 429 quota
        answers each kept a $0.045-0.050 worst case, so the ledger showed
        $0.47 "spent" (provider cost $0) and the build stopped on budget.
        Timeouts and dropped connections are NOT released: those requests may
        have been served and billed."""
        if not route.endpoint.external:
            return
        self.state.external_spend_usd -= route.max_estimated_cost_usd
        if self.state.external_spend_usd < 0:
            self.state.external_spend_usd = Decimal('0')
        record.metered_cost_usd = Decimal('0')

    @staticmethod
    def _fill(record: AttemptRecord, gateway, usage, option, elapsed: int) -> None:
        record.latency_ms = elapsed
        record.model_version = getattr(gateway, 'last_response_model', None) if gateway is not None else None
        if usage is not None:
            record.provider_request_id = usage.request_id or usage.response_id
            record.input_tokens = usage.input_tokens
            record.output_tokens = usage.output_tokens
            record.cached_tokens = usage.cached_tokens
            record.provider_reported_cost_usd = usage.provider_reported_cost_usd
            record.metered_cost_usd = metered_cost(option, usage.input_tokens, usage.output_tokens)

    @staticmethod
    def _decision(route: ProviderRoute, method: str, reason: str) -> dict:
        return {'model': route.endpoint.model, 'call': method,
                'max_estimated_cost_usd': str(route.max_estimated_cost_usd), 'reason': reason}

    def task_quality_floor(self, task: str) -> int:
        """Minimum model quality preferred for a task type.

        Rehearsal 2026-10-08: with cost-first routing every call, including
        code generation and repair, went to the cheapest Flash-Lite model, and
        repair rounds oscillated (Flask, then `requests`, then a 116-character
        page). Writing and repairing code prefers the stronger model; cheaper
        models stay available as escalation when it is unavailable.
        OMNI_MODEL_TASK_MIN_QUALITY (JSON object) overrides the defaults.
        """
        from .intelligence.task_policy import TASK_CLASSES
        floors = {k: t.preferred_floor for k, t in TASK_CLASSES.items()}
        raw = os.getenv('OMNI_MODEL_TASK_MIN_QUALITY', '').strip()
        if raw:
            try:
                floors.update({str(k): int(v) for k, v in json.loads(raw).items()})
            except (ValueError, AttributeError, TypeError):
                pass
        return max(self.routing_policy.minimum_quality, floors.get(task, floors['general']))

    def ranked_routes(self, kwargs: dict, task: str = 'general') -> list[tuple]:
        """Cheapest eligible catalog model first, with a conservative per-call cap.

        Input tokens are bounded by the UTF-8 byte length of the prompt (a token
        is never shorter than one byte), output by the requested max_tokens
        clamped to the model limit, so the authorized maximum is never below the
        real billable amount of a successful call.

        Returns (route, call_kwargs, option) tuples in selection order.
        """
        text = f"{kwargs.get('system', '')}{kwargs.get('user', '')}"
        input_tokens = len(text.encode('utf-8')) + 64
        requested = int(kwargs.get('max_tokens', 4096))
        policy = self.routing_policy
        candidates = []
        for model in self.ranked:
            option = model.option
            if not option.enabled or option.quality < policy.minimum_quality:
                continue
            # Wave A: below the task's MANDATORY floor a model is never used
            # for it, not even as escalation (no silent downgrade).
            from .intelligence.task_policy import eligible
            if not eligible(task, model_id=option.model, quality=option.quality):
                continue
            if policy.maximum_latency_ms is not None and option.latency_ms > policy.maximum_latency_ms:
                continue
            out_tokens = min(requested, model.max_output_tokens)
            cost = estimated_cost(option, input_tokens=input_tokens, output_tokens=out_tokens)
            order = ((cost, -option.quality, option.latency_ms, model.endpoint.name)
                     if policy.prefer_cost else (-option.quality, cost, option.latency_ms, model.endpoint.name))
            candidates.append((order, ProviderRoute(model.endpoint, cost), {**kwargs, 'max_tokens': out_tokens}, option))
        floor = self.task_quality_floor(task)
        # Agent OS spec §4: the reviewer is not the author. Among models that
        # meet the floor, prefer one that did not write or repair the code.
        authors = set()
        if task == 'review':
            for t in ('codegen', 'repair', 'modification'):
                authors |= self.models_by_task.get(t, set())
        # Models meeting the task's floor first (cheapest among them), then the
        # rest as escalation; the base minimum_quality filter above still holds.
        candidates.sort(key=lambda c: (c[3].quality < floor, c[1].endpoint.name in authors, c[0]))
        return [(route, kw, option) for _, route, kw, option in candidates]

    # Smallest output allowance still useful per task: below it a response is
    # likely truncated and the call is wasted.
    MIN_FITTED_OUTPUT = {'codegen': 12000, 'repair': 6000, 'modification': 6000}

    def fit_to_budget(self, route: ProviderRoute, call_kwargs: dict, option, task: str):
        """A model at or above the task's quality floor whose worst case does
        not fit the remaining budget gets one more try with the largest output
        allowance that does fit (never below MIN_FITTED_OUTPUT), instead of
        dropping straight to a weaker model.

        Paid build bld_e2698426 (2026-10-09): with $0.09 left after code
        generation, the strong model's 20k-token repair reservation ($0.11) did
        not fit, every repair went to Flash-Lite (8k output), and five rounds
        oscillated without converging. Real repair responses were 1-3k tokens.
        Returns (route, kwargs) or None. The cut call is still authorized
        against the budget like any other."""
        minimum = self.MIN_FITTED_OUTPUT.get(task)
        if option is None or minimum is None or option.quality < self.task_quality_floor(task):
            return None
        current = int(call_kwargs.get('max_tokens', 0))
        text = f"{call_kwargs.get('system', '')}{call_kwargs.get('user', '')}"
        input_tokens = len(text.encode('utf-8')) + 64
        remaining = self.policy.external_budget_usd - self.state.external_spend_usd
        out_price = Decimal(str(option.output_per_million)) / Decimal(1_000_000)
        if out_price <= 0:
            return None
        input_cost = estimated_cost(option, input_tokens=input_tokens, output_tokens=0)
        allowance = int(((remaining - input_cost) / out_price) * Decimal('0.98'))
        if allowance < minimum or allowance >= current:
            return None
        cost = estimated_cost(option, input_tokens=input_tokens, output_tokens=allowance)
        return ProviderRoute(route.endpoint, cost), {**call_kwargs, 'max_tokens': allowance}

    # Directive 2026-10-09 §10: a build's stop/live-log hook (BuildControl).
    # Runs before any provider is contacted; raising here costs nothing.
    before_call: Callable[[str], None] | None = None
    # Called after a provider attempt is written ahead (worker: flush the ledger).
    on_attempt_start: Callable[[], None] | None = None

    def _route(self, method: str, kwargs: dict, task: str = 'general'):
        if self.before_call is not None:
            self.before_call(task)
        last_error: Exception | None = None
        routes = []
        if self.primary is not None:
            routes.append((self.primary, kwargs, 'local primary', None))
        basis = 'cheapest' if self.routing_policy.prefer_cost else 'highest quality'
        floor = self.task_quality_floor(task)
        for rank, (route, call_kwargs, option) in enumerate(self.ranked_routes(kwargs, task)):
            why = (f'{basis} eligible catalog model for {task} (quality>={floor})' if rank == 0
                   else f'catalog escalation #{rank} after earlier route failed')
            routes.append((route, call_kwargs, why, option))
        routes.extend((route, kwargs, 'configured fallback', None) for route in self.fallback)
        if not routes:
            raise ModelGatewayError('no eligible model route for this request')
        candidate_set = [{'name': r.endpoint.name, 'model': r.endpoint.model,
                          'max_cost_usd': str(r.max_estimated_cost_usd)} for r, _, _, _ in routes]
        from .model_policy import ModelPolicyViolation
        failures = []
        budget_skips = 0
        for rank, (route, call_kwargs, why, option) in enumerate(routes):
            name = route.endpoint.name
            if name in self.unavailable:
                failures.append(f'{route.endpoint.model}: skipped ({self.unavailable[name]})')
                continue
            if route.endpoint.external:
                admitted, why_not = self.health.admit(name)
                if not admitted:
                    self.unavailable[name] = why_not
                    failures.append(f'{route.endpoint.model}: skipped (provider health: {why_not})')
                    self._record(RouteEvent(name, True, False, 0, f'skipped: {why_not}'[:300],
                                            **self._decision(route, method, 'circuit open')))
                    continue
            for retry in range(self.transient_retries + 1):
                try:
                    return self._attempt(route, method, call_kwargs,
                                         why if retry == 0 else f'{why}; transient retry #{retry}',
                                         task=task, option=option, rank=rank, candidate_set=candidate_set)
                except Exception as exc:
                    last_error = exc
                    if isinstance(exc, AttemptLedgerUnavailable):
                        raise
                    if isinstance(exc, ModelPolicyViolation):
                        # A route whose worst case does not fit the remaining
                        # budget is passed over for a cheaper one that does (still
                        # authorized). Every other policy error stops the call
                        # rather than bypassing budget/zero-cost controls.
                        if 'budget exceeded' in str(exc):
                            fitted = self.fit_to_budget(route, call_kwargs, option, task)
                            if fitted is not None:
                                # Same model, smaller output allowance that fits: one attempt.
                                f_route, f_kwargs = fitted
                                try:
                                    return self._attempt(f_route, method, f_kwargs,
                                                         f'{why}; output allowance cut to {f_kwargs["max_tokens"]} tokens '
                                                         'to fit the remaining budget',
                                                         task=task, option=option, rank=rank, candidate_set=candidate_set)
                                except Exception as fitted_exc:
                                    last_error = fitted_exc
                                    if isinstance(fitted_exc, AttemptLedgerUnavailable):
                                        raise
                                    if isinstance(fitted_exc, ModelPolicyViolation) and 'budget exceeded' not in str(fitted_exc):
                                        raise
                                    if quota_exhausted(fitted_exc):
                                        self.unavailable[name] = f'HTTP {getattr(fitted_exc, "status", "?")}: quota or key'
                                        if provider_quota_depleted(fitted_exc):
                                            self.depleted_routes.add(name)
                                    failures.append(f'{route.endpoint.model} (fitted output): {fitted_exc}')
                                    break
                            budget_skips += 1
                            failures.append(f'{route.endpoint.model}: does not fit the remaining budget')
                            break
                        raise
                    if isinstance(exc, ModelHTTPError) and route.endpoint.external:
                        from .intelligence import states as HS
                        hs = self.health.classify(exc) if hasattr(self.health, 'classify') else None
                        if hs in (HS.CREDIT_EXHAUSTED, HS.AUTH_INVALID, HS.UNAVAILABLE) or quota_exhausted(exc) \
                                or (hs == HS.RATE_LIMITED and retry == self.transient_retries):
                            self.health.record_failure(name, exc)
                    if quota_exhausted(exc):
                        self.unavailable[name] = f'HTTP {getattr(exc, "status", "?")}: quota or key'
                        if provider_quota_depleted(exc):
                            self.depleted_routes.add(name)
                        failures.append(f'{route.endpoint.model}: {exc}')
                        break
                    transient = isinstance(exc, ModelHTTPError) and exc.transient
                    if not transient or retry == self.transient_retries:
                        failures.append(f'{route.endpoint.model}: {exc}')
                        break
                    # Every retry is its own recorded, budget-checked attempt.
                    hint = exc.retry_after_seconds
                    delay = self.retry_delays[min(retry, len(self.retry_delays) - 1)]
                    self.sleep(min(self.max_retry_delay, hint if hint is not None else delay))
        if budget_skips and all('remaining budget' in f or 'skipped' in f for f in failures):
            raise ModelPolicyViolation('external model budget exceeded')
        if self.depleted_routes:
            # This is emitted only when no route served the request. A quota
            # failure in one provider does NOT prevent a valid fallback.
            raise ProviderQuotaUnavailable(self.depleted_routes)
        detail = '; '.join(failures[-4:]) if failures else str(last_error)
        raise ModelGatewayError(f'all model routes failed: {detail}')

    def complete(self, *, system: str, user: str, temperature: float = 0.1, max_tokens: int = 4096,
                 task: str = 'general') -> str:
        return self._route('complete', {
            'system': system,
            'user': user,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }, task)

    def complete_json(self, *, system: str, user: str, max_tokens: int = 4096, task: str = 'general') -> dict:
        return self._route('complete_json', {
            'system': system,
            'user': user,
            'max_tokens': max_tokens,
        }, task)
