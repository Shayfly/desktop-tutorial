"""S4.5 (the owner's plan v3, 2026-11-25): one customer can never read or change another customer's data.

The REAL served app (app.py: omni_prod.investor_app plus the live_core router) runs over a REAL PostgreSQL
(M4D2_DATABASE_URL, migrated with `python -m omni_prod.migrate`) with the durable PostgresProjectWorkspace, in two
configurations:

  deployed  Vercel production's own: OMNI_ENV is NOT set (tests/fixtures/vercel_env_keys_148aiv28_2026_11_15.json has
            no OMNI_ENV; on 2026-11-26 09:19 UTC an unknown /api/v28 route answered 404 without credentials, where the
            production_auth middleware would have answered 401), VERCEL_ENV=production, OMNI_CREATOR_PERSISTENCE=postgres
            with OMNI_S3_* (durable, so the legacy in-process paths are refused by _async_build_mode, not by OMNI_ENV).
            The Bearer middleware is off and every route must check the session itself. Accounts sign in the way the
            web app does (omni_prod/assets/app.js: fetch with credentials 'same-origin', no Authorization header): the
            HttpOnly 148ai_session cookie set by /api/v28/auth/register, over https, with a same-origin Origin header.
  strict    the same process with OMNI_ENV=production for the duration of a test (production_auth on: a Bearer token
            on every non-public /api route); the matrix runs in both.
  v26, v27 and live_core have no cookie session: their accounts use a Bearer token in both configurations.

Two real accounts are registered through the real routes; account B then uses account A's identifiers on every route
that takes one (tests/tenant_isolation_routes.json, which tests/test_tenant_isolation_registry.py compares with the
app) and must get exactly the answer it gets for an identifier that does not exist -- never A's data, and never a change
to A's rows. An anonymous caller (no cookie, no token) gets only the unauthenticated answer from every non-public route.

Object storage: omni_prod has S3ArtifactStore (boto3, a real bucket) and the in-process
omni_prod.memory_adapters.MemoryArtifactStore. The workspace and the attachments here use the latter through ExactKeyStore
below: an object is reached by its exact key only, a missing key raises KeyError (S3's NoSuchKey), and every read is
recorded so a test can say whose objects a request touched. Nothing at the boundary is doubled: ownership is decided by
the unmodified route, platform and repository code. No model, provider or queue is called (OMNI_REDIS_URL points at a
closed port, so nothing can be enqueued).

Run alone -- investor_app reads its configuration once, at import:  python -m pytest -q tests/test_tenant_isolation_pg.py
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
import re
import secrets
import struct
import sys
import uuid
import zlib
from pathlib import Path

import pytest

from tests.evidence_notice import notice

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'tests' / 'tenant_isolation_routes.json').read_text(encoding='utf-8'))
DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', '')


def _skip_reason() -> str | None:
    if not DATABASE_URL:
        return 'needs PostgreSQL (M4D2_DATABASE_URL), migrated with python -m omni_prod.migrate'
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            missing = [t for t in ('creator_projects', 'conversation_attachments', 'preview_access_tokens', 'live_users',
                                   'm5_build_contracts', 'intake_messages')
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

ORIGIN = 'https://testserver'                  # the browser clients' own origin (TestClient base_url below)
BROWSER = {'Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin'}

if _SKIP is None:
    # Vercel production's names (values never read): no OMNI_ENV and no OMNI_GENERATED_APP_TOKEN_SECRET. Unset here
    # although production has them: OMNI_INTAKE_MODEL / OMNI_INTAKE_VIA_WORKER (they would send the conversation to a
    # paid model through the worker) and every provider key -- no route can reach a model or provider from this test.
    for name in ('OMNI_ENV', 'OMNI_GENERATED_APP_TOKEN_SECRET', 'OMNI_INTAKE_MODEL', 'OMNI_INTAKE_VIA_WORKER',
                 'OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_MEDIA_READER', 'OMNI_SESSION_COOKIE_SECURE',
                 *[n for n in os.environ if n.endswith(('_API_KEY', '_API_TOKEN'))]):
        os.environ.pop(name, None)
    os.environ.update({
        'VERCEL_ENV': 'production', 'OMNI_CREATOR_PERSISTENCE': 'postgres', 'OMNI_DATABASE_URL': DATABASE_URL,
        'OMNI_SECRET_KEY': 'tenant-isolation-control-plane-' + 'k' * 40,
        'OMNI_ALLOWED_ORIGINS': ORIGIN, 'OMNI_LIVE_ENABLED': '1',
        # set here, absent in production (each lets a probe reach a deeper check; absent, the route refuses everyone):
        'OMNI_BILLING_ADMIN_KEY': 'tenant-isolation-billing-admin-key',
        'OMNI_RIGHTS_REVIEW_KEY': 'tenant-isolation-rights-review-key',
        'PREVIEW_DOMAIN_TEMPLATE': 'https://{preview_id}.preview.148ai.test',
        'OMNI_REDIS_URL': 'redis://127.0.0.1:1/0',
    })
    from fastapi.testclient import TestClient

    import app as served                       # the Vercel entrypoint: investor_app + the live_core router
    from omni_prod import investor_app as IA
    from omni_prod.memory_adapters import MemoryArtifactStore
    from omni_prod.storage import StoredObject
    from omni_prod.workspace import PostgresProjectWorkspace

    class ExactKeyStore(MemoryArtifactStore):
        """omni_prod.memory_adapters.MemoryArtifactStore with S3ArtifactStore's signatures: get_bytes(key, verify=),
        put_bytes returns the StoredObject (key, sha256, size), an identical re-put is a no-op (S3 overwrites; a
        content-addressed key always carries the same bytes) and delete(key). No prefix match, no default: a key that
        is not there raises KeyError."""

        def __init__(self):
            super().__init__()
            self.reads: list[str] = []

        def get_bytes(self, key, *, verify=True):
            self.reads.append(key)
            return self.objects[key]

        def put_bytes(self, key, data):
            if self.objects.get(key) != bytes(data):
                super().put_bytes(key, data)
            return StoredObject(key=key, sha256=hashlib.sha256(bytes(data)).hexdigest(), size=len(data))

        def delete(self, key):
            del self.objects[key]

    STORE = ExactKeyStore()
    IA._v28.engine.workspace = PostgresProjectWorkspace(IA._v28_pool, STORE)


# ----------------------------------------------------------------------------------------------- the two customers

def _png(w=3, h=2) -> bytes:
    raw = b''.join(b'\x00' + b'\x22\x44\x66' * w for _ in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def _browser():
    """A browser of its own: https, its own cookie jar, and the headers a same-origin fetch sends. No Authorization."""
    return TestClient(served.app, base_url=ORIGIN, raise_server_exceptions=False, headers=BROWSER)


class Customer:
    def __init__(self, name: str):
        self.name = name
        self.marker = f'{name}-secret-{uuid.uuid4().hex[:12]}'
        self.ids: dict[str, str] = {}
        self.gen_ids: dict[str, dict[str, str]] = {}
        self.tokens: dict[str, str] = {}
        self.account: dict[str, str] = {}
        self.browser = _browser()          # signed in by the 148ai_session cookie, as the web app is

    def signed_in(self, gen: str, config: str, shared):
        """(client, headers) this customer uses: the cookie session for v28 in the deployed configuration (as the web
        app does), a Bearer token otherwise (strict: the middleware requires one; v26/v27/live have no cookie)."""
        if gen == 'v28' and config == 'deployed':
            return self.browser, {}
        return shared, self.headers(gen)

    def objects(self) -> set[str]:
        """This customer's objects now: the repositories of every version of the project, and the attachments."""
        with IA._v28_pool.connection() as conn:
            repositories = {r[0] for r in conn.execute('SELECT artifact_key FROM project_versions WHERE project_id = %s',
                                                       (self.ids['internal_key'],)).fetchall()}
        return repositories | {k for k in STORE.objects if k.startswith(f"attachments/{self.account['id']}/")}

    def headers(self, gen: str = 'v28') -> dict:
        return {'Authorization': 'Bearer ' + self.tokens[gen]}

    def ids_for(self, gen: str) -> dict[str, str]:
        """The identifiers of this customer's rows in one generation (legacy routes take v28 ids)."""
        return {**self.ids, **self.gen_ids.get(gen, {})} if gen in ('v26', 'v27', 'live') else dict(self.ids)

    def traces(self) -> list[str]:
        """Strings that only this customer's own data contains (never an identifier a caller sends)."""
        return [self.marker, self.account['id'], self.account['email'], self.ids['internal_key'],
                self.ids['attachment_sha256'], self.account['live_id'], *self.account['other_ids']]


