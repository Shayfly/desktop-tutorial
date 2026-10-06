from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Any
import time

from .model_gateway import ModelEndpoint, OpenAICompatibleGateway, ModelGatewayError
from .model_policy import ModelUsePolicy, ModelUseState, authorize_model_call
from .provider_usage import ProviderUsageLedger
from .model_router import RoutingPolicy, estimated_cost
from .attempt_ledger import AttemptRecord, AttemptRecorder, content_version, metered_cost
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
    ):
        if primary is not None and primary.endpoint.external:
            raise ValueError('primary route must be local/self-hosted')
        # ranked: CatalogModel entries (omni_prod.model_catalog). Only configured
        # entries are routable; order is chosen per call by price and quality.
        self.ranked = tuple(m for m in ranked if getattr(m, 'endpoint', None) is not None)
        self.routing_policy = routing_policy or RoutingPolicy()
        if primary is None and not self.ranked and not fallback:
            raise ValueError('no model route is configured')
        self.primary = primary
        self.fallback = fallback
        self.policy = policy or ModelUsePolicy()
        self.state = state or ModelUseState()
        self.gateway_factory = gateway_factory
        self.on_event = on_event
        self.events: list[RouteEvent] = []
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
        try:
            gateway = self.gateway_factory(route.endpoint)
            value = getattr(gateway, method)(**kwargs)
        except Exception as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            usage = getattr(gateway, 'last_usage', None) if gateway is not None else None
            self.usage.record(usage)
            self._fill(record, gateway, usage, option, elapsed)
            record.outcome = 'error' if usage is not None else self._outcome_of(exc)
            record.failure_reason = f'{type(exc).__name__}: {exc}'[:500]
            self.recorder.add(record)
            self._record(RouteEvent(route.endpoint.name, route.endpoint.external, False, elapsed, str(exc)[:300],
                                    request_id=getattr(usage, 'request_id', None), **self._decision(route, method, reason)))
            if isinstance(exc, ModelGatewayError):
                raise
            raise ModelGatewayError(f'{route.endpoint.name} failed: {exc}') from exc
        elapsed = int((time.monotonic() - started) * 1000)
        usage = getattr(gateway, 'last_usage', None)
        self.usage.record(usage)
        self._fill(record, gateway, usage, option, elapsed)
        record.outcome = 'ok'
        self.recorder.add(record)
        self._record(RouteEvent(route.endpoint.name, route.endpoint.external, True, elapsed,
                                request_id=getattr(usage, 'request_id', None), **self._decision(route, method, reason)))
        return value

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

    def ranked_routes(self, kwargs: dict) -> list[tuple]:
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
            if policy.maximum_latency_ms is not None and option.latency_ms > policy.maximum_latency_ms:
                continue
            out_tokens = min(requested, model.max_output_tokens)
            cost = estimated_cost(option, input_tokens=input_tokens, output_tokens=out_tokens)
            order = ((cost, -option.quality, option.latency_ms, model.endpoint.name)
                     if policy.prefer_cost else (-option.quality, cost, option.latency_ms, model.endpoint.name))
            candidates.append((order, ProviderRoute(model.endpoint, cost), {**kwargs, 'max_tokens': out_tokens}, option))
        candidates.sort(key=lambda c: c[0])
        return [(route, kw, option) for _, route, kw, option in candidates]

    def _route(self, method: str, kwargs: dict, task: str = 'general'):
        last_error: Exception | None = None
        routes = []
        if self.primary is not None:
            routes.append((self.primary, kwargs, 'local primary', None))
        basis = 'cheapest' if self.routing_policy.prefer_cost else 'highest quality'
        for rank, (route, call_kwargs, option) in enumerate(self.ranked_routes(kwargs)):
            why = (f'{basis} eligible catalog model (quality>={self.routing_policy.minimum_quality})' if rank == 0
                   else f'catalog escalation #{rank} after earlier route failed')
            routes.append((route, call_kwargs, why, option))
        routes.extend((route, kwargs, 'configured fallback', None) for route in self.fallback)
        if not routes:
            raise ModelGatewayError('no eligible model route for this request')
        candidate_set = [{'name': r.endpoint.name, 'model': r.endpoint.model,
                          'max_cost_usd': str(r.max_estimated_cost_usd)} for r, _, _, _ in routes]
        for rank, (route, call_kwargs, why, option) in enumerate(routes):
            try:
                return self._attempt(route, method, call_kwargs, why, task=task, option=option,
                                     rank=rank, candidate_set=candidate_set)
            except Exception as exc:
                last_error = exc
                # Policy errors intentionally stop the route rather than silently
                # bypassing budget/zero-cost controls.
                from .model_policy import ModelPolicyViolation
                if isinstance(exc, ModelPolicyViolation):
                    raise
                continue
        raise ModelGatewayError(f'all model routes failed: {last_error}')

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
