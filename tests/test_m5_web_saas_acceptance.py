import json
import unittest
from types import SimpleNamespace

from omni_prod.product_spec import ProductSpec
from omni_prod.web_saas_acceptance import (
    AcceptanceReport,
    HttpResponse,
    WebSaaSAcceptanceRunner,
)
from omni_prod.preview_runtime import parse_web_saas_acceptance_plan
from omni_prod.worker_tasks import _run_preview_launch


REQUIRED_KINDS = (
    'auth', 'role', 'data_create', 'data_read', 'data_update', 'data_delete',
    'integration', 'responsive', 'api_smoke',
)


def contract(ids=tuple(f'A{i}' for i in range(1, 10))):
    reqs = []
    acceptance = []
    for i, aid in enumerate(ids, 1):
        rid = f'R{i}'
        reqs.append({'id': rid, 'text': f'requirement {i}', 'kind': 'functional', 'mandatory': True})
        acceptance.append({'id': aid, 'requirement_id': rid, 'text': f'criterion {i}'})
    return ProductSpec.from_dict({
        'title': 'Generic SaaS', 'summary': 'Generic vertical slice', 'stack': ['web'],
        'requirements': reqs, 'acceptance': acceptance,
    })


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, *, method, url, headers=None, json_body=None, timeout_seconds=10.0):
        self.calls.append({
            'method': method, 'url': url, 'headers': dict(headers or {}),
            'json_body': json_body, 'timeout_seconds': timeout_seconds,
        })
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def response(status=200, payload=None, text=None, headers=None):
    if text is None:
        text = json.dumps(payload if payload is not None else {})
    return HttpResponse(status=status, headers=headers or {'content-type': 'application/json'}, body=text.encode())


def full_personas():
    return [{
        'id': 'admin-primary',
        'role': 'admin',
        'steps': [
            {'id': 'login', 'kind': 'auth', 'acceptance_ids': ['A1'], 'method': 'POST',
             'path': '/api/login', 'json': {'email': 'owner@example.test', 'password': 'secret'},
             'expect_status': 200, 'expect_json_contains': {'role': 'admin'}, 'capture': {'token': 'token'}},
            {'id': 'role', 'kind': 'role', 'acceptance_ids': ['A2'], 'method': 'GET',
             'path': '/api/me', 'headers': {'Authorization': 'Bearer ${token}'},
             'expect_status': 200, 'expect_json_contains': {'role': 'admin'}},
            {'id': 'create', 'kind': 'data_create', 'acceptance_ids': ['A3'], 'method': 'POST',
             'path': '/api/items', 'headers': {'Authorization': 'Bearer ${token}'},
             'json': {'name': 'first'}, 'expect_status': 201, 'capture': {'item_id': 'id'}},
            {'id': 'read', 'kind': 'data_read', 'acceptance_ids': ['A4'], 'method': 'GET',
             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
             'expect_status': 200, 'expect_json_contains': {'name': 'first'}},
            {'id': 'update', 'kind': 'data_update', 'acceptance_ids': ['A5'], 'method': 'PATCH',
             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
             'json': {'name': 'changed'}, 'expect_status': 200, 'expect_json_contains': {'name': 'changed'}},
            {'id': 'delete', 'kind': 'data_delete', 'acceptance_ids': ['A6'], 'method': 'DELETE',
             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
             'expect_status': 204},
            {'id': 'job', 'kind': 'integration', 'acceptance_ids': ['A7'], 'method': 'POST',
             'path': '/api/jobs', 'headers': {'Authorization': 'Bearer ${token}'},
             'expect_status': 202, 'expect_json_contains': {'queued': True}},
            {'id': 'responsive', 'kind': 'responsive', 'acceptance_ids': ['A8'], 'method': 'GET',
             'path': '/', 'expect_status': 200, 'expect_text_contains': 'viewport'},
            {'id': 'api-smoke', 'kind': 'api_smoke', 'acceptance_ids': ['A9'], 'method': 'GET',
             'path': '/api/health', 'expect_status': 200},
        ],
    }]