def _ok(response, *codes):
    assert response.status_code in (codes or (200,)), (response.status_code, response.text[:500])
    return response.json() if response.headers.get('content-type', '').startswith('application/json') else response


def _register(client, customer: Customer) -> None:
    email = f'{customer.name.lower()}-{uuid.uuid4().hex[:10]}@tenant.example'
    password = 'Tenant-isolation-123!'
    reg = _ok(customer.browser.post('/api/v28/auth/register', json={'email': email, 'password': password}))
    assert customer.browser.cookies.get('148ai_session') == reg['token'], 'the register route set no session cookie'
    customer.tokens['v28'] = reg['token']
    customer.account = {'id': reg['user']['id'], 'email': email}
    _ok(client.post('/api/v28/admin/subscription', json={'user_id': reg['user']['id'], 'plan': 'business'},
                    headers={**customer.headers(), 'X-148AI-Billing-Admin-Key': 'tenant-isolation-billing-admin-key'}))
    customer.account['other_ids'] = []
    for gen in ('v26', 'v27'):
        other = _ok(client.post(f'/api/{gen}/auth/register', json={'email': f'{gen}-{email}', 'password': password}))
        customer.tokens[gen] = other['token']
        customer.account['other_ids'].append(other['user']['id'])
    live = _ok(client.post('/api/live/auth/register', json={'email': f'live-{email}', 'password': password}))
    customer.tokens['live'] = live['token']
    customer.account['live_id'] = live['user']['id']


def _seed_v28(client, customer: Customer) -> None:
    """Every kind of v28 row a route can name, written through the real routes or the real repository methods the
    worker uses (a build, a preview and a ready modification are produced by workers in production)."""
    from omni_prod.build_contract_repository import PostgresBuildContractRepository
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.modification_repository import PostgresModificationRepository
    from omni_prod.preview_repository import PostgresPreviewRepository
    from omni_prod.product_architect import ProductArchitect
    from omni_prod.product_spec import ProductSpec
    from omni_prod.spec_repository import PostgresSpecRepository

    web, pool = customer.browser, IA._v28_pool          # the routes are called with the cookie session
    pid = _ok(web.post('/api/v28/projects', json={'title': f'Project {customer.marker}'}))['id']
    _, key = IA._v28.resolve_project_key(token=customer.tokens['v28'], project_id=pid)
    customer.ids.update(project_id=pid, internal_key=key)
    _ok(web.post(f'/api/v28/projects/{pid}/discovery',
                    json={'prompt': f'A landing page for a bakery called {customer.marker}', 'mode': 'guided'}))
    _ok(web.post(f'/api/v28/projects/{pid}/conversation',
                    json={'message': f'The bakery is named {customer.marker} and sells bread'}))
    att = _ok(web.post(f'/api/v28/projects/{pid}/attachments',
                          json={'kind': 'image', 'data_base64': base64.b64encode(_png()).decode()}))
    customer.ids['attachment_id'] = att['id']
    customer.ids['attachment_sha256'] = att['sha256']

    spec = ProductSpec.from_dict({
        'title': f'Bakery {customer.marker}', 'summary': 'A bakery page', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'show the bakery name', 'kind': 'functional', 'mandatory': True}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'the home page shows the name'}],
    })
    files = {'index.html': f'<!doctype html><html><body><h1 id="title">{customer.marker}</h1></body></html>',
             'README.md': f'# {customer.marker}\n'}
    workspace = IA._v28.engine.workspace
    v1 = workspace.commit(project_id=key, repository=files, message='first version')
    PostgresSpecRepository(pool).save(version_id=v1.id, project_id=key, spec=spec)
    v2 = workspace.commit(project_id=key, repository={**files, 'about.html': f'<p>{customer.marker} about</p>'},
                          message='second version')
    PostgresSpecRepository(pool).save(version_id=v2.id, project_id=key, spec=spec)
    customer.ids.update(version_id=v2.id, first_version_id=v1.id)

    build_id = f'bld_{uuid.uuid4().hex}'
    PostgresBuildRepository(pool).create(build_id=build_id, project_id=key, version_id=v2.id)
    customer.ids['build_id'] = build_id

    preview_id = f'prv_{uuid.uuid4().hex}'
    previews = PostgresPreviewRepository(pool)
    previews.create(preview_id, key, v2.id, ttl_seconds=3600)
    assert previews.record_runtime(preview_id, container_id=f'c-{preview_id}', runtime_host='worker-test',
                                   host_port=40000, workdir=f'/tmp/{preview_id}', data_storage='temporary')
    assert previews.mark_running(preview_id, url=f'https://{preview_id.replace("_", "-")}.preview.148ai.test')
    customer.ids['preview_id'] = preview_id

    mods = PostgresModificationRepository(pool)
    modification_id = f'mod_{uuid.uuid4().hex}'
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                mods.create(cur, modification_id=modification_id, project_id=key, user_id=customer.account['id'],
                            source_version_id=v2.id, followup=f'Make the heading say {customer.marker} bigger')
                mods.create_outbox(cur, modification_id=modification_id)
    assert mods.transition_running(modification_id)
    assert mods.complete(modification_id, project_id=key, status='READY_FOR_REVIEW', classification='change_request',
                         classification_reason='tenant isolation seed', billable=True,
                         candidate_repository={**files, 'index.html': files['index.html'].replace('<h1', '<h1 class="big"')},
                         candidate_spec=spec)
    customer.ids['modification_id'] = modification_id

    contract = ProductArchitect().compile(f'Build a SaaS CRM with login for {customer.marker}', project_id=pid,
                                          contract_version=1)
    PostgresBuildContractRepository(pool).save(contract)
    customer.ids['build_contract_id'] = contract.id

    sessions = _ok(web.get('/api/v28/auth/sessions'))['sessions']
    customer.ids['session_id'] = sessions[0]['session_id']


def _zip(files: dict[str, str]) -> bytes:
    import io
    import zipfile
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return out.getvalue()


