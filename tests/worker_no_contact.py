"""Execute the production worker + engine + routed gateway, with HTTP observation.

Control-plane jobs/workspace use the existing harness. The caller can supply a
real PostgreSQL subscription service. No network/provider service is contacted.
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from omni_prod import investor_app
from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway, ModelGatewayError
from omni_prod.model_policy import ModelPolicyViolation, ModelUsePolicy
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway
from tests.m5_worker_harness import ContractBuildHarness


def observed_gateway(*, allowed=False):
    def blocked_http(*args, **kwargs):
        raise ModelGatewayError('observed HTTP boundary; network intentionally disabled')
    http = MagicMock(side_effect=blocked_http)
    endpoint = ModelEndpoint('audit-provider', 'https://invalid.example', 'audit-model',
                             api_key='synthetic-test-key', external=True)
    policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                            external_budget_usd=Decimal('0.01'), max_external_calls_per_build=1) \
        if allowed else ModelUsePolicy()
    gateway = RoutedModelGateway(
        fallback=(ProviderRoute(endpoint, Decimal('0.01'), declared_quality=95),),
        policy=policy, transient_retries=0,
        gateway_factory=lambda ep: OpenAICompatibleGateway(ep, urlopen=http))
    return gateway, http


def failed_worker_without_contact(*, subscriptions, build_id):
    gateway, http = observed_gateway()
    with patch.object(investor_app, '_model_gateway_and_executor', return_value=(gateway, MagicMock())):
        engine, _ = investor_app._live_components()  # real architect/generator/repair agents
    harness = ContractBuildHarness(gateway=gateway)
    harness.engine = engine
    harness.platform.subscriptions = subscriptions
    harness.jobs.request['economics_quote'] = {'infrastructure_maximum_usd': '0.25'}
    from omni_prod.worker_tasks import _run_live_build_job
    try:
        _run_live_build_job(build_id, jobs=harness.jobs, platform=harness.platform,
                            workspace=harness.workspace, components_factory=harness.factory,
                            quality_fn=lambda **kw: harness.quality, security_fn=lambda repo: harness.security)
    except ModelPolicyViolation:
        pass
    else:
        raise AssertionError('the real model policy did not fail the build')
    return gateway, http, harness.final