class TestAcceptanceRunner(unittest.TestCase):
    def test_health_only_does_not_create_false_release_pass(self):
        transport = ScriptedTransport([response(200, {'ok': True})])
        runner = WebSaaSAcceptanceRunner(transport=transport)
        personas = [{'id': 'health', 'steps': [
            {'id': 'health', 'kind': 'health', 'acceptance_ids': ['A1'], 'method': 'GET', 'path': '/health', 'expect_status': 200}
        ]}]
        report = runner.verify(
            {'id': 'prv1', 'project_id': 'p', 'version_id': 'v', 'preview_url': 'https://p.example'},
            contract(), personas,
        )
        self.assertEqual(report.status, 'FAIL')
        self.assertFalse(report.release_eligible)
        self.assertIn('auth', report.missing_kinds)
        self.assertIn('A9', report.missing_acceptance_ids)

    def test_login_role_crud_integration_responsive_and_api_smoke_pass(self):
        transport = ScriptedTransport([
            response(200, {'role': 'admin', 'token': 'tok-1'}),
            response(200, {'role': 'admin'}),
            response(201, {'id': 'item-7', 'name': 'first'}),
            response(200, {'id': 'item-7', 'name': 'first'}),
            response(200, {'id': 'item-7', 'name': 'changed'}),
            response(204, text=''),
            response(202, {'queued': True}),
            response(200, text='<meta name="viewport" content="width=device-width">'),
            response(200, {'ok': True}),
        ])
        runner = WebSaaSAcceptanceRunner(transport=transport)
        report = runner.verify(
            {'id': 'prv1', 'project_id': 'p', 'version_id': 'v', 'preview_url': 'https://p.example'},
            contract(), full_personas(),
        )
        self.assertEqual(report.status, 'PASS')
        self.assertTrue(report.release_eligible)
        self.assertEqual(report.missing_kinds, ())
        self.assertEqual(report.missing_acceptance_ids, ())
        self.assertEqual(transport.calls[1]['headers']['Authorization'], 'Bearer tok-1')
        self.assertTrue(transport.calls[3]['url'].endswith('/api/items/item-7'))

    def test_unknown_contract_acceptance_id_fails_closed_without_request(self):
        transport = ScriptedTransport([])
        runner = WebSaaSAcceptanceRunner(transport=transport)
        personas = [{'id': 'bad', 'steps': [
            {'id': 'bad', 'kind': 'api_smoke', 'acceptance_ids': ['NOT-IN-CONTRACT'],
             'method': 'GET', 'path': '/', 'expect_status': 200}
        ]}]
        report = runner.verify(
            {'id': 'prv1', 'project_id': 'p', 'version_id': 'v', 'preview_url': 'https://p.example'},
            contract(), personas,
        )
        self.assertEqual(report.status, 'FAIL')
        self.assertIn('unknown acceptance id', report.summary.lower())
        self.assertEqual(transport.calls, [])

    def test_failed_integration_blocks_release_even_when_other_smokes_pass(self):
        responses = [
            response(200, {'role': 'admin', 'token': 'tok-1'}), response(200, {'role': 'admin'}),
            response(201, {'id': 'item-7'}), response(200, {'name': 'first'}),
            response(200, {'name': 'changed'}), response(204, text=''),
            response(500, {'queued': False}),
            response(200, text='viewport'), response(200, {'ok': True}),
        ]
        report = WebSaaSAcceptanceRunner(transport=ScriptedTransport(responses)).verify(
            {'id': 'prv1', 'project_id': 'p', 'version_id': 'v', 'preview_url': 'https://p.example'},
            contract(), full_personas(),
        )
        self.assertEqual(report.status, 'FAIL')
        self.assertFalse(report.release_eligible)
        failed = [x for x in report.checks if not x.passed]
        self.assertEqual(failed[0].step_id, 'job')


class TestAcceptancePlanParsing(unittest.TestCase):
    def test_parses_generic_plan_from_project_manifest(self):
        repo = {'.omni/project.json': json.dumps({
            'schema_version': 2,
            'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
            'web_saas_acceptance': {
                'product_family': 'managed_web_saas_v1',
                'required_kinds': list(REQUIRED_KINDS),
                'personas': full_personas(),
            },
        })}
        plan = parse_web_saas_acceptance_plan(repo)
        self.assertEqual(plan.product_family, 'managed_web_saas_v1')
        self.assertEqual(set(plan.required_kinds), set(REQUIRED_KINDS))
        self.assertEqual(plan.personas[0]['id'], 'admin-primary')


class FakeLaunchRepo:
    def __init__(self):
        self.acceptance = None
        self.crashed_error = None
        self.running = False

    def record_runtime(self, *args, **kwargs): return True
    def mark_running(self, *args, **kwargs): self.running = True; return True
    def mark_failed(self, *args, **kwargs): return True
    def mark_cleaned(self, *args, **kwargs): return None
    def record_acceptance(self, preview_id, project_id, version_id, report):
        self.acceptance = report
        return 'build-1'
    def mark_crashed(self, preview_id, error):
        self.crashed_error = error
        self.running = False
        return True


