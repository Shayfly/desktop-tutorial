"""Live run 1 (bld_15f930f7638d4d97897890cc003b7e4b, 2026-10-22): the generated acceptance step S2
(data_create, POST /api/items) had no body. The app correctly answered 400, so no correct app could
pass, and the repair message told the repairer to fix the app. Founder 2026-10-22 08:56: refuse such a
step in the existing validator before any request; correct the misleading repair message; stop alert().
"""
from __future__ import annotations

import unittest

from omni_prod import autonomous_agents as agents
from omni_prod.behavior_acceptance import _failure_text
from omni_prod.web_saas_acceptance import _validate_plan

IDS = {'A1', 'A2'}


def plan(step: dict) -> list[dict]:
    base = {'id': 'S2', 'kind': 'data_create', 'acceptance_ids': ['A2'], 'method': 'POST', 'path': '/api/items',
            'expect_status': 201}
    return [{'id': 'admin', 'steps': [{**base, **step}]}]


class WriteStepNeedsBody(unittest.TestCase):
    def test_run1_step_exactly_as_generated_is_refused(self):
        error = _validate_plan(plan({}), IDS)
        self.assertIsNotNone(error)
        self.assertIn('S2', error)
        self.assertIn('without a json body', error)

    def test_empty_bodies_are_refused(self):
        for body in ({}, [], '', None):
            with self.subTest(body=body):
                self.assertIsNotNone(_validate_plan(plan({'json': body}), IDS))

    def test_update_with_put_or_patch_needs_a_body(self):
        for method in ('PUT', 'PATCH', 'POST'):
            with self.subTest(method=method):
                self.assertIsNotNone(_validate_plan(plan({'kind': 'data_update', 'method': method,
                                                           'path': '/api/items/1', 'expect_status': 200}), IDS))

    def test_a_create_with_data_is_accepted(self):
        body = {'name': 'x', 'description': 'd', 'price': 10, 'date': '${today}'}
        self.assertIsNone(_validate_plan(plan({'json': body}), IDS))

    def test_other_kinds_and_methods_are_unchanged(self):
        self.assertIsNone(_validate_plan(plan({'kind': 'data_delete', 'method': 'DELETE', 'path': '/api/items/1',
                                               'expect_status': 204}), IDS))
        self.assertIsNone(_validate_plan(plan({'kind': 'data_read', 'method': 'GET', 'path': '/'}), IDS))
        self.assertIsNone(_validate_plan(plan({'kind': 'api_smoke', 'method': 'POST', 'path': '/api/ping'}), IDS))


class RepairMessageNamesTheRequest(unittest.TestCase):
    REPORT = {'summary': '1 failed check(s); missing required behavior kinds: data_create',
              'checks': [{'step_id': 'S2', 'kind': 'data_create', 'acceptance_ids': ['A2'], 'passed': False,
                          'request': 'POST /api/items', 'http_status': 400,
                          'detail': 'AssertionError: expected HTTP 201, got 400'}],
              'missing_kinds': ['data_create']}

    def test_body_less_write_is_marked(self):
        _, detail = _failure_text(self.REPORT)
        self.assertIn('sent POST /api/items (no body) -> HTTP 400', detail)

    def test_request_with_body_is_not_marked(self):
        report = {**self.REPORT, 'checks': [{**self.REPORT['checks'][0], 'request': 'POST /api/items {"name": "x"}'}]}
        _, detail = _failure_text(report)
        self.assertNotIn('(no body)', detail)

    def test_message_sends_the_repairer_to_the_step_first(self):
        _, detail = _failure_text(self.REPORT)
        self.assertIn('first check the request it sent', detail)
        self.assertIn('correct that step in .omni/project.json', detail)
        self.assertIn('Never remove coverage of an acceptance criterion', detail)
        # the old wording pushed the repairer to change the app whatever the request was
        self.assertNotIn('Fix the app so these requests behave as the product promises', detail)


class NoBrowserDialogs(unittest.TestCase):
    def test_generator_and_repairer_are_told(self):
        for system in (agents._GENERATOR_SYSTEM, agents._REPAIR_SYSTEM):
            self.assertIn('Never call alert(), confirm() or prompt()', system)

    def test_generator_is_told_write_steps_need_a_body(self):
        self.assertIn('must carry a non-empty "json" body', agents._GENERATOR_SYSTEM)


if __name__ == '__main__':
    unittest.main()
