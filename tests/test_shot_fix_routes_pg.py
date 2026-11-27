"""Warehouse 124: a customer's screenshot, over the REAL served app and REAL PostgreSQL.

Run alone (investor_app reads its configuration once, at import):  python -m pytest -q tests/test_shot_fix_routes_pg.py
Needs M4D2_DATABASE_URL pointing at a database migrated with `python -m omni_prod.migrate`. Skipped, reported, without one.

What is proved, on the unmodified routes, workspace, attachment table, conversation store and modification repository (no model, no
queue: OMNI_REDIS_URL is a closed port; the vision model is the one double, a scripted reader, as the worker's gateway is in
tests/test_shot_fix_pg.py):
  * a screenshot of a finished build is stored whole -- the file as it came, its reduced copy, the window width, five evidence lines --
    and the build's own status route shows it, whatever the model did (here: nothing is connected, and the customer is told so);
  * with a model that answers an edit block, the reply carries one action; the click (the existing modifications route) stores the
    followup that carries exactly those edits, and the server's own record -- never the browser's text -- decides them;
  * another account gets the unknown-build answer on both routes and the unknown-fix answer on the apply; a fix of another
    version is refused; a bad width and a file that is not an image store nothing; a retried upload is one round."""
from __future__ import annotations

import base64
import os
import sys
import uuid
from unittest import mock

import pytest

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', '')


def _skip_reason() -> str | None:
    if not DATABASE_URL:
        return 'needs PostgreSQL (M4D2_DATABASE_URL), migrated with python -m omni_prod.migrate'
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            missing = [t for t in ('creator_projects', 'intake_messages', 'conversation_attachments', 'build_jobs')
                       if conn.execute('SELECT to_regclass(%s)', (f'public.{t}',)).fetchone()[0] is None]
    except Exception as exc:  # pragma: no cover - environment probe
        return f'no live Postgres at M4D2_DATABASE_URL: {exc}'
    if missing:
        return f'the database is not migrated (missing {missing}): run python -m omni_prod.migrate'
    if 'omni_prod.investor_app' in sys.modules:
        return 'omni_prod.investor_app was imported by another test in this process: run this file alone'
    return None


_SKIP = _skip_reason()
pytestmark = pytest.mark.skipif(_SKIP is not None, reason=str(_SKIP))
ORIGIN = 'https://testserver'
BROWSER = {'Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin'}

if _SKIP is None:
    for name in ('OMNI_ENV', 'OMNI_GENERATED_APP_TOKEN_SECRET', 'OMNI_INTAKE_MODEL', 'OMNI_INTAKE_VIA_WORKER', 'OMNI_S3_ENDPOINT',
                 'OMNI_S3_BUCKET', 'OMNI_MEDIA_READER', 'OMNI_SESSION_COOKIE_SECURE', 'OMNI_SHOT_FIX', 'OMNI_SHOT_FIX_PROJECT_USD',
                 *[n for n in os.environ if n.endswith(('_API_KEY', '_API_TOKEN'))]):
        os.environ.pop(name, None)
    os.environ.update({
        'VERCEL_ENV': 'production', 'OMNI_CREATOR_PERSISTENCE': 'postgres', 'OMNI_DATABASE_URL': DATABASE_URL,
        'OMNI_SECRET_KEY': 'shot-fix-routes-' + 'k' * 40, 'OMNI_ALLOWED_ORIGINS': ORIGIN,
        'OMNI_BILLING_ADMIN_KEY': 'shot-fix-routes-billing-admin-key', 'OMNI_REDIS_URL': 'redis://127.0.0.1:1/0',
        'PREVIEW_DOMAIN_TEMPLATE': 'https://{preview_id}.preview.148ai.test'})
    from fastapi.testclient import TestClient

    import app as served
    from omni_prod import investor_app as IA
    from omni_prod import shot_fix as SF
    from omni_prod.build_contract_repository import PostgresBuildContractRepository  # noqa: F401  (the app's own wiring)
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.memory_adapters import MemoryArtifactStore
    from omni_prod.product_spec import ProductSpec
    from omni_prod.spec_repository import PostgresSpecRepository
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.shot_fix_support import CSS, FIX_ANSWER, HTML, JS, Reader, png

    import hashlib

    from omni_prod.storage import StoredObject

    class ExactKeyStore(MemoryArtifactStore):
        """MemoryArtifactStore with S3ArtifactStore's signatures (get_bytes(key, verify=), put_bytes returning the StoredObject,
        an identical re-put a no-op, delete(key)), as tests/test_tenant_isolation_pg.py has it: a key that is not there raises."""

        def get_bytes(self, key, *, verify=True):
            return self.objects[key]

        def put_bytes(self, key, data):
            if self.objects.get(key) != bytes(data):
                super().put_bytes(key, data)
            return StoredObject(key=key, sha256=hashlib.sha256(bytes(data)).hexdigest(), size=len(data))

        def delete(self, key):
            del self.objects[key]

    IA._v28.engine.workspace = PostgresProjectWorkspace(IA._v28_pool, ExactKeyStore())
    FILES = {'index.html': HTML, 'style.css': CSS, 'app.js': JS, 'README.md': '# the site\n'}
    PNG = png(1500, 900)
    SPEC = ProductSpec.from_dict({
        'title': 'Salon', 'summary': 'A salon page', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'show the salon name', 'kind': 'functional', 'mandatory': True}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'the home page shows the name'}]})