class FakePreviewProvider:
    bind_address = '127.0.0.1'
    def __init__(self):
        self.stopped = False
        self.liveness_calls = 0
    def start(self, **kwargs):
        return SimpleNamespace(container_id='cid', host_port=43210, workdir='/tmp/w',
                               contract=SimpleNamespace(health_path='/health'))
    def is_running(self, cid):
        self.liveness_calls += 1
        return (True, None) if self.liveness_calls == 1 else (False, 17)
    def logs(self, cid, tail=50): return 'fatal preview crash\nsecret=REDACTED'
    def stop(self, cid): self.stopped = True
    def remove_workdir(self, path): pass


class FailingAcceptanceRunner:
    def verify(self, preview, contract, personas):
        return AcceptanceReport(
            status='FAIL', release_eligible=False, summary='functional request failed', checks=(),
            covered_acceptance_ids=(), missing_acceptance_ids=('A1',),
            covered_kinds=(), missing_kinds=('api_smoke',), runtime_logs=None,
        )


class TestPreviewCrashEvidence(unittest.TestCase):
    def test_acceptance_crash_preserves_logs_and_marks_preview_failed(self):
        repo = FakeLaunchRepo()
        provider = FakePreviewProvider()
        status = _run_preview_launch(
            'prv1', 'p', 'v', repo=repo, provider=provider, runtime_host='worker1',
            url_template='https://{preview_id}.preview.example', probe_host='127.0.0.1',
            probe_timeout=0.1, probe_interval=0,
            http_get=lambda url, timeout: 200, sleep=lambda _: None,
            acceptance_runner=FailingAcceptanceRunner(), acceptance_contract=contract(('A1',)),
            acceptance_personas=[{'id': 'x', 'steps': []}],
        )
        self.assertEqual(status, 'FAILED')
        self.assertIsNotNone(repo.acceptance)
        self.assertIn('fatal preview crash', repo.acceptance.runtime_logs)
        self.assertIn('fatal preview crash', repo.crashed_error)


class ScriptedCursor:
    def __init__(self, fetch=(), rowcounts=()):
        self.executed = []
        self._fetch = list(fetch)
        self._rowcounts = list(rowcounts)
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((' '.join(sql.split()), params))
        self.rowcount = self._rowcounts.pop(0) if self._rowcounts else 1

    def fetchone(self):
        return self._fetch.pop(0) if self._fetch else None

    def __enter__(self): return self
    def __exit__(self, *args): return False


class Ctx:
    def __init__(self, value=None): self.value = value
    def __enter__(self): return self.value if self.value is not None else self
    def __exit__(self, *args): return False


class FakeConn:
    def __init__(self, cur): self.cur = cur
    def cursor(self): return self.cur
    def transaction(self): return Ctx()


class FakePool:
    def __init__(self, cur): self.conn = FakeConn(cur)
    def connection(self): return Ctx(self.conn)


class TestDurableAcceptanceEvidence(unittest.TestCase):
    def test_report_is_linked_to_build_version_and_preview_in_existing_build_evidence(self):
        from omni_prod.preview_repository import PostgresPreviewRepository
        report = AcceptanceReport(
            status='PASS', release_eligible=True, summary='ok', checks=(),
            covered_acceptance_ids=('A1',), missing_acceptance_ids=(),
            covered_kinds=REQUIRED_KINDS, missing_kinds=(), runtime_logs=None,
        )
        cur = ScriptedCursor(fetch=[('build-7', {'economics_quote': {'x': 1}})])
        repo = PostgresPreviewRepository(FakePool(cur))
        build_id = repo.record_acceptance('prv-7', 'project-key', 'version-7', report)
        self.assertEqual(build_id, 'build-7')
        self.assertIn('FOR UPDATE', cur.executed[0][0])
        self.assertIn('jsonb_set', cur.executed[1][0])
        payload = json.loads(cur.executed[1][1][1])
        self.assertEqual(payload['build_id'], 'build-7')
        self.assertEqual(payload['preview_id'], 'prv-7')
        self.assertEqual(payload['version_id'], 'version-7')
        self.assertEqual(payload['status'], 'PASS')

    def test_no_owning_build_means_no_false_durable_pass(self):
        from omni_prod.preview_repository import PostgresPreviewRepository
        cur = ScriptedCursor(fetch=[None])
        repo = PostgresPreviewRepository(FakePool(cur))
        report = AcceptanceReport(
            status='PASS', release_eligible=True, summary='ok', checks=(),
            covered_acceptance_ids=('A1',), missing_acceptance_ids=(),
            covered_kinds=REQUIRED_KINDS, missing_kinds=(), runtime_logs=None,
        )
        self.assertIsNone(repo.record_acceptance('prv', 'p', 'v', report))
        self.assertEqual(len(cur.executed), 1)