def _seed_other_generations(client, customer: Customer, *, with_evidence: bool) -> None:
    """v26 and v27 (in-memory control planes, still mounted) and live_core (/api/live/*, its own Postgres tables)."""
    from live_core.postgres_store import PostgresStore
    for gen in ('v26', 'v27'):
        h = customer.headers(gen)
        customer.gen_ids[gen] = {'project_id': _ok(client.post(f'/api/{gen}/projects', headers=h,
                                                               json={'title': f'{gen} {customer.marker}'}))['id'],
                                 'version_id': _fresh('version_id')}   # every build of v26/v27 is refused: no version
    if with_evidence:   # evidence ids are a per-project sequence (evidence-001...), so only A has one
        evidence = _ok(client.post(f"/api/v27/projects/{customer.gen_ids['v27']['project_id']}/rights/evidence",
                                   headers=customer.headers('v27'),
                                   json={'right_kind': 'copyright', 'subject': f'logo {customer.marker}',
                                         'evidence_type': 'license', 'scope': 'web'}))
        customer.gen_ids['v27']['evidence_id'] = evidence['record']['id']
    store = PostgresStore(DATABASE_URL)
    uid = customer.account['live_id']
    project = store.create_project(uid, f'Live {customer.marker}')
    blob = _zip({'index.html': f'<h1>{customer.marker}</h1>', 'app.js': 'console.log(1)'})
    artifact = store.create_artifact(uid, project.id, hashlib.sha256(blob).hexdigest(), blob)
    version = store.create_version(uid, project.id, artifact.id, f'first {customer.marker}')
    store.set_active_version(project.id, uid, version.id)
    build = store.create_build(uid, project.id, f'build {customer.marker}')
    handle = _ok(client.post(f'/api/live/projects/{project.id}/versions/{version.id}/preview',
                             headers=customer.headers('live')))['preview_id']
    customer.gen_ids['live'] = {'project_id': project.id, 'version_id': version.id, 'build_id': build.id,
                                'artifact_id': artifact.id, 'live_preview_handle': handle}


@pytest.fixture(scope='module')
def world():
    client = TestClient(served.app, raise_server_exceptions=False)
    a, b = Customer('Alice'), Customer('Bob')
    for customer in (a, b):
        _register(client, customer)
        _seed_v28(client, customer)
        _seed_other_generations(client, customer, with_evidence=customer is a)
        customer.ids['bare_project_id'] = _ok(customer.browser.post('/api/v28/projects',
                                                                    json={'title': 'Nothing in it yet'}))['id']
        customer.ids['draft_fingerprint'] = secrets.token_hex(32)   # no reading draft exists (the reader is off)
        customer.ids['deployment_id'] = f'dep_{uuid.uuid4().hex[:12]}'
        customer.ids['account_id'] = customer.account['id']
    assert a.objects() and b.objects() and not a.objects() & b.objects()
    yield {'client': client, 'A': a, 'B': b, 'anonymous': _browser()}
    IA._v28_pool.close()


_SHAPES = {
    'project_id': lambda gen: str(uuid.uuid4()) if gen == 'live' else 'prj_' + secrets.token_urlsafe(10),
    'version_id': lambda gen: str(uuid.uuid4()) if gen == 'live' else f'v_{uuid.uuid4().hex[:16]}',
    'first_version_id': lambda gen: f'v_{uuid.uuid4().hex[:16]}',
    'build_id': lambda gen: str(uuid.uuid4()) if gen == 'live' else f'bld_{uuid.uuid4().hex}',
    'preview_id': lambda gen: f'prv_{uuid.uuid4().hex}', 'modification_id': lambda gen: f'mod_{uuid.uuid4().hex}',
    'attachment_id': lambda gen: f'att_{uuid.uuid4().hex}', 'build_contract_id': lambda gen: 'bc_' + uuid.uuid4().hex[:24],
    'session_id': lambda gen: 'ses_' + secrets.token_urlsafe(18), 'draft_fingerprint': lambda gen: secrets.token_hex(32),
    'evidence_id': lambda gen: f'evidence-{secrets.randbelow(10 ** 6):06d}', 'account_id': lambda gen: 'usr_' + secrets.token_urlsafe(12),
    'deployment_id': lambda gen: f'dep_{uuid.uuid4().hex[:12]}',
    'live_preview_handle': lambda gen: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='),
}


def _fresh(name: str, gen: str = 'v28') -> str:
    """An identifier of the same shape that names nothing."""
    return _SHAPES[name](gen)


# Read only from production (Neon 148ai-db-v2, 2026-11-26, SET TRANSACTION READ ONLY, aggregates only -- no row, no
# personal data): the prefix and the length of every identifier kind; 37/37 version artifacts are
# repositories/<sha256>.zip; 28/28 attachments lie under attachments/<account>/<project>/; the md5 of the column list of
# the ten tables the routes read was 962bd37ea6d59c17f7a029345ac71868, the same as this migrated database's.
PRODUCTION_SHAPES = {'project_id': ('prj_', 18), 'session_id': ('ses_', 28), 'version_id': ('v_', 18),
                     'internal_key': ('tenant_', 31), 'build_id': ('bld_', 36), 'preview_id': ('prv_', 36),
                     'modification_id': ('mod_', 36), 'build_contract_id': ('bc_', 27), 'attachment_id': ('att_', 36)}
PRODUCTION_COLUMNS_MD5 = '962bd37ea6d59c17f7a029345ac71868'
_COLUMNS_SQL = ("SELECT md5(string_agg(t, ',' ORDER BY t)) FROM (SELECT table_name || '.' || column_name t FROM "
                "information_schema.columns WHERE table_schema='public' AND table_name IN ('creator_projects',"
                "'project_versions','build_jobs','project_previews','preview_access_tokens','conversation_attachments',"
                "'m5_build_contracts','modification_requests','intake_messages','project_briefs')) s")


def test_the_identifiers_have_the_shape_production_uses(world):
    """An unknown id is only a fair comparison if it looks like a real one: every seeded id and every fresh id has the
    prefix and length production's rows have."""
    for name, (prefix, length) in PRODUCTION_SHAPES.items():
        for value in (world['A'].ids[name], *((_fresh(name),) if name in _SHAPES else ())):
            assert value.startswith(prefix) and len(value) == length, (name, value, prefix, length)
    with IA._v28_pool.connection() as conn:
        columns = conn.execute(_COLUMNS_SQL).fetchone()[0]
    # A migration that adds a column changes this before production has it: said out loud, not failed.
    notice('tenant isolation schema', f'columns md5 {columns}, production on 2026-11-26 {PRODUCTION_COLUMNS_MD5}: '
                                      f'{"equal" if columns == PRODUCTION_COLUMNS_MD5 else "DIFFERENT"}')


_VOLATILE_HEADERS = {'date', 'x-request-id', 'content-length'}   # differ between any two requests


def _normalized(response, supplied: dict[str, str]):
    """Status, headers and body, with every identifier the caller supplied replaced by its name (an echo of the
    caller's own input is not a difference). Only the date, the request id and the length are left out."""
    def clean(text: str) -> str:
        for name, value in sorted(supplied.items(), key=lambda kv: -len(kv[1])):
            text = text.replace(value, f'<{name}>')
        return text
    headers = sorted((k.lower(), clean(v)) for k, v in response.headers.items() if k.lower() not in _VOLATILE_HEADERS)
    return response.status_code, headers, clean(response.text)


# ------------------------------------------------------------------------------------- build contract identifiers

