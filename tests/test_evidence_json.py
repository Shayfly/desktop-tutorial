"""A build always reaches a terminal status, whatever its evidence holds.

Golden E2E #1 on Preview (2026-10-07): after both model routes failed, the
worker's failure handler crashed in json.dumps on a Decimal in the evidence
and the build stayed "running" forever.
"""
import json
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from omni_prod.evidence_json import dumps_evidence, dumps_evidence_for_terminal_state
from omni_prod.job_repository import PostgresBuildRepository
from omni_prod.models import BuildStatus

ROOT = Path(__file__).resolve().parents[1]

# Shape of the worker's failure evidence (worker_tasks._run_live_build_job).
FAILURE_EVIDENCE = {
    'billing': 'released',
    'economics_settlement': {'action': 'released', 'settled_provider_cost_usd': Decimal('0')},
    'model_budget_binding': {'effective_budget_usd': Decimal('0.50'), 'reserved_model_usd': Decimal('0.50')},
    'model_route_events': [{'route': 'gemini-3-8-flash', 'max_estimated_cost_usd': Decimal('0.0123')}],
    'provider_spend_usd': '0', 'external_model_calls': 0,
    'at': datetime(2026, 10, 7, 14, 36, tzinfo=timezone.utc), 'kinds': {'database', 'auth_session'},
}


@dataclass
class _Endpoint:
    name: str
    api_key: str


class EncodingTests(unittest.TestCase):
    def test_decimals_are_exact_strings(self):
        data = json.loads(dumps_evidence(FAILURE_EVIDENCE))
        self.assertEqual(data['model_budget_binding']['effective_budget_usd'], '0.50')
        self.assertEqual(data['model_route_events'][0]['max_estimated_cost_usd'], '0.0123')
        self.assertEqual(data['at'], '2026-10-07T14:36:00+00:00')
        self.assertEqual(data['kinds'], ['auth_session', 'database'])

    def test_plain_json_raised_on_this_evidence(self):
        with self.assertRaises(TypeError):
            json.dumps(FAILURE_EVIDENCE)

    def test_unknown_objects_are_never_stringified(self):
        evidence = {'endpoint': _Endpoint('gemini', 'AIza-secret-value')}
        with self.assertRaises(TypeError):
            dumps_evidence(evidence)
        marker = dumps_evidence_for_terminal_state(evidence)
        self.assertNotIn('AIza-secret-value', marker)
        self.assertEqual(json.loads(marker)['evidence_keys'], ['endpoint'])


class _Cur:
    def __init__(self):
        self.calls, self.rowcount = [], 1

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TerminalTransitionTests(unittest.TestCase):
    def test_failed_transition_is_written_with_decimal_evidence(self):
        cur = _Cur()

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def cursor(self): return cur

        import omni_prod.db as db
        original = db.transaction
        db.transaction = lambda url: Conn()
        try:
            ok = PostgresBuildRepository.__new__(PostgresBuildRepository)
            ok.database_url = 'postgresql://unused'
            written = ok.transition(build_id='bld_1', expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
                                    error_code='worker_exception', error_message='ModelGatewayError: 503',
                                    evidence_json=FAILURE_EVIDENCE)
        finally:
            db.transaction = original
        self.assertTrue(written)
        evidence_param = next(p for p in cur.calls[0][1] if isinstance(p, str) and p.startswith('{'))
        self.assertEqual(json.loads(evidence_param)['billing'], 'released')

    def test_repositories_use_the_encoder(self):
        for path in ('omni_prod/job_repository.py', 'omni_prod/modification_repository.py'):
            source = (ROOT / path).read_text()
            self.assertIn('dumps_evidence_for_terminal_state(evidence_json', source, path)
            self.assertNotIn('json.dumps(evidence_json', source, path)


if __name__ == '__main__':
    unittest.main()
