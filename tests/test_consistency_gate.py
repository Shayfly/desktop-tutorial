"""Cross-file consistency gate (directive 2026-10-10 P0.4/5/7)."""
import json
import unittest

from omni_prod.consistency_gate import CONSISTENCY_FAILURE_ID, ConsistencyGateExecutor, scan

APP = '''import json, sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from storage import add_item, list_items

PAGE = """<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="/static/app.css"></head><body>
<form id="f"><label for="name">שם</label><input id="name" name="name"></form>
<script>fetch('/api/items').then(r => r.json()); fetch(`/api/items/${id}`, {method: 'DELETE'});</script>
</body></html>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._send(PAGE)
        elif self.path.startswith('/static/'):
            self._file(self.path)
        elif self.path == '/api/items':
            self._send(json.dumps(list_items()))
'''
STORAGE = 'def add_item(x):\n    pass\n\ndef list_items():\n    return []\n'
MANIFEST = {'verify': [{'name': 'unit', 'argv': ['python', '-m', 'pytest', 'tests/test_app.py'], 'acceptance_ids': ['A1']}],
            'web_saas_acceptance': {'personas': [{'id': 'p', 'steps': [
                {'id': 's1', 'kind': 'data_read', 'method': 'GET', 'path': '/api/items', 'expect_status': 200},
                {'id': 's2', 'kind': 'data_delete', 'method': 'DELETE', 'path': '/api/items/${created_id}', 'expect_status': 200}]}]}}


def repo(**over):
    r = {'app.py': APP, 'storage.py': STORAGE, 'static/app.css': 'body{}', 'tests/test_app.py': 'def test_x():\n    pass\n',
         '.omni/project.json': json.dumps(MANIFEST)}
    r.update(over)
    return {k: v for k, v in r.items() if v is not None}


def checks(report):
    return sorted({f.check for f in report.blocking})


class ConsistencyTests(unittest.TestCase):
    def test_a_consistent_single_file_app_passes(self):
        report = scan(repo())
        self.assertEqual(report.blocking, [], [f.__dict__ for f in report.blocking])

    def test_python_syntax_error_names_file_and_line(self):
        r = scan(repo(**{'storage.py': 'def add_item(x):\n    return (\n'}))
        f = [f for f in r.blocking if f.check == 'syntax'][0]
        self.assertEqual(f.path, 'storage.py')
        self.assertIsNotNone(f.line)

    def test_import_of_a_name_the_local_module_lacks(self):
        r = scan(repo(**{'storage.py': 'def add_item(x):\n    pass\n'}))
        f = [f for f in r.blocking if f.check == 'imports'][0]
        self.assertIn("'list_items'", f.message)
        self.assertEqual((f.path, f.line), ('app.py', 3))

    def test_page_calling_a_route_the_server_lacks(self):
        r = scan(repo(**{'app.py': APP.replace("fetch('/api/items')", "fetch('/api/bookings')")}))
        self.assertIn('routes', checks(r))
        self.assertIn('/api/bookings', r.blocking[0].message)

    def test_acceptance_step_calling_a_missing_route(self):
        m = json.loads(json.dumps(MANIFEST))
        m['web_saas_acceptance']['personas'][0]['steps'][0]['path'] = '/api/appointments'
        r = scan(repo(**{'.omni/project.json': json.dumps(m)}))
        self.assertTrue(any('acceptance step s1' in f.message for f in r.blocking))

    def test_segment_dispatching_server_is_not_a_false_positive(self):
        server = APP.replace("elif self.path == '/api/items':",
                             "parts = self.path.strip('/').split('/')\n        if parts[0] == 'api' and parts[1] == 'items':")
        self.assertNotIn('routes', checks(scan(repo(**{'app.py': server}))))

    def test_specific_prefix_handler_serves_slugs_but_generic_api_does_not(self):
        server = APP + "\n        elif self.path.startswith('/team/'):\n            pass\n        elif self.path.startswith('/api/'):\n            pass\n"
        m = json.loads(json.dumps(MANIFEST))
        m['web_saas_acceptance']['personas'][0]['steps'][0]['path'] = '/team/maccabi-tel-aviv'
        m['web_saas_acceptance']['personas'][0]['steps'][1]['path'] = '/api/bookings'
        r = scan(repo(**{'app.py': server, '.omni/project.json': json.dumps(m)}))
        msgs = ' '.join(f.message for f in r.blocking)
        self.assertNotIn('/team/', msgs)
        self.assertIn('/api/bookings', msgs)

    def test_missing_static_asset(self):
        r = scan(repo(**{'static/app.css': None}))
        self.assertIn('static', checks(r))

    def test_manifest_naming_a_missing_test_file(self):
        r = scan(repo(**{'tests/test_app.py': None, 'tests/test_other.py': 'def test_y():\n    pass\n'}))
        self.assertIn('manifest', checks(r))

    def test_accessibility_findings_are_advisories(self):
        page = APP.replace('<label for="name">שם</label>', '<h1>תורים</h1>').replace(' dir="rtl"', '')
        r = scan(repo(**{'app.py': page}))
        self.assertEqual(checks(r), [])
        kinds = {f.message for f in r.advisories}
        self.assertIn('<input> without a label', kinds)
        self.assertIn('Hebrew page without dir="rtl"', kinds)

    def test_no_server_source_skips_route_check(self):
        r = scan({'index.html': "<html lang='en'><script>fetch('/api/x')</script></html>"})
        self.assertEqual(r.blocking, [])
        self.assertIn('routes', r.skipped)


class GateExecutorTests(unittest.TestCase):
    def test_blocking_finding_stops_before_the_sandbox(self):
        ran = []
        inner = type('I', (), {'execute': lambda self, **k: ran.append(1)})()
        gate = ConsistencyGateExecutor(inner)
        report = gate.execute(repository=repo(**{'storage.py': 'def add_item(x):\n    pass\n'}), spec=None)
        self.assertFalse(report.passed)
        self.assertEqual(report.failures[0].acceptance_id, CONSISTENCY_FAILURE_ID)
        self.assertIn('app.py:3', report.failures[0].message)
        self.assertEqual(ran, [])
        self.assertFalse(gate.last_consistency['passed'])

    def test_disabled_gate_passes_through(self):
        inner = type('I', (), {'execute': lambda self, **k: 'inner'})()
        self.assertEqual(ConsistencyGateExecutor(inner, enabled=False).execute(repository={}, spec=None), 'inner')



class ReplayTests(unittest.TestCase):
    def test_replay_counts_blocking_versions_and_prompt_coverage(self):
        from omni_prod.gate_replay import replay
        good, bad = repo(), repo(**{'storage.py': 'def add_item(x):\n    pass\n'})
        good['rights/rights-manifest.json'] = '{}'
        store = {'k1': good, 'k2': bad}
        out = replay([('v1', 'k1'), ('v2', 'k2'), ('v3', 'missing')], lambda k: store[k])
        self.assertEqual((out['versions'], out['blocking_versions'], out['load_failures']), (2, 1, 1))
        self.assertEqual(out['coverage']['entry_in_prompt'], 2)
        self.assertEqual(out['coverage']['all_source_in_prompt'], 2)   # rights metadata is not code


if __name__ == '__main__':
    unittest.main()
