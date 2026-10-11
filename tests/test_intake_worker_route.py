"""Real-model intake routed through the worker -- TEST DOUBLES ONLY.

No provider is called here. These tests prove the wiring, the fail-closed
switches, the re-validation on the API side and the fallback; they are not
evidence of a live AI conversation."""
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.intake import worker_route as W


class _Gateway:
    def __init__(self, out):
        self.out, self.calls = out, []
        self.recorder = type('R', (), {'records': []})()
        self.last_usage = None

    def complete_json(self, **kw):
        self.calls.append(kw)
        if isinstance(self.out, Exception):
            raise self.out
        return self.out


class WorkerSideTests(unittest.TestCase):
    def test_disabled_without_flag_or_budget(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            self.assertFalse(W.execute('x', gateway_factory=lambda cap: _Gateway({}))['ok'])
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_CALL_BUDGET_USD': '0'}):
            self.assertIn('budget', W.execute('x', gateway_factory=lambda cap: _Gateway({}))['error'])

    def test_uses_the_conversation_task_class_within_the_cap(self):
        seen = {}
        def factory(cap):
            seen['cap'] = cap
            return gw
        gw = _Gateway({'language': 'en', 'product_family': 'web_app', 'proposals': []})
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.004'}):
            out = W.execute('a booking site', gateway_factory=factory)
        self.assertTrue(out['ok'])
        self.assertEqual(seen['cap'], Decimal('0.004'))
        self.assertEqual(gw.calls[0]['task'], 'conversation')
        self.assertEqual(gw.calls[0]['max_tokens'], 1200)

    def test_provider_error_is_reported_not_raised(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.004'}):
            out = W.execute('x', gateway_factory=lambda cap: _Gateway(RuntimeError('quota')))
        self.assertFalse(out['ok'])
        self.assertIn('quota', out['error'])


class ApiSideTests(unittest.TestCase):
    MSG = 'אני צריך אתר תורים בלי התחברות'

    def _interp(self, result, wait=1.0):
        clock = iter([0.0, 0.1, 0.2, 5.0, 9.0, 20.0])
        return W.WorkerInterpreter(lambda m: 'job1', lambda j: result, wait_seconds=wait, sleep=lambda s: None,
                                   clock=lambda: next(clock))

    def test_valid_model_result_is_revalidated_and_merged(self):
        raw = {'language': 'he', 'product_family': 'web_app', 'proposals': [
            {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'},
            {'field': 'color', 'value': 'green', 'confidence': 'high', 'evidence': 'ירוק'}]}  # not in the message
        it = self._interp({'ok': True, 'raw': raw, 'cost_usd': '0.0009', 'model': 'gemini-3.1-flash-lite'}).interpret(self.MSG)
        fields = {p.field for p in it.proposals}
        self.assertIn('login', fields)
        self.assertNotIn('color', fields)                    # hallucinated evidence dropped on the API side
        self.assertEqual(it.interpreter, 'model:gemini-3.1-flash-lite+deterministic')
        self.assertEqual(it.cost_usd, '0.0009')

    def test_timeout_or_failure_falls_back_to_deterministic(self):
        it = self._interp(None).interpret(self.MSG)
        self.assertEqual(it.interpreter, 'deterministic')
        self.assertIn('timeout', it.dropped[-1])
        it = self._interp({'ok': False, 'error': 'disabled'}).interpret(self.MSG)
        self.assertIn('disabled', it.dropped[-1])

    def test_queue_down_falls_back(self):
        def boom(m):
            raise ConnectionError('redis down')
        it = W.WorkerInterpreter(boom, lambda j: None, wait_seconds=1).interpret(self.MSG)
        self.assertEqual(it.interpreter, 'deterministic')

    def test_supervisor_routes_to_worker_only_when_fully_authorized(self):
        from omni_prod.conversation.store import MemoryConversationStore
        from omni_prod.conversation.supervisor import ConversationSupervisor
        from tests.test_conversation_os import MemoryBriefs
        calls = []
        fake = W.WorkerInterpreter(lambda m: calls.append(m) or 'j', lambda j: {'ok': False, 'error': 'x'}, wait_seconds=0)
        sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), worker_interpreter=fake)
        env = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0'}
        with mock.patch.dict(os.environ, env):
            sup.turn(project_id='p', account_id='a', message='crm for my team')
        self.assertEqual(calls, [])                          # no budget -> never enqueued
        with mock.patch.dict(os.environ, {**env, 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05'}):
            sup.turn(project_id='p', account_id='a', message='blue please')
        self.assertEqual(calls, ['blue please'])


if __name__ == '__main__':
    unittest.main()