def test_a_foreign_build_contract_id_is_answered_like_an_unknown_one(world):
    """LEAK FOUND 2026-11-26: POST .../builds with another project's build_contract_id answered 403 "build contract
    does not belong to project", and with an unknown id 500 -- an oracle for which contract ids exist elsewhere. B's
    own project and A's contract id must get B's answer for an id that names nothing: a 409 that says to plan again."""
    a, b = world['A'], world['B']
    # A project of B's own with no active build: a queued build is answered before the contract is read.
    own = _ok(b.browser.post('/api/v28/projects', json={'title': 'Bob, no build yet'}))['id']
    path = f'/api/v28/projects/{own}/builds'
    foreign_id, missing_id = a.ids['build_contract_id'], _fresh('build_contract_id')
    foreign = b.browser.post(path, json={'prompt': 'Build a CRM app', 'build_contract_id': foreign_id})
    missing = b.browser.post(path, json={'prompt': 'Build a CRM app', 'build_contract_id': missing_id})
    assert _normalized(foreign, {'build_contract_id': foreign_id}) == _normalized(missing, {'build_contract_id': missing_id})
    assert foreign.status_code == 409, (foreign.status_code, foreign.text)
    assert foreign.json()['detail']['error'] == 'build_contract_invalid'
    assert a.marker not in foreign.text


def test_the_contract_repositories_do_not_tell_a_foreign_contract_from_a_missing_one(world):
    from omni_prod.build_contract_repository import (BuildContractNotFound, MemoryBuildContractRepository,
                                                     PostgresBuildContractRepository)
    from omni_prod.product_architect import ProductArchitect
    a, b = world['A'], world['B']
    postgres = PostgresBuildContractRepository(IA._v28_pool)
    memory = MemoryBuildContractRepository()
    memory.save(ProductArchitect().compile('Build a SaaS CRM with login', project_id=a.ids['project_id'], contract_version=1))
    memory_foreign = memory.latest(a.ids['project_id']).id
    for repo, foreign_id in ((postgres, a.ids['build_contract_id']), (memory, memory_foreign)):
        outcomes = []
        for contract_id in (foreign_id, _fresh('build_contract_id')):
            with pytest.raises(BuildContractNotFound) as caught:
                repo.get(contract_id, project_id=b.ids['project_id'])
            outcomes.append((type(caught.value), str(caught.value).replace(contract_id, '<id>')))
        assert outcomes[0] == outcomes[1], (type(repo).__name__, outcomes)
    assert postgres.get(a.ids['build_contract_id'], project_id=a.ids['project_id']).id == a.ids['build_contract_id']


# ------------------------------------------------------------------------------------------- the route matrix

def _canonical(name: str, spec: dict) -> str:
    return (spec.get('param_map') or {}).get(name) or REGISTRY['aliases'].get(name, name)


def _fill(value, ids: dict[str, str]):
    extra = {'png_base64': base64.b64encode(_png()).decode(), 'rights_review_key': os.environ['OMNI_RIGHTS_REVIEW_KEY']}
    if isinstance(value, str):
        return re.sub(r'\{(\w+)\}', lambda m: ids[m.group(1)] if m.group(1) in ids else extra[m.group(1)], value)
    if isinstance(value, list):
        return [_fill(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, ids) for k, v in value.items()}
    return value


_NOT_AN_ID = {'engine': 'godot', 'platform': 'android', 'collection': 'items', 'path': 'index.html'}


def _request(client, key: str, spec: dict, ids: dict[str, str], headers: dict):
    method, template = key.split(' ', 1)
    path = re.sub(r'\{(\w+)(?::\w+)?\}',
                  lambda m: ids.get(_canonical(m.group(1), spec)) or _NOT_AN_ID[m.group(1)], template)
    return client.request(method, path, params=_fill(spec.get('query'), ids), json=_fill(spec.get('body'), ids),
                          headers={**headers, **_fill(spec.get('headers') or {}, ids)})


def _assert_no_trace(owner: Customer, response, what: str) -> None:
    body = response.content
    for trace in owner.traces():
        assert trace.encode() not in body, f'{what}: the answer carries {owner.name}\'s data ({trace[:24]}...)'


_STATE_SQL = {
    'creator_projects': 'owner_id = %(account)s', 'creator_sessions': 'user_id = %(account)s',
    'project_briefs': 'project_id = %(project)s', 'intake_messages': 'project_id = %(project)s',
    'execution_plans': 'project_id = %(project)s', 'conversation_attachments': 'account_id = %(account)s',
    'project_versions': 'project_id = %(key)s', 'project_version_specs': 'project_id = %(key)s',
    'build_jobs': 'project_id = %(key)s', 'project_previews': 'project_id = %(key)s',
    'preview_access_tokens': 'preview_id IN (SELECT id FROM project_previews WHERE project_id = %(key)s)',
    'modification_requests': 'project_id = %(key)s', 'credit_reservations': 'project_id = %(key)s',
    'm5_build_contracts': 'project_id = %(project)s', 'build_approvals': 'project_id = %(project)s',
    'live_projects': 'owner_id = %(live)s', 'live_versions': 'owner_id = %(live)s',
    'live_builds': 'owner_id = %(live)s', 'live_artifacts': 'owner_id = %(live)s', 'live_sessions': 'user_id = %(live)s',
    # the account itself and everything else keyed by the account, the public id or the internal key
    'creator_accounts': 'id = %(account)s', 'creator_subscriptions': 'user_id = %(account)s',
    'creator_consents': 'user_id = %(account)s', 'creator_privacy_requests': 'user_id = %(account)s',
    'creator_identity_tokens': 'user_id = %(account)s', 'project_memory': 'project_id IN (%(project)s, %(key)s)',
    'modification_candidates': 'project_id = %(key)s',
    'build_requests': 'user_id = %(account)s OR internal_project_id = %(key)s OR public_project_id = %(project)s',
    'credit_ledger': 'account_id = %(account)s OR project_id IN (%(project)s, %(key)s)',
    'intake_reservations': 'account_id = %(account)s OR project_id IN (%(project)s, %(key)s)',
    'usage_events': 'account_id = %(account)s OR project_id IN (%(project)s, %(key)s)',
    'agent_memory': 'project_id IN (%(project)s, %(key)s)',
    'build_events': 'build_id IN (SELECT id FROM build_jobs WHERE project_id = %(key)s '
                    'UNION SELECT id FROM modification_requests WHERE project_id = %(key)s)',
}
_V28_MEMORY = ('_project_brand_visible', '_project_white_label', '_rights_evidence', '_rights_assessment',
               '_rights_prompt', '_rights_markets')   # V28Platform's in-process state, keyed by the internal key


def _state(owner: Customer) -> dict:
    """Every row and object that belongs to `owner`, as digests: a request by anyone else must leave it equal."""
    args = {'account': owner.account['id'], 'project': owner.ids['project_id'], 'key': owner.ids['internal_key'],
            'live': owner.account['live_id']}
    out = {}
    with IA._v28_pool.connection() as conn:
        for table, where in _STATE_SQL.items():
            out[table] = conn.execute(f"SELECT count(*), md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) "
                                      f"FROM {table} t WHERE {where}", args).fetchone()
    mine = owner.objects()
    out['objects'] = sorted((k, hashlib.sha256(v).hexdigest()) for k, v in STORE.objects.items() if k in mine)
    for gen, platform in (('v26', IA._v26), ('v27', IA._v27)):
        account = platform.account(owner.tokens[gen])
        out[gen] = sorted(repr(p) for p in platform.accounts.list_projects(owner_id=account.id))
        key = platform.accounts.internal_project_key(owner_id=account.id, project_id=owner.gen_ids[gen]['project_id'])
        out[gen + '_evidence'] = repr(getattr(platform, '_rights_evidence', {}).get(key))
    out['v28_memory'] = [repr(getattr(IA._v28, name, {}).get(owner.ids['internal_key'])) for name in _V28_MEMORY]
    return out


