from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Any
import time

from .model_gateway import ModelEndpoint, OpenAICompatibleGateway, ModelGatewayError
from .model_policy import ModelUsePolicy, ModelUseState, authorize_model_call
from .provider_usage import ProviderUsageLedger
from .model_router import RoutingPolicy, estimated_cost


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


class RoutedModelGateway:
    """Local-first OpenAI-compatible model gateway with fail-closed paid fallback.

    The primary route is expected to be self-hosted/local. External routes are
    never used unless ModelUsePolicy explicitly permits them and the conservative
    per-call cost estimate fits the build budget.
    """

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

    @property
    def last_usage(self):
        return self.usage.last

    def _record(self, event: RouteEvent) -> None:
        self.events.append(event)
        if self.on_event:
            self.on_event(event)

    def _attempt(self, route: ProviderRoute, method: str, kwargs: dict):
        authorize_model_call(
            endpoint=route.endpoint,
            policy=self.policy,
            state=self.state,
            estimated_cost_usd=route.max_estimated_cost_usd,
        )
        started = time.monotonic()
        gateway = None
        try:
            gateway = self.gateway_factory(route.endpoint)
            value = getattr(gateway, method)(**kwargs)
        except Exception as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            usage = getattr(gateway, 'last_usage', None) if gateway is not None else None
            self.usage.record(usage)
            self._record(RouteEvent(route.endpoint.name, route.endpoint.external, False, elapsed, str(exc)[:300],
                                    request_id=getattr(usage, 'request_id', None)))
            if isinstance(exc, ModelGatewayError):
                raise
            raise ModelGatewayError(f'{route.endpoint.name} failed: {exc}') from exc
        elapsed = int((time.monotonic() - started) * 1000)
        usage = getattr(gateway, 'last_usage', None)
        self.usage.record(usage)
        self._record(RouteEvent(route.endpoint.name, route.endpoint.external, True, elapsed,
                                request_id=getattr(usage, 'request_id', None)))
        return value

    def ranked_routes(self, kwargs: dict) -> list[tuple[ProviderRoute, dict]]:
        """Cheapest eligible catalog model first, with a conservative per-call cap.

        Input tokens are bounded by the UTF-8 byte length of the prompt (a token
        is never shorter than one byte), output by the requested max_tokens
        clamped to the model limit, so the authorized maximum is never below the
        real billable amount of a successful call.
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
            candidates.append((order, ProviderRoute(model.endpoint, cost), {**kwargs, 'max_tokens': out_tokens}))
        candidates.sort(key=lambda c: c[0])
        return [(route, kw) for _, route, kw in candidates]

    def _route(self, method: str, kwargs: dict):
        last_error: Exception | None = None
        routes = []
        if self.primary is not None:
            routes.append((self.primary, kwargs))
        routes.extend(self.ranked_routes(kwargs))
        routes.extend((route, kwargs) for route in self.fallback)
        if not routes:
            raise ModelGatewayError('no eligible model route for this request')
        for route, call_kwargs in routes:
            try:
                return self._attempt(route, method, call_kwargs)
            except Exception as exc:
                last_error = exc
                # Policy errors intentionally stop the route rather than silently
                # bypassing budget/zero-cost controls.
                from .model_policy import ModelPolicyViolation
                if isinstance(exc, ModelPolicyViolation):
                    raise
                continue
        raise ModelGatewayError(f'all model routes failed: {last_error}')

    def complete(self, *, system: str, user: str, temperature: float = 0.1, max_tokens: int = 4096) -> str:
        return self._route('complete', {
            'system': system,
            'user': user,
            'temperature': temperature,
            'max_tokens': max_tokens,
        })

    def complete_json(self, *, system: str, user: str, max_tokens: int = 4096) -> dict:
        return self._route('complete_json', {
            'system': system,
            'user': user,
            'max_tokens': max_tokens,
        })