def _browser():
    return TestClient(served.app, base_url=ORIGIN, raise_server_exceptions=True, headers=BROWSER)


class Customer:
    def __init__(self, name: str):
        self.browser = _browser()
        email = f'{name}-{uuid.uuid4().hex[:10]}@shotfix.example'
        reg = self.browser.post('/api/v28/auth/register', json={'email': email, 'password': 'Shot-fix-routes-123!'})
        assert reg.status_code == 200, reg.text[:300]
        self.token, self.account_id = reg.json()['token'], reg.json()['user']['id']
        sub = TestClient(served.app, raise_server_exceptions=False).post(
            '/api/v28/admin/subscription', json={'user_id': self.account_id, 'plan': 'business'},
            headers={'Authorization': 'Bearer ' + self.token, 'X-148AI-Billing-Admin-Key': 'shot-fix-routes-billing-admin-key'})
        assert sub.status_code == 200, sub.text[:300]
        self.project = self.browser.post('/api/v28/projects', json={'title': f'Project {name}'}).json()['id']
        _, self.key = IA._v28.resolve_project_key(token=self.token, project_id=self.project)
        workspace, pool = IA._v28.engine.workspace, IA._v28_pool
        self.files = {**FILES, 'owner.txt': name}                      # a repository is stored by its digest: each customer's is their own
        self.version = workspace.commit(project_id=self.key, repository=dict(self.files), message='first version').id
        PostgresSpecRepository(pool).save(version_id=self.version, project_id=self.key, spec=SPEC)
        self.build = self.new_build(self.version)
        self.empty_build = self.new_build(None)

    def new_build(self, version_id):
        build_id = f'bld_{uuid.uuid4().hex}'
        PostgresBuildRepository(IA._v28_pool).create(build_id=build_id, project_id=self.key, version_id=version_id or self.version)
        with IA._v28_pool.connection() as conn:
            with conn.transaction():
                conn.execute("UPDATE build_jobs SET status = 'READY', phase = 'DONE', result_version_id = %s WHERE id = %s",
                             (version_id, build_id))
        return build_id

    def shot(self, build=None, *, project=None, data=PNG, width=390, **kw):
        body = {'data_base64': base64.b64encode(data).decode(), 'viewport_width': width, **kw}
        return self.browser.post(f'/api/v28/projects/{project or self.project}/builds/{build or self.build}/shots?lang=he', json=body)

    def messages(self):
        return self.browser.get(f'/api/v28/projects/{self.project}/conversation').json()['messages']


def _sql(q, args=()):
    with IA._v28_pool.connection() as conn:
        return conn.execute(q, args).fetchall()


@pytest.fixture(scope='module')
def world():
    a, b = Customer('alice'), Customer('bob')
    yield {'A': a, 'B': b}
    IA._v28_pool.close()