MATRIX = sorted(k for k, e in REGISTRY['routes'].items()
                if e['kind'] in ('tenant', 'admin', 'legacy_refused'))


def _validation_error(response) -> bool:
    """FastAPI's own 422 (the body never reached the route), not a route's 422."""
    try:
        return response.status_code == 422 and isinstance(response.json().get('detail'), list)
    except ValueError:
        return False


CONFIGS = ('deployed', 'strict')


@contextmanager
def _configured(config: str):
    """deployed: OMNI_ENV unset, as in Vercel production; strict: OMNI_ENV=production (production_auth on). Both
    middlewares read OMNI_ENV on every request, so one process serves both."""
    saved = os.environ.pop('OMNI_ENV', None)
    if config == 'strict':
        os.environ['OMNI_ENV'] = 'production'
    try:
        yield
    finally:
        os.environ.pop('OMNI_ENV', None)
        if saved is not None:
            os.environ['OMNI_ENV'] = saved


@pytest.mark.parametrize('config', CONFIGS)
@pytest.mark.parametrize('key', MATRIX)
def test_another_account_gets_the_unknown_id_answer(world, key, config):
    """B sends A's identifiers, then identifiers that name nothing, and must get the same answer -- status, headers and
    body (no existence leak) -- with nothing of A's in it; then B's own project with A's child identifier (version,
    build, preview, ...) against an unknown one. A's rows and objects are unchanged and B's requests read none of A's
    objects. Last, A's own request gets past the ownership check (an answer other than B's refusal)."""
    with _configured(config):
        _matrix(world, key, config)


def _matrix(world, key, config):
    spec = REGISTRY['routes'][key]
    gen, names = spec['world'], spec['ids']
    a, b = world['A'], world['B']
    a_ids, b_ids = a.ids_for(gen), b.ids_for(gen)
    a_client, a_auth = a.signed_in(gen, config, world['client'])
    b_client, b_auth = b.signed_in(gen, config, world['client'])
    before, reads = _state(a), len(STORE.reads)

    foreign = {n: a_ids[n] for n in names}
    missing = {n: _fresh(n, gen) for n in names}
    got_foreign = _request(b_client, key, spec, foreign, b_auth)
    got_missing = _request(b_client, key, spec, missing, b_auth)
    seen = [f'B with A ids {got_foreign.status_code} {_short(got_foreign)}']
    assert not _validation_error(got_foreign), f'{key}: the probe body never reaches the route ({got_foreign.text[:300]})'
    assert _normalized(got_foreign, foreign) == _normalized(got_missing, missing), \
        f'{key}: A\'s identifiers are answered differently from unknown ones'
    _assert_no_trace(a, got_foreign, key)

    for child in spec.get('child', []):
        own = {n: b_ids[n] for n in names if n != child}
        if spec.get('own_parent') == 'bare':
            own['project_id'] = b_ids['bare_project_id']
        with_foreign, with_missing = {**own, child: a_ids[child]}, {**own, child: _fresh(child, gen)}
        got_foreign = _request(b_client, key, spec, with_foreign, b_auth)
        got_missing = _request(b_client, key, spec, with_missing, b_auth)
        assert not _validation_error(got_foreign), f'{key} ({child}): {got_foreign.text[:300]}'
        assert _normalized(got_foreign, {child: a_ids[child]}) == _normalized(got_missing, {child: with_missing[child]}), \
            f'{key}: B\'s own project with A\'s {child} is answered differently from an unknown {child}'
        _assert_no_trace(a, got_foreign, f'{key} ({child})')
        seen.append(f'B own project + A {child} {got_foreign.status_code} {_short(got_foreign)}')

    assert _state(a) == before, f'{key}: a request by B changed A\'s rows or objects'
    touched = sorted(set(STORE.reads[reads:]) & a.objects())
    assert not touched, f'{key}: B\'s requests read A\'s objects {touched}'

    if spec['kind'] == 'legacy_refused':
        for who, (who_client, who_auth) in ((a, (a_client, a_auth)), (b, (b_client, b_auth))):
            got = _request(who_client, key, spec, foreign, who_auth)
            assert got.status_code == spec['refused'], (key, who.name, got.status_code, got.text[:300])
        seen.append(f'owner refused too {got.status_code}')
    elif isinstance(spec.get('owner'), list):
        got = _request(a_client, key, spec, foreign, a_auth)
        assert got.status_code in spec['owner'], (key, 'owner', got.status_code, got.text[:300])
        refused = _request(b_client, key, spec, foreign, b_auth)
        assert (got.status_code, got.content) != (refused.status_code, refused.content), \
            f'{key}: the owner gets the refusal another account gets'
        seen.append(f'owner {got.status_code} {_short(got)}')
    notice('tenant isolation', f'{config} {key}: ' + ' | '.join(seen))


def _short(response) -> str:
    kind = response.headers.get('content-type', '')
    if not kind.startswith('application/json'):
        return f'[{kind.split(";")[0] or "no type"} {len(response.content)} bytes]'
    return re.sub(r'\s+', ' ', response.text)[:90]


# ------------------------------------------------------------- the owner's destructive calls, on rows of their own

def _ready_modification(customer: Customer, *, status: str = 'READY_FOR_REVIEW') -> str:
    from omni_prod.modification_repository import PostgresModificationRepository
    from omni_prod.spec_repository import PostgresSpecRepository
    pool, key, source = IA._v28_pool, customer.ids['internal_key'], customer.ids['version_id']
    mods = PostgresModificationRepository(pool)
    modification_id = f'mod_{uuid.uuid4().hex}'
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                mods.create(cur, modification_id=modification_id, project_id=key, user_id=customer.account['id'],
                            source_version_id=source, followup='Make the heading bigger')
                mods.create_outbox(cur, modification_id=modification_id)
    if status == 'QUEUED':
        return modification_id
    repo = IA._v28.engine.workspace.get(project_id=key, version_id=source).repository()
    assert mods.transition_running(modification_id)
    assert mods.complete(modification_id, project_id=key, status='READY_FOR_REVIEW', classification='change_request',
                         classification_reason='tenant isolation', billable=True,
                         candidate_repository={**repo, 'extra.html': '<p>more</p>'},
                         candidate_spec=PostgresSpecRepository(pool).get(source, key))
    return modification_id


DESTRUCTIVE = sorted(k for k, e in REGISTRY['routes'].items() if e.get('owner') == 'destructive')
NOT_RUN_FOR_THE_OWNER = {'POST /api/live/builds/{build_id}/run': 'runs the generator (a model call); another account '
                                                                  'is refused before it in the matrix'}