class TestDeterministicAcceptanceFloor(unittest.TestCase):
    def test_generated_required_kinds_cannot_weaken_platform_minimum(self):
        runner = WebSaaSAcceptanceRunner(transport=ScriptedTransport([]), required_kinds=('api_smoke',))
        self.assertTrue(set(REQUIRED_KINDS).issubset(set(runner.required_kinds)))

    def test_generator_prompt_requires_behavioral_plan(self):
        from omni_prod.autonomous_agents import _GENERATOR_SYSTEM
        for token in ('web_saas_acceptance', 'managed_web_saas_v1', 'data_create', 'integration', 'api_smoke'):
            self.assertIn(token, _GENERATOR_SYSTEM)


class TestRealHttpAcceptance(unittest.TestCase):
    def test_real_http_session_executes_full_behavioral_flow(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        state = {'items': {}}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def _json_body(self):
                n = int(self.headers.get('content-length', '0') or 0)
                return json.loads(self.rfile.read(n) or b'{}')

            def _send(self, status, payload=None, content_type='application/json'):
                body = b'' if payload is None else (
                    payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                )
                self.send_response(status)
                self.send_header('content-type', content_type)
                self.send_header('content-length', str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _authorized(self):
                return self.headers.get('authorization') == 'Bearer tok-1'

            def do_GET(self):
                if self.path == '/':
                    return self._send(200, '<meta name="viewport" content="width=device-width">', 'text/html')
                if self.path == '/api/health':
                    return self._send(200, {'ok': True})
                if self.path == '/api/me':
                    return self._send(200 if self._authorized() else 401,
                                      {'role': 'admin'} if self._authorized() else {'error': 'unauthorized'})
                if self.path.startswith('/api/items/'):
                    if not self._authorized():
                        return self._send(401, {'error': 'unauthorized'})
                    item_id = self.path.rsplit('/', 1)[-1]
                    item = state['items'].get(item_id)
                    return self._send(200, item) if item else self._send(404, {'error': 'not found'})
                return self._send(404, {'error': 'not found'})

            def do_POST(self):
                if self.path == '/api/login':
                    self._json_body()
                    return self._send(200, {'role': 'admin', 'token': 'tok-1'})
                if self.path == '/api/items':
                    if not self._authorized():
                        return self._send(401, {'error': 'unauthorized'})
                    payload = self._json_body()
                    item = {'id': 'item-7', **payload}
                    state['items']['item-7'] = item
                    return self._send(201, item)
                if self.path == '/api/jobs':
                    if not self._authorized():
                        return self._send(401, {'error': 'unauthorized'})
                    return self._send(202, {'queued': True})
                return self._send(404, {'error': 'not found'})

            def do_PATCH(self):
                if self.path == '/api/items/item-7' and self._authorized():
                    state['items']['item-7'].update(self._json_body())
                    return self._send(200, state['items']['item-7'])
                return self._send(404, {'error': 'not found'})

            def do_DELETE(self):
                if self.path == '/api/items/item-7' and self._authorized():
                    state['items'].pop('item-7', None)
                    return self._send(204)
                return self._send(404, {'error': 'not found'})

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_address[1]}'
            report = WebSaaSAcceptanceRunner().verify(
                {'id': 'live-local', 'project_id': 'p', 'version_id': 'v', 'preview_url': base},
                contract(), full_personas(),
            )
            self.assertEqual(report.status, 'PASS', report.summary)
            self.assertTrue(report.release_eligible)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    @unittest.skipUnless(__import__('os').environ.get('M5_LIVE_PREVIEW_BASE_URL'),
                         'set M5_LIVE_PREVIEW_BASE_URL to run against the canonical live Web/SaaS fixture')
    def test_external_live_preview_gate(self):
        import os
        report = WebSaaSAcceptanceRunner().verify(
            {'id': 'external', 'project_id': 'p', 'version_id': 'v',
             'preview_url': os.environ['M5_LIVE_PREVIEW_BASE_URL']},
            contract(), full_personas(),
        )
        self.assertEqual(report.status, 'PASS', report.summary)


if __name__ == '__main__':
    unittest.main()
