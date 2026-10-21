"""T3, Matt on #105: a rejected model answer is DURABLE evidence of the build, not only memory.

The real worker sink (install_rejected_json_sink) writes the full raw answer to the build's object store at the moment
it is rejected; the build evidence (rejected_json_evidence) carries the manifest with the key and the raw sha256. A store
failure is recorded on the entry, never silent.
"""
import hashlib
import json
import unittest
from decimal import Decimal
from types import SimpleNamespace

from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway
from omni_prod.worker_tasks import install_rejected_json_sink, rejected_json_evidence
from tests.test_t3_json_no_silent_trailing import gateway as answering

RAW = '{"files": [{"path": "app.py", "content": "x"}]}\n\nI also changed config.py, see above.'


class Store:
    def __init__(self, fail=False):
        self.objects, self.fail = {}, fail

    def put_bytes(self, key, data):
        if self.fail:
            raise OSError('r2 down')
        self.objects[key] = data
        return SimpleNamespace(key=key)


def routed(content):
    ep = ModelEndpoint(name='m', base_url='https://x.invalid', model='m', api_key='k', external=False)
    return RoutedModelGateway(primary=ProviderRoute(ep), policy=ModelUsePolicy(
        zero_cost_mode=True, allow_external_fallback=False, external_budget_usd=Decimal('0'),
        max_external_calls_per_build=0), gateway_factory=lambda endpoint: answering(content))


class RejectedJsonIsDurable(unittest.TestCase):
    def test_the_full_raw_answer_is_in_the_build_store_and_in_the_evidence(self):
        gw, store = routed(RAW), Store()
        install_rejected_json_sink(gw, SimpleNamespace(storage=store), 'bld_1')
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', task='codegen')
        [(key, data)] = store.objects.items()
        self.assertTrue(key.startswith('build-model-json/bld_1/00-codegen-'))
        stored = json.loads(data)
        self.assertEqual(stored['stored_text'], RAW)                               # the whole answer, not a cut
        self.assertEqual((stored['build_id'], stored['stored_truncated'], stored['stored_redacted']), ('bld_1', False, False))
        self.assertIsInstance(stored['attempt_seq'], int)
        self.assertIn('content after the first JSON value', stored['diagnostic']['reason'])
        ev = rejected_json_evidence(gw)
        self.assertTrue(ev['rejected_model_json_durable'])
        [row] = ev['rejected_model_json']
        self.assertEqual((row['key'], row['task'], row['raw_chars']), (key, 'codegen', len(RAW)))
        self.assertEqual(row['raw_sha256'], hashlib.sha256(RAW.encode()).hexdigest())
        self.assertNotIn('raw', row)                                               # the row stays small
        json.dumps(ev)                                                              # storable in evidence_json

    def test_it_is_retrievable_after_the_gateway_is_gone(self):
        store = Store()
        gw = routed(RAW)
        install_rejected_json_sink(gw, SimpleNamespace(storage=store), 'bld_9')
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', task='codegen')
        evidence = json.loads(json.dumps(rejected_json_evidence(gw)))             # what is written to evidence_json
        del gw                                                                       # the worker's objects are gone
        [row] = evidence['rejected_model_json']
        stored = json.loads(store.objects[row['key']])                              # retrieved by the evidence key
        self.assertEqual(hashlib.sha256(stored['stored_text'].encode()).hexdigest(), row['raw_sha256'])
        self.assertEqual(stored['attempt_seq'], row['attempt_seq'])

    def test_a_key_shaped_secret_is_redacted_in_the_store_and_says_so(self):
        leaky = '{"files": []}\nkey=AIza' + 'x' * 30
        gw, store = routed(leaky), Store()
        install_rejected_json_sink(gw, SimpleNamespace(storage=store), 'bld_1')
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', task='codegen')
        stored = json.loads(next(iter(store.objects.values())))
        self.assertNotIn('AIza' + 'x' * 30, stored['stored_text'])
        self.assertTrue(stored['stored_redacted'])
        self.assertEqual(stored['raw_sha256'], hashlib.sha256(leaky.encode()).hexdigest())   # digest of the original

    def test_every_rejection_is_kept_not_only_the_last_ten(self):
        gw, store = routed(RAW), Store()
        install_rejected_json_sink(gw, SimpleNamespace(storage=store), 'bld_1')
        for _ in range(12):
            with self.assertRaises(ModelGatewayError):
                gw.complete_json(system='s', user='u', task='repair')
        self.assertEqual(len(store.objects), 12)
        self.assertEqual(len(rejected_json_evidence(gw)['rejected_model_json']), 12)

    def test_a_store_failure_is_recorded_not_silent(self):
        gw = routed(RAW)
        install_rejected_json_sink(gw, SimpleNamespace(storage=Store(fail=True)), 'bld_1')
        with self.assertRaises(ModelGatewayError):                                 # the call still fails as JSON
            gw.complete_json(system='s', user='u', task='codegen')
        [row] = rejected_json_evidence(gw)['rejected_model_json']
        self.assertIsNone(row['key'])
        self.assertIn('OSError: r2 down', row['store_error'])

    def test_without_storage_the_evidence_says_it_is_not_durable(self):
        gw = routed(RAW)
        install_rejected_json_sink(gw, SimpleNamespace(storage=None), 'bld_1')
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', task='codegen')
        ev = rejected_json_evidence(gw)
        self.assertFalse(ev['rejected_model_json_durable'])
        self.assertEqual(len(ev['rejected_model_json']), 1)


if __name__ == '__main__':
    unittest.main()