def test_the_destructive_routes_work_for_their_owner(world):
    """The matrix leaves A's rows alone, so the routes that delete, cancel, revoke or change state are shown to work for
    their owner here, on a third customer's own fresh rows -- the refusals are not routes that refuse everyone. Carol
    signs in with the cookie session, as the web app does (deployed configuration)."""
    client = world['client']
    c = Customer('Carol')
    _register(client, c)
    _seed_v28(client, c)
    web, pid = c.browser, c.ids['project_id']
    done = {}

    def call(key, path, expect, **kw):
        method = key.split(' ', 1)[0]
        got = web.request(method, path, **kw)
        assert got.status_code in expect, (key, got.status_code, got.text[:300])
        done[key] = got
        return got

    call('POST /api/v28/projects/{project_id}/builds/{build_id}/cancel',
         f"/api/v28/projects/{pid}/builds/{c.ids['build_id']}/cancel", (200,))
    assert done['POST /api/v28/projects/{project_id}/builds/{build_id}/cancel'].json()['outcome'] in ('cancelled', 'cancel_requested')
    call('DELETE /api/v28/projects/{project_id}/previews/{preview_id}',
         f"/api/v28/projects/{pid}/previews/{c.ids['preview_id']}", (200, 202, 503))
    assert _ok(web.get(f"/api/v28/projects/{pid}/previews/{c.ids['preview_id']}"))['status'] == 'STOPPED'
    call('POST /api/v28/projects/{project_id}/modifications/{modification_id}/reject',
         f"/api/v28/projects/{pid}/modifications/{c.ids['modification_id']}/reject", (200,), json={'reason': 'no'})
    call('POST /api/v28/projects/{project_id}/modifications/{modification_id}/accept',
         f"/api/v28/projects/{pid}/modifications/{_ready_modification(c)}/accept", (200,), json={'message': 'yes'})
    call('POST /api/v28/projects/{project_id}/modifications/{modification_id}/cancel',
         f"/api/v28/projects/{pid}/modifications/{_ready_modification(c, status='QUEUED')}/cancel", (200,))
    key_before = {k for k in STORE.objects if k.startswith(f"attachments/{c.account['id']}/")}
    call('DELETE /api/v28/projects/{project_id}/attachments/{attachment_id}',
         f"/api/v28/projects/{pid}/attachments/{c.ids['attachment_id']}", (200,))
    assert key_before and not key_before & set(STORE.objects), 'the attachment\'s object is not gone'
    other_device = _browser()
    _ok(other_device.post('/api/v28/auth/login', json={'email': c.account['email'], 'password': 'Tenant-isolation-123!'}))
    assert other_device.get('/api/v28/me').status_code == 200
    session = [s for s in _ok(web.get('/api/v28/auth/sessions'))['sessions']
               if s['session_id'] != c.ids['session_id']][0]['session_id']
    call('POST /api/v28/auth/sessions/{session_id}/revoke', f'/api/v28/auth/sessions/{session}/revoke', (200,))
    assert other_device.get('/api/v28/me').status_code == 401              # that device's cookie no longer signs in
    call('PATCH /api/v28/projects/{project_id}', f'/api/v28/projects/{pid}', (200,), json={'title': 'Carol renamed'})
    call('POST /api/v28/projects/{project_id}/archive', f'/api/v28/projects/{pid}/archive', (200,))
    call('POST /api/v28/projects/{project_id}/unarchive', f'/api/v28/projects/{pid}/unarchive', (200,))
    call('DELETE /api/v28/projects/{project_id}', f'/api/v28/projects/{pid}', (202,))
    assert web.get(f'/api/v28/projects/{pid}/state').json()['deleted_at']
    assert set(done) | set(NOT_RUN_FOR_THE_OWNER) == set(DESTRUCTIVE), sorted(set(DESTRUCTIVE) ^ (set(done) | set(NOT_RUN_FOR_THE_OWNER)))


# --------------------------------------------------------------------------- listings and the caller's own account

def _gen_of(path: str) -> str:
    return next((g for g in ('v26', 'v27', 'live') if path.startswith(f'/api/{g}/')), 'v28')


def _served_routes() -> dict:
    from fastapi.routing import APIRoute, APIWebSocketRoute
    out = {}
    for r in served.app.routes:
        if isinstance(r, APIRoute) or type(r).__name__ == 'Route':
            out.update({f'{m} {r.path}': r for m in r.methods})
        elif isinstance(r, APIWebSocketRoute):
            out[f'WS {r.path}'] = r
        elif type(r).__name__ == 'Mount':
            out[f'MOUNT {r.path}'] = r
    return out


def _probe_value(annotation, owner: Customer):
    """A value of the field's type that carries another customer's identifiers wherever text goes."""
    import enum
    import types
    import typing
    from pydantic import BaseModel
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if origin in (typing.Union, types.UnionType):
        return _probe_value(next(t for t in args if t is not type(None)), owner)
    if origin is typing.Literal:
        return args[0]
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return next(iter(annotation)).value
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {name: _probe_value(f.annotation, owner) for name, f in annotation.model_fields.items()}
    if origin in (list, tuple, set, frozenset) or annotation in (list, tuple, set):
        return [_probe_value(args[0] if args else str, owner)]
    if origin is dict or annotation is dict:
        return {name: owner.ids[name] for name in ('project_id', 'version_id', 'build_id', 'preview_id')}
    if annotation is bool:
        return False
    if annotation in (int, float):
        return 1
    return owner.ids['project_id']


_FIXED_PATH = {'platform': 'android', 'engine': 'godot', 'asset_name': '148ai-logo-64.png', 'department_id': 'engineering'}


def _probe_call(client, key: str, owner: Customer, headers: dict):
    """Call a route that takes no customer identifier with every text field and query parameter set to `owner`'s
    project id (and every free-form object to `owner`'s ids): a route that uses one of them to look a row up shows it."""
    method, template = key.split(' ', 1)
    route = SERVED[key]
    dependant = getattr(route, 'dependant', None)
    path = re.sub(r'\{(\w+)(?::\w+)?\}', lambda m: _FIXED_PATH.get(m.group(1), owner.ids['project_id']), template)
    query, body = {}, None
    if dependant is not None:
        query = {p.name: _probe_value(p.field_info.annotation, owner) for p in dependant.query_params}
        params = dependant.body_params
        if len(params) == 1 and not getattr(params[0].field_info, 'embed', False) and \
                hasattr(params[0].field_info.annotation, 'model_fields'):
            body = _probe_value(params[0].field_info.annotation, owner)
        elif params:
            body = {p.alias or p.name: _probe_value(p.field_info.annotation, owner) for p in params}
    return client.request(method, path, params=query, json=body, headers=headers)


if _SKIP is None:
    SERVED = _served_routes()
SWEEP = sorted(k for k, e in REGISTRY['routes'].items() if e['kind'] in ('account', 'public') and not k.startswith('MOUNT'))


def _throwaway(world, gen: str):
    """A fresh account of `gen` for a call that may change or end the caller's own session (logout, deletion)."""
    t = Customer('Mallory')
    email = f'mallory-{uuid.uuid4().hex[:10]}@tenant.example'
    if gen == 'v28':
        _ok(t.browser.post('/api/v28/auth/register', json={'email': email, 'password': 'Tenant-isolation-123!'}))
        return t.browser, {}
    prefix = '/api/live' if gen == 'live' else f'/api/{gen}'
    token = _ok(world['client'].post(f'{prefix}/auth/register', json={'email': email, 'password': 'Tenant-isolation-123!'}))['token']
    return world['client'], {'Authorization': 'Bearer ' + token}


