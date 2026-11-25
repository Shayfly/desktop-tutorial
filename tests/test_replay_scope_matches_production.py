"""verify-replay hands a stored version's contract to the behavioural acceptance like production does.

2026-11-25, post-deploy run 45607249874: verify-replay re-verified the 10 newest versions and 0 passed. Every content
site failed "missing required behavior kinds: data_create", including v_089840b5472d4323, whose build
(bld_c35b8332) production had passed READY. Root cause: gate_replay copied the keys infrastructure /
required_integrations / user_roles / defaults_applied / prompt, but contract_scope_for_version returns the defaults
under 'defaults', so 'static_content_site' never reached acceptance_scope and the strict data floor applied.

The contract row is the production row behind that build (read-only, phone and address redacted).
"""
import json
import unittest
from pathlib import Path

from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
from omni_prod.gate_replay import apply_version_scope
from omni_prod.web_saas_acceptance import acceptance_scope
from omni_prod.worker_tasks import contract_scope_for_version, set_acceptance_scope

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'replay_content_site_contract.json').read_text('utf-8'))


class _Cursor:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        self.params = params

    def fetchone(self):
        return self._row


class _Conn(_Cursor):
    def cursor(self):
        return _Cursor(self._row)


class _Pool:
    def __init__(self, row):
        self._row = row

    def connection(self):
        return _Conn(self._row)


class _Engine:
    def __init__(self, executor):
        self.executor = executor


def _replayed_scope():
    target = BehaviorAcceptanceExecutor(object())
    scope = contract_scope_for_version(_Pool(tuple(FIXTURE['row'])), project_id='tenant_x', version_id='v_089840b5472d4323')
    apply_version_scope(target, scope)
    return target.scope


def _production_scope():
    infra, integrations, roles, defaults, prompt = FIXTURE['row']
    target = BehaviorAcceptanceExecutor(object())
    set_acceptance_scope(_Engine(target), {'infrastructure': infra, 'required_integrations': integrations,
                                           'user_roles': roles, 'defaults_applied': defaults, 'prompt': prompt})
    return target.scope


class ReplayScopeTests(unittest.TestCase):
    def test_a_content_site_replays_without_the_data_floor(self):
        required, waived = acceptance_scope(_replayed_scope())
        self.assertNotIn('data_create', required)
        self.assertIn('data_create', waived)

    def test_replay_requires_exactly_what_the_production_build_required(self):
        self.assertEqual(acceptance_scope(_replayed_scope()), acceptance_scope(_production_scope()))

    def test_no_contract_keeps_the_strict_floor(self):
        target = BehaviorAcceptanceExecutor(object())
        apply_version_scope(target, contract_scope_for_version(_Pool(None), project_id='p', version_id='v'))
        self.assertIsNone(target.scope)
        required, waived = acceptance_scope(target.scope)
        self.assertIn('data_create', required)
        self.assertEqual(waived, ())


if __name__ == '__main__':
    unittest.main()
