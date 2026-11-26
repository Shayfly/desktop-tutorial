"""verify-replay hands a stored version's contract to the behavioural acceptance like production does.

2026-11-25, post-deploy run 45607249874: verify-replay re-verified the 10 newest versions and 0 passed. Every content
site failed "missing required behavior kinds: data_create", including v_089840b5472d4323, whose build
(bld_c35b8332) production had passed READY. Root cause: gate_replay copied the keys infrastructure /
required_integrations / user_roles / defaults_applied / prompt, but contract_scope_for_version returns the defaults
under 'defaults', so 'static_content_site' never reached acceptance_scope and the strict data floor applied.

The contract row is the production row behind that build (read-only, phone and address redacted). The fixture's
contract_md5 was recorded when the row was fetched; because of the redaction this file's row cannot reproduce it, and
no test compares it (it names the fetch, it checks nothing). What is checked is the behaviour of that row.

VerifyVersionsTests drives gate_replay.verify_versions itself (review of #530, finding 7: every other test here calls
the helper apply_version_scope, so putting the old five-key copy back INSIDE verify_versions left everything green).
It runs the production chain (investor_app._verification_executor) and the real acceptance runner against a small
content site started on this machine. The doubles are the boundaries only: the database connection (its three
reads), object storage (a dict) and the sandbox runner's HTTP endpoint -- the real RemoteSandboxRepositoryExecutor
builds, checks and signs every request, and the commands run here instead of in the remote sandbox. The browser and
visual stages need a browser in the sandbox and are switched off by their own flags.
"""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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