@pytest.mark.parametrize('key', SWEEP)
def test_account_and_public_routes_never_show_another_customer(world, key):
    """Every method of every route that takes no customer identifier, called by another account (a fresh one when the
    call may change the caller's own account) or, for a public route, by an anonymous browser -- with A's ids in every
    text field: nothing of A's comes back. Deployed configuration, the cookie session for v28."""
    a, b = world['A'], world['B']
    method, template = key.split(' ', 1)
    gen = _gen_of(template)
    if REGISTRY['routes'][key]['kind'] == 'public':
        client, auth = world['anonymous'], {}
        client.cookies.clear()
    elif method in ('GET', 'HEAD'):
        client, auth = b.signed_in(gen, 'deployed', world['client'])
    else:
        client, auth = _throwaway(world, gen)
    before = _state(a)
    got = _probe_call(client, key, a, auth)
    _assert_no_trace(a, got, key)
    assert _state(a) == before, f'{key}: a call by another account changed A\'s rows'
    if client is world['anonymous']:
        client.cookies.clear()


def test_listings_and_search_show_only_the_callers_own_projects(world):
    client, a, b = world['client'], world['A'], world['B']
    for gen, listing in (('v28', '/api/v28/projects'), ('v26', '/api/v26/projects'), ('v27', '/api/v27/projects'),
                         ('live', '/api/live/projects')):
        mine = {p['id'] for p in _ok(_get(a, gen, client, listing))['projects']}
        theirs = {p['id'] for p in _ok(_get(b, gen, client, listing))['projects']}
        assert a.ids_for(gen)['project_id'] in mine and not mine & theirs, (gen, mine, theirs)
    search = '/api/v28/projects/search'
    assert _ok(b.browser.get(search, params={'q': a.marker, 'include_archived': True}))['projects'] == []
    assert [p['id'] for p in _ok(a.browser.get(search, params={'q': a.marker}))['projects']] == [a.ids['project_id']]
    sessions = _ok(b.browser.get('/api/v28/auth/sessions'))['sessions']
    assert a.ids['session_id'] not in {s['session_id'] for s in sessions}


def _get(customer: Customer, gen: str, shared, path: str, **kw):
    client, auth = customer.signed_in(gen, 'deployed', shared)
    return client.get(path, headers=auth, **kw)


def test_signing_in_does_not_tell_whether_an_account_exists(world):
    """A's email with a wrong password is answered exactly like an email nobody registered (v28, v26, v27, live), and
    a password reset for A's email like one for an unknown email."""
    a, anon = world['A'], world['anonymous']
    unknown = f'nobody-{uuid.uuid4().hex[:10]}@tenant.example'
    for prefix, email in (('/api/v28', a.account['email']), ('/api/v26', 'v26-' + a.account['email']),
                          ('/api/v27', 'v27-' + a.account['email']), ('/api/live', 'live-' + a.account['email'])):
        anon.cookies.clear()
        known = anon.post(f'{prefix}/auth/login', json={'email': email, 'password': 'Wrong-password-123!'})
        nobody = anon.post(f'{prefix}/auth/login', json={'email': unknown, 'password': 'Wrong-password-123!'})
        assert _normalized(known, {'email': email}) == _normalized(nobody, {'email': unknown}), prefix
        assert known.status_code == 401, (prefix, known.status_code, known.text)
    known = anon.post('/api/v28/auth/password-reset/request', json={'email': a.account['email']})
    nobody = anon.post('/api/v28/auth/password-reset/request', json={'email': unknown})
    assert _normalized(known, {'email': a.account['email']}) == _normalized(nobody, {'email': unknown})


ANONYMOUS = sorted(k for k, e in REGISTRY['routes'].items() if e['kind'] not in ('legacy_ws', 'capability_url'))


def _unauthenticated(spec: dict):
    """The answer a caller without a session must get: None for a public route (anything, but no customer data)."""
    if 'anonymous' in spec:
        return spec['anonymous']
    return {'public': None, 'legacy_refused': spec.get('refused'), 'admin': 403}.get(spec['kind'], 401)


@pytest.mark.parametrize('key', ANONYMOUS)
def test_an_anonymous_caller_gets_only_the_unauthenticated_answer(world, key):
    """Deployed configuration (the Bearer middleware is off, as in Vercel production): every route that is not public
    must refuse a caller with no cookie and no token by itself -- 401, or its own refusal for everyone (410/501 legacy,
    403 for a staff key) -- even when the caller sends A's identifiers. Nothing of A's or B's comes back."""
    spec = REGISTRY['routes'][key]
    a, b, anon = world['A'], world['B'], world['anonymous']
    anon.cookies.clear()
    method, template = key.split(' ', 1)
    before = _state(a)
    if method == 'MOUNT':
        got = anon.get(template + '/index.html')
    elif 'ids' in spec:
        got = _request(anon, key, spec, {n: a.ids_for(spec['world'])[n] for n in spec['ids']}, {})
    else:
        got = _probe_call(anon, key, a, {})
    anon.cookies.clear()
    expected = _unauthenticated(spec)
    if expected is not None:
        assert got.status_code == expected, \
            f'{key} ({spec["kind"]}) answered {got.status_code} to a caller with no session, not {expected}: {got.text[:200]}'
    for owner in (a, b):
        _assert_no_trace(owner, got, f'{key} (anonymous)')
    assert _state(a) == before, f'{key}: an anonymous call changed A\'s rows'


def test_legacy_websockets_authorize_nothing(world):
    from starlette.websockets import WebSocketDisconnect
    client, a, b = world['client'], world['A'], world['B']
    for key, entry in REGISTRY['routes'].items():
        if entry['kind'] != 'legacy_ws':
            continue
        for deployment in (a.ids['project_id'], a.ids['deployment_id'], _fresh('deployment_id')):
            path = key.split(' ', 1)[1].replace('{deployment_id}', deployment)
            with pytest.raises(WebSocketDisconnect) as closed:
                with client.websocket_connect(f"{path}?token={b.tokens['v28']}") as ws:
                    ws.receive_json()
            assert closed.value.code == 4401, (key, closed.value.code)


# ------------------------------------------------------------------------------- previews: links, tokens, router

def _handle(version_id: str, artifact_id: str) -> str:
    return base64.urlsafe_b64encode(uuid.UUID(version_id).bytes + uuid.UUID(artifact_id).bytes).decode().rstrip('=')


def test_live_preview_handles_open_only_the_archive_they_name(world):
    """A live_core preview link is a capability: whoever holds it sees that version, and nothing else. A handle that
    pairs one account's version with the other's artifact, an unknown handle, and a path outside the archive are all
    the same 404."""
    client, a, b = world['client'], world['A'], world['B']
    la, lb = a.gen_ids['live'], b.gen_ids['live']
    page = client.get(f"/preview/live/{la['live_preview_handle']}/")
    assert page.status_code == 200 and a.marker in page.text and b.marker not in page.text
    unknown = client.get(f"/preview/live/{_fresh('live_preview_handle')}/")
    for handle in (_handle(la['version_id'], lb['artifact_id']), _handle(lb['version_id'], la['artifact_id'])):
        got = client.get(f'/preview/live/{handle}/')
        assert (got.status_code, got.text) == (unknown.status_code, unknown.text) == (404, '{"detail":"Preview not found"}')
    missing = client.get(f"/preview/live/{la['live_preview_handle']}/no-such-file.txt")
    for escape in ('..%2f..%2f..%2fetc%2fpasswd', '%2e%2e/%2e%2e/app.py', '/etc/passwd', '..\\..\\app.py'):
        got = client.get(f"/preview/live/{la['live_preview_handle']}/{escape}")
        assert got.status_code == 404 and b.marker not in got.text, (escape, got.status_code, got.text[:200])
        assert got.text == missing.text, escape


