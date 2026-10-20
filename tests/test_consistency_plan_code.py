"""Consistency gate `plan_code`: what the plan makes users do must exist in the code (founder 2026-10-20 22:07).

Paid run 39473090833: the plan had data_create (POST /api/appointments) and data_delete (DELETE /api/appointments/1);
the page said "you can book in the form below" and had no form, no input, no button and no script. Preview rejected it
(rounds 0 and 2) and behaviour failed: three repair rounds. The fixture is the REAL round-0 index.html and app.py, read
from R2 by run 39477884309 (tests/fixtures/run_39473090833_round0). The plan is the one the same build's behaviour
evidence records (steps S1-S5, inspect-build 39473867717); the round-0 project.json itself was not printed by that read.
"""
import json
import unittest
from pathlib import Path

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.consistency_gate import CONSISTENCY_FAILURE_ID, ConsistencyGateExecutor, scan

FIX = Path(__file__).resolve().parent / 'fixtures' / 'run_39473090833_round0'
PLAN_STEPS = [
    {"id": "S1", "kind": "api_smoke", "acceptance_ids": ["A5"], "method": "GET", "path": "/", "expect_status": 200},
    {"id": "S2", "kind": "data_read", "acceptance_ids": ["A1", "A6"], "method": "GET", "path": "/api/appointments",
     "expect_status": 200},
    {"id": "S3", "kind": "data_create", "acceptance_ids": ["A2", "A4"], "method": "POST", "path": "/api/appointments",
     "json": {"name": "ישראל", "phone": "0501234567", "date": "${date_plus_1}", "time": "10:00"}, "expect_status": 201},
    {"id": "S4", "kind": "data_delete", "acceptance_ids": ["A3"], "method": "DELETE", "path": "/api/appointments/1",
     "expect_status": 200},
    {"id": "S5", "kind": "responsive", "acceptance_ids": ["A5"], "method": "GET", "path": "/", "expect_status": 200},
]


def manifest(steps=PLAN_STEPS):
    return json.dumps({"schema_version": 2, "runtime": "python:3.11-slim", "start": ["python", "app.py"], "port": 8000,
                       "health_path": "/", "web_saas_acceptance": {"product_family": "managed_web_saas_v1",
                       "required_kinds": ["api_smoke", "data_create", "data_read", "data_delete"],
                       "personas": [{"id": "user", "steps": steps}]}})


def real_round0(**over):
    repo = {'index.html': (FIX / 'index.html').read_text(encoding='utf-8'),
            'app.py': (FIX / 'app.py.txt').read_text(encoding='utf-8'), '.omni/project.json': manifest()}
    repo.update(over)
    return {k: v for k, v in repo.items() if v is not None}


WORKING_PAGE = ('<!DOCTYPE html><html lang="he" dir="rtl"><body><form id="f"><input name="name"><button>קבע</button></form>'
                '<ul id="list"></ul><script>'
                "f.onsubmit = e => { e.preventDefault(); fetch('/api/appointments', {method: 'POST', body: '{}'}); };"
                "function cancel(id) { return fetch('/api/appointments/' + id, {method: 'DELETE'}); }"
                '</script></body></html>')


def plan_code(repo):
    report = scan(repo)
    return [f for f in report.findings if f.check == 'plan_code'], report


class TheRealRound0(unittest.TestCase):
    def test_is_reported_before_the_sandbox_with_one_narrow_message(self):
        found, _ = plan_code(real_round0())
        self.assertEqual(len(found), 1, found)
        f = found[0]
        self.assertTrue(f.blocking)
        self.assertEqual(f.path, 'index.html')
        self.assertIn('no page contains an interactive control', f.message)
        self.assertIn('S3 (data_create: POST /api/appointments)', f.message)
        self.assertIn('S4 (data_delete: DELETE /api/appointments/1)', f.message)

    def test_the_executor_does_not_start_the_sandbox(self):
        class Sandbox:
            ran = False

            def execute(self, *, repository, spec):
                Sandbox.ran = True
                return ExecutionReport(True, (), 'ok')
        report = ConsistencyGateExecutor(Sandbox()).execute(repository=real_round0(), spec=None)
        self.assertFalse(report.passed)
        self.assertFalse(Sandbox.ran)
        msgs = [f.message for f in report.failures]
        self.assertTrue(any(m.startswith('consistency (plan_code): index.html') for m in msgs), msgs)
        self.assertTrue(all(f.acceptance_id == CONSISTENCY_FAILURE_ID for f in report.failures))

    def test_the_same_app_with_a_working_page_passes(self):
        self.assertEqual(plan_code(real_round0(**{'index.html': WORKING_PAGE}))[0], [])


class EachRule(unittest.TestCase):
    def test_controls_without_delete_wiring(self):
        page = WORKING_PAGE.replace("function cancel(id) { return fetch('/api/appointments/' + id, {method: 'DELETE'}); }", '')
        found, _ = plan_code(real_round0(**{'index.html': page}))
        self.assertEqual([f.message for f in found], ['acceptance step S4 (data_delete: DELETE /api/appointments/1): '
                                                      'no page code sends DELETE'])

    def test_server_without_the_method(self):
        app = (FIX / 'app.py.txt').read_text(encoding='utf-8').replace('def do_DELETE', 'def remove')
        found, _ = plan_code(real_round0(**{'index.html': WORKING_PAGE, 'app.py': app}))
        self.assertEqual(len(found), 1)
        self.assertIn('the server has no DELETE handler', found[0].message)

    def test_client_libraries_and_forms_count(self):
        page = ('<html><body><form method="post" action="/api/appointments"><input name="n"><button>x</button></form>'
                "<script>axios.delete('/api/appointments/' + id)</script></body></html>")
        self.assertEqual(plan_code(real_round0(**{'index.html': page}))[0], [])

    def test_createElement_of_a_form_is_a_control(self):
        page = ("<html><body><div id=r></div><script>const f = document.createElement('form'); r.append(f);"
                "fetch('/api/appointments', {method: 'POST'}); fetch(u, {method: 'DELETE'});</script></body></html>")
        self.assertEqual(plan_code(real_round0(**{'index.html': page}))[0], [])


class NeverGuesses(unittest.TestCase):
    def test_a_plan_without_create_update_delete_is_not_checked(self):
        steps = [s for s in PLAN_STEPS if s['kind'] not in ('data_create', 'data_delete')]
        self.assertEqual(plan_code(real_round0(**{'.omni/project.json': manifest(steps)}))[0], [])

    def test_no_page_or_no_server_is_skipped_not_failed(self):
        found, report = plan_code(real_round0(**{'index.html': None,
                                                 'app.py': 'print("no html here")\n'}))
        self.assertEqual(found, [])
        self.assertEqual(report.skipped.get('plan_code'), 'no page source')

    def test_an_unparsable_manifest_is_left_to_the_syntax_check(self):
        self.assertEqual(plan_code(real_round0(**{'.omni/project.json': '{not json'}))[0], [])


if __name__ == '__main__':
    unittest.main()
