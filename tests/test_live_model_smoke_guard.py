import unittest
from decimal import Decimal
from unittest import mock

from tools.live_model_smoke import (
    APPROVAL_ENV,
    MAX_TOTAL_SPEND_USD,
    configured_gateway,
    require_approval,
)
from omni_prod.model_runtime_config import ModelRuntimeConfig
from omni_prod.model_policy import ModelUsePolicy


class LiveModelSmokeGuardTests(unittest.TestCase):
    def test_call_requires_exact_explicit_approval(self):
        for value in (None, '', 'true', 'yes', '0'):
            with self.subTest(value=value):
                env = {} if value is None else {APPROVAL_ENV: value}
                with self.assertRaises(SystemExit):
                    require_approval(env)
        require_approval({APPROVAL_ENV: '1'})

    def test_gateway_enforces_one_call_and_quarter_dollar_total_cap(self):
        config = ModelRuntimeConfig(
            primary=None,
            fallback=(),
            policy=ModelUsePolicy(),
            catalog=(),
        )
        with mock.patch('tools.live_model_smoke.RoutedModelGateway') as gateway_type:
            configured_gateway(config)
        kwargs = gateway_type.call_args.kwargs
        policy = kwargs['policy']
        self.assertEqual(policy.external_budget_usd, Decimal('0.25'))
        self.assertEqual(policy.max_external_calls_per_build, 1)
        self.assertEqual(kwargs['transient_retries'], 0)

    def test_cap_is_fixed_not_environment_configurable(self):
        with mock.patch.dict('os.environ', {'OMNI_LIVE_MODEL_SMOKE_MAX_USD': '50'}, clear=False):
            self.assertEqual(MAX_TOTAL_SPEND_USD, Decimal('0.25'))


if __name__ == '__main__':
    unittest.main()