def test_a_screenshot_is_stored_whole_even_when_no_model_is_connected_and_the_build_shows_it(world):
    a = world['A']
    r = a.shot(note='הכפתור נעלם')
    assert r.status_code == 200, r.text[:400]
    last = r.json()['messages'][-1]
    assert last['role'] == 'assistant' and last['actions'] == []
    assert last['content'] == SF.sentence('not_connected', 'he')                      # the next action, in Hebrew, nothing built
    # both images are in the attachment table, the original as it came
    images = a.browser.get(f'/api/v28/projects/{a.project}/attachments').json()['attachments']
    assert len(images) == 2 and {i['kind'] for i in images} == {'screenshot'}
    original = next(i for i in images if i['width'] == 1500)
    assert next(i for i in images if i['width'] != 1500)['width'] == 1400                  # the reduced copy: long side 1,400
    served_back = a.browser.get(f"/api/v28/projects/{a.project}/attachments/{original['id']}")
    assert served_back.status_code == 200 and served_back.content == PNG
    # the build's own status route carries the round: the width, both images, the five lines
    status = a.browser.get(f'/api/v28/projects/{a.project}/builds/{a.build}').json()
    shots = status['screenshots']
    assert len(shots) == 1 and shots[0]['viewport_width'] == 390 and shots[0]['build_id'] == a.build
    assert [line['stage'] for line in shots[0]['evidence']] == list(SF.STAGES)
    assert shots[0]['original']['attachment_id'] == original['id'] and shots[0]['original']['sha256'] == original['sha256']
    assert shots[0]['reduced']['width'] == 1400 and shots[0]['outcome'] == 'not_connected'
    assert a.browser.get(f'/api/v28/projects/{a.project}/builds/{a.build}/shots').json()['screenshots'] == shots


def test_a_fix_is_one_action_and_the_click_stores_exactly_those_edits(world):
    a = world['A']
    reader = Reader(FIX_ANSWER)
    with mock.patch.object(SF, 'reader_for', lambda *args, **kw: reader):
        r = a.shot(data=png(1600, 1000), width=430)
    assert r.status_code == 200, r.text[:400]
    actions = r.json()['messages'][-1]['actions']
    assert [x['type'] for x in actions] == ['apply_shot_fix']
    fix = actions[0]
    assert fix['build_id'] == a.build and fix['version_id'] == a.version and len(fix['fingerprint']) == 64
    call = reader.calls[0]
    assert call['user']['viewport_width'] == 430 and call['user']['build_id'] == a.build        # the width and the build id told to the model
    assert sorted(call['user']['files']) == ['app.js', 'index.html', 'style.css']                # this version's own files
    # the apply: the existing modifications route, with the stored fix's fingerprint and nothing of the browser's own edits
    ok = a.browser.post(f'/api/v28/projects/{a.project}/versions/{a.version}/modifications',
                        json={'followup': 'תיקון לפי הצילום', 'shot_fix': fix['fingerprint']})
    assert ok.status_code == 202, ok.text[:400]
    (stored,) = _sql('SELECT followup FROM modification_requests WHERE id = %s', (ok.json()['modification_id'],))[0]
    assert SF.edits_of(stored) == FIX_ANSWER['edits']                                           # exactly the model's edit block
    assert 'הכפתור יורד מתחת לקצה המסך בטלפון' in stored
    # a click with the browser's own text and no fingerprint is an ordinary change: the mark is not the browser's to write
    plain = a.browser.post(f'/api/v28/projects/{a.project}/versions/{a.version}/modifications', json={'followup': 'make the title bigger'})
    assert plain.status_code == 202
    (plain_followup,) = _sql('SELECT followup FROM modification_requests WHERE id = %s', (plain.json()['modification_id'],))[0]
    assert SF.edits_of(plain_followup) is None


