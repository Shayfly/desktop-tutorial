"""Financial write-ahead failure must stop all paid routes before dispatch."""
from decimal import Decimal

import pytest

from omni_prod.build_control import BuildControl
from omni_prod.model_gateway import ModelEndpoint
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway


def test_failed_write_ahead_never_dispatches_or_falls_back():
    dispatched = []

    class Provider:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def complete(self, **kwargs):
            dispatched.append(self.endpoint.name)
            return 'served'

    gateway = RoutedModelGateway(
        fallback=tuple(ProviderRoute(ModelEndpoint(name, 'http://127.0.0.1:1/v1', 'fixture-model',
                                                  api_key='fixture-only', external=True), Decimal('0.05'),
                                     declared_quality=90)
                       for name in ('fixture-a', 'fixture-b')),
        gateway_factory=Provider,
        policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                              external_budget_usd=Decimal('1'), max_external_calls_per_build=10),
    )

    def unavailable():
        raise OSError('ledger write rejected')

    gateway.on_attempt_start = unavailable
    with pytest.raises(RuntimeError, match='ledger'):
        gateway.complete(system='fixture', user='fixture')
    assert dispatched == []
    assert gateway.state.external_calls == 0
    assert gateway.state.external_spend_usd == Decimal('0')


def test_control_propagates_financial_flush_failure():
    control = BuildControl(None, 'fixture-build')

    def unavailable():
        raise OSError('ledger write rejected')

    control.flush = unavailable
    with pytest.raises(OSError, match='ledger write rejected'):
        control.flush_attempts()