class _App:
    """The generated app behind the router (not the boundary): it answers with its owner's name."""

    def __init__(self, name: str):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        seen = self.seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append((self.path, self.headers.get('Cookie'), self.headers.get('X-148ai-Preview-Access')))
                body = f'app of {name}'.encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def test_the_preview_router_lets_each_token_open_only_its_own_preview(world):
    """The worker host's router (omni_prod.preview_router) with the real PreviewAccess and route table on PostgreSQL;
    each token is issued by the real API route to the preview's owner. An owner link never opens another account's
    preview, a share link opens only the preview it was made for and only while it is SHARED, and nothing opens a
    PRIVATE preview anonymously."""
    import threading
    from http.server import ThreadingHTTPServer
    from urllib import error, parse, request as urlrequest
    from omni_prod import preview_router
    from omni_prod.preview_access import HEADER, PreviewAccess
    from omni_prod.preview_repository import PostgresPreviewRepository
    client, a, b = world['client'], world['A'], world['B']
    previews, apps, tokens = PostgresPreviewRepository(IA._v28_pool), {}, {}
    for who in (a, b):
        apps[who.name] = _App(who.name)
        prv = f'prv_{uuid.uuid4().hex}'
        previews.create(prv, who.ids['internal_key'], who.ids['version_id'], ttl_seconds=3600)
        assert previews.record_runtime(prv, container_id=f'c-{prv}', runtime_host='router-test',
                                       host_port=apps[who.name].port, workdir=f'/tmp/{prv}', data_storage='temporary')
        assert previews.mark_running(prv, url=f'https://{prv.replace("_", "-")}.preview.148ai.test')
        base = f"/api/v28/projects/{who.ids['project_id']}/previews/{prv}"
        owner_url = _ok(client.post(base + '/access', headers=who.headers()))['url']
        share_url = _ok(client.post(base + '/sharing', headers=who.headers(), json={'mode': 'SHARED'}))['share_url']
        tokens[who.name] = {'preview': prv, 'base': base,
                            'owner': parse.parse_qs(parse.urlsplit(owner_url).query)['__148ai_access'][0],
                            'share': parse.parse_qs(parse.urlsplit(share_url).query)['__148ai_access'][0]}
    clock = [1000.0]
    access = PreviewAccess(IA._v28_pool, clock=lambda: clock[0])
    table = preview_router.RouteTable(previews.get_route, 'router-test', clock=lambda: clock[0])
    router = ThreadingHTTPServer(('127.0.0.1', 0), preview_router.make_handler(table, 'preview.148ai.test', access=access))
    threading.Thread(target=router.serve_forever, daemon=True).start()

    def get(owner: Customer, token: str | None = None):
        host = tokens[owner.name]['preview'].replace('_', '-') + '.preview.148ai.test'
        req = urlrequest.Request(f'http://127.0.0.1:{router.server_address[1]}/',
                                 headers={'Host': host, **({HEADER: token} if token else {})})
        try:
            with urlrequest.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode()
        except error.HTTPError as exc:
            return exc.code, exc.read().decode()
    try:
        assert get(a, tokens['Alice']['owner']) == (200, 'app of Alice')
        assert get(b, tokens['Bob']['owner']) == (200, 'app of Bob')
        for owner, token in ((b, tokens['Alice']['owner']), (b, tokens['Alice']['share']),
                             (a, tokens['Bob']['owner']), (a, tokens['Bob']['share']), (a, None), (b, None),
                             (a, 'not-a-token')):
            status, body = get(owner, token)
            assert status == 401 and 'app of' not in body, (owner.name, token and token[:6], status)
        assert get(a, tokens['Alice']['share']) == (200, 'app of Alice')        # SHARED: the share link works
        _ok(client.post(tokens['Alice']['base'] + '/sharing', headers=a.headers(), json={'mode': 'PRIVATE'}))
        clock[0] += 60                                                            # past both router caches
        assert get(a, tokens['Alice']['share'])[0] == 401                        # PRIVATE revoked the share link
        assert get(a, tokens['Alice']['owner']) == (200, 'app of Alice')        # the owner's link still works
        _ok(client.post(tokens['Bob']['base'] + '/sharing', headers=b.headers(), json={'mode': 'PUBLIC'}))
        clock[0] += 60
        assert get(b) == (200, 'app of Bob') and get(a)[0] == 401                 # PUBLIC is Bob's preview alone
        assert all(seen[1] is None and seen[2] is None for app in apps.values() for seen in app.seen), \
            'a token reached the generated app'
    finally:
        router.shutdown()
        for app in apps.values():
            app.server.shutdown()


# ----------------------------------------------------------------------------------------- files and workers

def test_object_keys_carry_their_tenant_and_are_reached_only_through_owned_rows(world):
    """Attachments live under attachments/<account>/<project>/ (the key is built from server ids only). A version's
    repository is content-addressed (repositories/<sha256>.zip, shared when two repositories are byte-identical) and is
    reached only through its project_versions row, which is read under the owner-bound internal key."""
    a, b = world['A'], world['B']
    with IA._v28_pool.connection() as conn:
        rows = conn.execute('SELECT account_id, project_id, storage_key FROM conversation_attachments '
                            'WHERE account_id = ANY(%s)', ([a.account['id'], b.account['id']],)).fetchall()
        versions = conn.execute('SELECT project_id, artifact_key FROM project_versions WHERE project_id = ANY(%s)',
                                ([a.ids['internal_key'], b.ids['internal_key']],)).fetchall()
    assert rows and versions
    for account, project, key in rows:
        assert key.startswith(f'attachments/{account}/{project}/') and '..' not in key.split('/'), key
    for project, key in versions:
        assert re.fullmatch(r'repositories/[0-9a-f]{64}\.zip', key), key
        assert key in STORE.objects
    a_repos = {k for p, k in versions if p == a.ids['internal_key']}
    b_repos = {k for p, k in versions if p == b.ids['internal_key']}
    assert a_repos and b_repos and not a_repos & b_repos     # different content, different objects
    assert IA._v28.accounts.internal_project_key(owner_id=b.account['id'], project_id=a.ids['project_id']) \
        != a.ids['internal_key']                             # B's key for A's project id names nothing of A's


def test_a_preview_worker_given_another_projects_version_starts_nothing(world):
    """worker_tasks.execute_preview_launch reads the version under the key it is given (the API enqueues the caller's
    own key after its ownership check). Given B's key with A's version id it fails before a container or a work
    directory exists, and reads none of A's objects."""
    from omni_prod import worker_tasks
    from omni_prod.preview_repository import PostgresPreviewRepository
    a, b = world['A'], world['B']
    prv = f'prv_{uuid.uuid4().hex}'
    previews = PostgresPreviewRepository(IA._v28_pool)
    previews.create(prv, b.ids['internal_key'], a.ids['version_id'], ttl_seconds=600)
    reads = len(STORE.reads)
    with pytest.raises(KeyError):
        worker_tasks.execute_preview_launch(prv, b.ids['internal_key'], a.ids['version_id'])
    row = previews.get(prv, b.ids['internal_key'])
    assert row['status'] == 'FAILED' and not row.get('container_id'), row
    assert not set(STORE.reads[reads:]) & a.objects()
