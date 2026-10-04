from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Any
import time

from .model_gateway import ModelEndpoint, OpenAICompatibleGateway, ModelGatewayError
from .model_policy import ModelUsePolicy, ModelUseState, authorize_model_call
from .provider_usage import ProviderUsageLedger


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
        primary: ProviderRoute,
        fallback: tuple[ProviderRoute, ...] = (),
        policy: ModelUsePolicy | None = None,
        state: ModelUseState | None = None,
        gateway_factory: Callable[[ModelEndpoint], Any] = OpenAICompatibleGateway,
        on_event: Callable[[RouteEvent], None] | None = None,
    ):
        if primary.endpoint.external:
            raise ValueError('primary route must be local/self-hosted')
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

    def _route(self, method: str, kwargs: dict):
        last_error: Exception | None = None
        routes = (self.primary, *self.fallback)
        for route in routes:
            try:
                return self._attempt(route, method, kwargs)
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