def test_an_unknown_fix_or_a_fix_of_another_version_applies_nothing(world):
    a = world['A']
    with mock.patch.object(SF, 'reader_for', lambda *args, **kw: Reader(FIX_ANSWER)):
        fix = a.shot(data=png(1700, 1000), width=390).json()['messages'][-1]['actions'][0]
    before = _sql('SELECT count(*) FROM modification_requests WHERE project_id = %s', (a.key,))[0][0]
    unknown = a.browser.post(f'/api/v28/projects/{a.project}/versions/{a.version}/modifications',
                             json={'followup': 'תיקון לפי הצילום', 'shot_fix': 'e' * 64})
    assert unknown.status_code == 409 and unknown.json()['detail']['error'] == 'shot_fix_not_found'
    newer = IA._v28.engine.workspace.commit(project_id=a.key, repository={**a.files, 'about.html': '<p>x</p>'}, message='second').id
    PostgresSpecRepository(IA._v28_pool).save(version_id=newer, project_id=a.key, spec=SPEC)
    other_version = a.browser.post(f'/api/v28/projects/{a.project}/versions/{newer}/modifications',
                                   json={'followup': 'תיקון לפי הצילום', 'shot_fix': fix['fingerprint']})
    assert other_version.status_code == 409 and other_version.json()['detail']['error'] == 'shot_fix_not_found'
    assert _sql('SELECT count(*) FROM modification_requests WHERE project_id = %s', (a.key,))[0][0] == before
    bad = a.browser.post(f'/api/v28/projects/{a.project}/versions/{a.version}/modifications',
                         json={'followup': 'תיקון לפי הצילום', 'shot_fix': 'not-a-fingerprint'})
    assert bad.status_code == 422                                                             # a fingerprint is 64 hex characters


def test_another_account_gets_the_unknown_answers_and_cannot_apply_a_fix_it_did_not_make(world):
    a, b = world['A'], world['B']
    with mock.patch.object(SF, 'reader_for', lambda *args, **kw: Reader(FIX_ANSWER)):
        fix = a.shot(data=png(1800, 1000), width=390).json()['messages'][-1]['actions'][0]
    for project, build in ((a.project, a.build), (b.project, a.build)):                      # A's project, or B's own with A's build
        assert b.shot(build, project=project).status_code in (403, 404), project
        assert b.browser.get(f'/api/v28/projects/{project}/builds/{build}/shots').status_code in (403, 404)
    assert not any(m['actions'] and m['actions'][0].get('type') == 'apply_shot_fix' for m in b.messages())
    stolen = b.browser.post(f'/api/v28/projects/{b.project}/versions/{b.version}/modifications',
                            json={'followup': 'תיקון לפי הצילום', 'shot_fix': fix['fingerprint']})
    assert stolen.status_code == 409                                                          # B's own conversation holds no such fix
    assert _sql('SELECT count(*) FROM conversation_attachments WHERE project_id = %s AND account_id = %s',
                (b.project, b.account_id))[0][0] == 0


def test_a_bad_width_a_file_that_is_not_an_image_and_a_build_with_no_version_store_nothing(world):
    a = world['A']
    images_before = len(a.browser.get(f'/api/v28/projects/{a.project}/attachments').json()['attachments'])
    messages_before = len(a.messages())
    assert a.shot(width=100).status_code == 422
    assert a.shot(width=5000).status_code == 422
    bad = a.shot(data=b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    assert bad.status_code in (415, 422) and bad.json()['detail']['error'] in ('unsupported_type', 'empty')
    none = a.shot(a.empty_build)
    assert none.status_code == 409 and none.json()['detail']['error'] == 'build_has_no_version'
    assert len(a.browser.get(f'/api/v28/projects/{a.project}/attachments').json()['attachments']) == images_before
    assert len(a.messages()) == messages_before


def test_a_retried_upload_is_one_round(world):
    a = world['A']
    body = {'data_base64': base64.b64encode(png(1900, 1100)).decode(), 'viewport_width': 390, 'request_key': 'retry-' + uuid.uuid4().hex[:8]}
    url = f'/api/v28/projects/{a.project}/builds/{a.build}/shots?lang=he'
    first = a.browser.post(url, json=body)
    count = len(a.messages())
    images = len(a.browser.get(f'/api/v28/projects/{a.project}/attachments').json()['attachments'])
    again = a.browser.post(url, json=body)
    assert first.status_code == again.status_code == 200
    assert (len(a.messages()), len(a.browser.get(f'/api/v28/projects/{a.project}/attachments').json()['attachments'])) == (count, images)
