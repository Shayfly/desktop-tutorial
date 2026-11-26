"""S4.5 (the owner's plan v3, 2026-11-25): one customer can never read or change another customer's data.

The REAL served app (app.py: omni_prod.investor_app plus the live_core router) runs over a REAL PostgreSQL
(M4D2_DATABASE_URL, migrated with `python -m omni_prod.migrate`), in the deployed configuration: OMNI_ENV=production
(bearer authentication on /api/, the legacy in-process paths refused), OMNI_CREATOR_PERSISTENCE=postgres, and the
durable PostgresProjectWorkspace. Two real accounts are registered through the real routes; account B then uses
account A's identifiers on every route that takes one (tests/tenant_isolation_routes.json, which
tests/test_tenant_isolation_registry.py compares with the app) and must get exactly the answer it gets for an
identifier that does not exist -- never A's data, and never a change to A's rows.

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

if _SKIP is None:
    for name in ('OMNI_INTAKE_MODEL', 'OMNI_INTAKE_VIA_WORKER', 'OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_MEDIA_READER',
                 'VERCEL_ENV'):
        os.environ.pop(name, None)
    os.environ.update({
        'OMNI_ENV': 'production', 'OMNI_CREATOR_PERSISTENCE': 'postgres', 'OMNI_DATABASE_URL': DATABASE_URL,
        'OMNI_SECRET_KEY': 'tenant-isolation-control-plane-' + 'k' * 40,
        'OMNI_GENERATED_APP_TOKEN_SECRET': 'tenant-isolation-generated-apps-' + 'g' * 40,
        'OMNI_ALLOWED_ORIGINS': 'https://app.148ai.test', 'OMNI_LIVE_ENABLED': '1',
        'OMNI_BILLING_ADMIN_KEY': 'tenant-isolation-billing-admin-key',
        'PREVIEW_DOMAIN_TEMPLATE': 'https://{preview_id}.preview.148ai.test',
        'OMNI_REDIS_URL': 'redis://127.0.0.1:1/0',
    })
    from fastapi.testclient import TestClient

    import app as served                       # the Vercel entrypoint: investor_app + the live_core router
    from omni_prod import investor_app as IA
    from omni_prod.memory_adapters import MemoryArtifactStore
    from omni_prod.workspace import PostgresProjectWorkspace

    class ExactKeyStore(MemoryArtifactStore):
        """omni_prod.memory_adapters.MemoryArtifactStore with S3ArtifactStore's signatures: get_bytes(key, verify=),
        an identical re-put is a no-op (S3 overwrites; a content-addressed key always carries the same bytes) and
        delete(key). No prefix match, no default: a key that is not there raises KeyError."""

        def __init__(self):
            super().__init__()
            self.reads: list[str] = []

        def get_bytes(self, key, *, verify=True):
            self.reads.append(key)
            return self.objects[key]

        def put_bytes(self, key, data):
            if self.objects.get(key) == bytes(data):
                return None
            return super().put_bytes(key, data)

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


class Customer:
    def __init__(self, name: str):
        self.name = name
        self.marker = f'{name}-secret-{uuid.uuid4().hex[:12]}'
        self.ids: dict[str, str] = {}
        self.tokens: dict[str, str] = {}
        self.account: dict[str, str] = {}

    def headers(self, gen: str = 'v28') -> dict:
        return {'Authorization': 'Bearer ' + self.tokens[gen]}


def _ok(response, *codes):
    assert response.status_code in (codes or (200,)), (response.status_code, response.text[:500])
    return response.json() if response.headers.get('content-type', '').startswith('application/json') else response


def _register(client, customer: Customer) -> None:
    email = f'{customer.name.lower()}-{uuid.uuid4().hex[:10]}@tenant.example'
    password = 'Tenant-isolation-123!'
    reg = _ok(client.post('/api/v28/auth/register', json={'email': email, 'password': password}))
    customer.tokens['v28'] = reg['token']
    customer.account = {'id': reg['user']['id'], 'email': email}
    _ok(client.post('/api/v28/admin/subscription', json={'user_id': reg['user']['id'], 'plan': 'business'},
                    headers={**customer.headers(), 'X-148AI-Billing-Admin-Key': 'tenant-isolation-billing-admin-key'}))
    for gen in ('v26', 'v27'):
        customer.tokens[gen] = _ok(client.post(f'/api/{gen}/auth/register',
                                               json={'email': f'{gen}-{email}', 'password': password}))['token']
    customer.tokens['live'] = _ok(client.post('/api/live/auth/register',
                                              json={'email': f'live-{email}', 'password': password}))['token']


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

    h, pool = customer.headers(), IA._v28_pool
    pid = _ok(client.post('/api/v28/projects', headers=h, json={'title': f'Project {customer.marker}'}))['id']
    _, key = IA._v28.resolve_project_key(token=customer.tokens['v28'], project_id=pid)
    customer.ids.update(project_id=pid, internal_key=key)
    _ok(client.post(f'/api/v28/projects/{pid}/discovery', headers=h,
                    json={'prompt': f'A landing page for a bakery called {customer.marker}', 'mode': 'guided'}))
    _ok(client.post(f'/api/v28/projects/{pid}/conversation', headers=h,
                    json={'message': f'The bakery is named {customer.marker} and sells bread'}))
    att = _ok(client.post(f'/api/v28/projects/{pid}/attachments', headers=h,
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

    sessions = _ok(client.get('/api/v28/auth/sessions', headers=h))['sessions']
    customer.ids['session_id'] = sessions[0]['session_id']


@pytest.fixture(scope='module')
def world():
    client = TestClient(served.app, raise_server_exceptions=False)
    a, b = Customer('Alice'), Customer('Bob')
    for customer in (a, b):
        _register(client, customer)
        _seed_v28(client, customer)
    yield {'client': client, 'A': a, 'B': b}
    IA._v28_pool.close()


def _fresh(name: str) -> str:
    """An identifier of the same shape that names nothing."""
    shapes = {'project_id': lambda: 'prj_' + secrets.token_urlsafe(10), 'version_id': lambda: f'v_{uuid.uuid4().hex[:16]}',
              'first_version_id': lambda: f'v_{uuid.uuid4().hex[:16]}', 'build_id': lambda: f'bld_{uuid.uuid4().hex}',
              'preview_id': lambda: f'prv_{uuid.uuid4().hex}', 'modification_id': lambda: f'mod_{uuid.uuid4().hex}',
              'attachment_id': lambda: f'att_{uuid.uuid4().hex}', 'build_contract_id': lambda: 'bc_' + uuid.uuid4().hex[:24],
              'session_id': lambda: 'ses_' + secrets.token_urlsafe(18)}
    return shapes[name]()


def _normalized(response, supplied: dict[str, str]):
    """The answer with every identifier the caller supplied replaced by its name (an echo of the caller's own input
    is not a difference)."""
    text = response.text
    for name, value in sorted(supplied.items(), key=lambda kv: -len(kv[1])):
        text = text.replace(value, f'<{name}>')
    return response.status_code, text


# ------------------------------------------------------------------------------------- build contract identifiers

def test_a_foreign_build_contract_id_is_answered_like_an_unknown_one(world):
    """LEAK FOUND 2026-11-26: POST .../builds with another project's build_contract_id answered 403 "build contract
    does not belong to project", and with an unknown id 500 -- an oracle for which contract ids exist elsewhere. B's
    own project and A's contract id must get B's answer for an id that names nothing: a 409 that says to plan again."""
    client, a, b = world['client'], world['A'], world['B']
    # A project of B's own with no active build: a queued build is answered before the contract is read.
    own = _ok(client.post('/api/v28/projects', headers=b.headers(), json={'title': 'Bob, no build yet'}))['id']
    path = f'/api/v28/projects/{own}/builds'
    foreign_id, missing_id = a.ids['build_contract_id'], _fresh('build_contract_id')
    foreign = client.post(path, headers=b.headers(), json={'prompt': 'Build a CRM app', 'build_contract_id': foreign_id})
    missing = client.post(path, headers=b.headers(), json={'prompt': 'Build a CRM app', 'build_contract_id': missing_id})
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
