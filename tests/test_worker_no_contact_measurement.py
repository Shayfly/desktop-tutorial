from unittest import TestCase
from unittest.mock import MagicMock
from omni_prod.model_gateway import ModelGatewayError
from tests.worker_no_contact import failed_worker_without_contact, observed_gateway


class WorkerNoContactMeasurementTests(TestCase):
    def test_real_worker_reads_counter_and_http_observer(self):
        subscriptions = MagicMock()
        gateway, http, terminal = failed_worker_without_contact(subscriptions=subscriptions, build_id='measured')
        self.assertEqual(gateway.state.external_calls, 0)
        http.assert_not_called()
        self.assertEqual(terminal['target'].value, 'failed')
        self.assertEqual(terminal['error_code'], 'model_policy_blocked')
        self.assertEqual(terminal['evidence_json']['external_model_calls'], gateway.state.external_calls)
        subscriptions.release.assert_called_once_with(build_id='measured')
        subscriptions.settle.assert_not_called()

    def test_observation_is_live_when_a_call_is_allowed(self):
        gateway, http = observed_gateway(allowed=True)
        with self.assertRaises(ModelGatewayError):
            gateway.complete_json(system='audit', user='audit', max_tokens=10)
        self.assertEqual(gateway.state.external_calls, 1)
        self.assertEqual(http.call_count, 1)