# ---- verify_versions itself ---------------------------------------------------------------------------------------
CONTENT_SITE_APP = r"""
import http.server, os
ITEMS = "".join("<h2>Item %d</h2><p>A catalogue entry with its name, what it is made of, its size and its price, "
                "written out in full so that a visitor can read about it on the page.</p>" % n for n in range(1, 5))
PAGE = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'><title>GOA</title></head>"
        "<body><h1>GOA catalogue</h1>" + ITEMS + "</body></html>").encode()
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
    def log_message(self, *a): pass
if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
"""
CONTENT_SITE_TEST = 'import app\n\n\ndef test_the_page_lists_the_catalogue():\n    assert b"<h1>GOA catalogue</h1>" in app.PAGE\n'
SPEC = {'title': 'GOA', 'summary': 'A content site', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'show the catalogue', 'kind': 'functional', 'mandatory': True}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'the page opens'}]}
STORED = ('v_089840b5472d4323', 'v_no_contract')        # newest first, as verify_versions reads them


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _content_site() -> dict:
    """A stored site that only serves a page. Its plan reads the page and creates nothing, so it can pass only when the
    acceptance knows it is a content site -- the condition under which run 45607249874 failed on data_create."""
    steps = [{'id': f's{n}', 'kind': kind, 'acceptance_ids': ['A1'], 'method': 'GET', 'path': '/', 'expect_status': 200}
             for n, kind in enumerate(('api_smoke', 'data_read', 'responsive'), 1)]
    manifest = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': [sys.executable, 'app.py'],
                'port': _free_port(), 'health_path': '/', 'build': [['python', '-m', 'compileall', '-q', '.']],
                'verify': [{'name': 'unit tests', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': ['A1']}],
                'web_saas_acceptance': {'product_family': 'managed_web_saas_v1',
                                        'required_kinds': ['api_smoke', 'data_read', 'responsive'],
                                        'personas': [{'id': 'visitor', 'steps': steps}]}}
    return {'app.py': CONTENT_SITE_APP, 'tests/test_app.py': CONTENT_SITE_TEST, '.omni/project.json': json.dumps(manifest)}


class _SandboxRunner:
    """The sandbox runner's HTTP endpoint (the network boundary), as in tests/test_sandbox_callers_real_policy.py: the
    request the REAL RemoteSandboxRepositoryExecutor built and signed is checked again the way sandbox_service checks
    it, then its argv really runs in a copy of the snapshot on this machine. It decides nothing itself."""

    def __init__(self):
        self.build_ids = []

    def __call__(self, req, timeout=None):
        from omni_prod.sandbox_request_policy import validate_command, validate_snapshot
        payload = json.loads(req.data.decode())
        argv = payload['argv']
        validate_snapshot(payload['repository'])
        validate_command(argv, build_id=payload['build_id'], profile=payload.get('profile', 'default'),
                         repository=payload['repository'])
        self.build_ids.append(payload['build_id'])
        with tempfile.TemporaryDirectory() as root:
            for path, text in payload['repository'].items():
                full = os.path.join(root, path)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, 'w', encoding='utf-8') as f:
                    f.write(text)
            p = subprocess.run([sys.executable if argv[0] == 'python' else argv[0], *argv[1:]], cwd=root,
                               capture_output=True, text=True, timeout=120)
        body = json.dumps({'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}).encode()

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Response(body)


class _NotInThisDatabase(RuntimeError):
    """A statement the double does not answer (the replay's optional stage rows): raised, never answered."""


class _ReplayCursor:
    def __init__(self, db):
        self._db, self._row = db, None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        from omni_prod.worker_tasks import _CONTRACT_SCOPE_FOR_VERSION_SQL
        if sql == _CONTRACT_SCOPE_FOR_VERSION_SQL:
            self._db.lookups.append(tuple(params))
            self._row = self._db.contracts[params[0]]
        elif 'FROM project_version_specs' in sql:
            self._row = (dict(SPEC),)
        else:
            raise _NotInThisDatabase(sql[:80])

    def fetchone(self):
        return self._row


class _ReplayConnection(_ReplayCursor):
    def cursor(self):
        return _ReplayCursor(self._db)

    def execute(self, sql, params=()):
        if 'FROM project_versions v' not in sql:
            raise _NotInThisDatabase(sql[:80])
        return SimpleNamespace(fetchall=lambda: list(self._db.versions[:params[0]]))


class _ReplayDatabase:
    """The database connection (the network boundary). It answers the three reads verify_versions makes: the stored
    versions, a version's spec, and the contract lookup. The lookup must be worker_tasks' own statement; its row is the
    one given for that version (the statement itself runs on real PostgreSQL in tests/test_contract_scope_lineage_pg.py)."""

    def __init__(self, versions, contracts):
        self.versions, self.contracts, self.lookups = versions, contracts, []

    def connection(self):
        return _ReplayConnection(self)


class VerifyVersionsTests(unittest.TestCase):
    """One real verify_versions run over two stored versions of the same site: the production content site's contract
    for the first, no contract for the second. Only the chain's verdict is read; the release policy's decision in the
    result is not (the browser stages are off here, so it cannot be READY)."""
    # The chain is the production one with its checks on. Off: the two stages that need a browser inside the sandbox,
    # and the quality score's minimum (this fixture is a page with one test, not a product with a README).
    ENV = {'OMNI_SANDBOX_RUNNER_URL': 'http://sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'x' * 40,
           'OMNI_CONSISTENCY_GATE': '1', 'OMNI_BEHAVIOR_ACCEPTANCE': '1',
           'OMNI_BROWSER_CHECK': '0', 'OMNI_VISUAL_QA': '0', 'OMNI_MIN_QUALITY_SCORE': '0', 'OMNI_REPLAY_OUT': ''}
    STRICT_FLOOR_MISSING = 'missing required behavior kinds: auth,data_create,data_delete,data_update,integration,role'

    @classmethod
    def setUpClass(cls):
        from omni_prod import gate_replay, investor_app
        from omni_prod.remote_sandbox import RemoteSandboxRepositoryExecutor
        from omni_prod.workspace import PostgresProjectWorkspace
        store = SimpleNamespace(objects={})
        store.get_bytes = lambda key, verify=True: store.objects[key]
        workspace = PostgresProjectWorkspace(None, store)       # the real unzip; object storage is a dict
        versions = []
        for vid in STORED:
            store.objects[f'repositories/{vid}.zip'] = workspace._zip_repo(_content_site())
            versions.append((vid, 'tenant_x', f'repositories/{vid}.zip'))
        cls.database = _ReplayDatabase(versions, {STORED[0]: tuple(FIXTURE['row']), STORED[1]: None})
        cls.runner = _SandboxRunner()
        with mock.patch.dict(os.environ, cls.ENV), \
                mock.patch.object(investor_app, 'RemoteSandboxRepositoryExecutor',
                                  lambda config: RemoteSandboxRepositoryExecutor(config, urlopen=cls.runner)), \
                mock.patch.object(investor_app, '_v28', SimpleNamespace(engine=SimpleNamespace(workspace=workspace))), \
                mock.patch.object(investor_app, '_v28_pool', cls.database):
            out = gate_replay.verify_versions(len(versions))
        cls.results = {r['version']: r for r in out['results']}

    def test_verify_versions_replays_a_content_site_as_production_judged_it(self):
        result = self.results[STORED[0]]
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['failing'], [])
        self.assertEqual(self.database.lookups[0], (STORED[0], 'tenant_x', 'tenant_x'))
        self.assertEqual(self.runner.build_ids.count('behavior-acceptance'), len(STORED))     # the acceptance really ran

    def test_verify_versions_keeps_the_strict_floor_for_a_version_without_a_contract(self):
        # Replayed right after the content site: it must not be judged by that version's scope, nor by a relaxed
        # one -- every kind of the full floor that its plan lacks is reported missing.
        result = self.results[STORED[1]]
        self.assertEqual(result['status'], 'FAIL', result)
        self.assertEqual(len(result['failing']), 1, result)
        self.assertTrue(result['failing'][0].startswith('BEHAVIOR: '), result)
        self.assertTrue(result['failing'][0].endswith(self.STRICT_FLOOR_MISSING), result)
        self.assertEqual(self.database.lookups[1], (STORED[1], 'tenant_x', 'tenant_x'))

if __name__ == '__main__':
    unittest.main()
