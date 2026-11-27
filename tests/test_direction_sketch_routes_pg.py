"""S6.3 slice 3: the direction sketch's routes and its offer, on the REAL served app over REAL PostgreSQL.

Run alone (investor_app reads its configuration once, at import):  python -m pytest -q tests/test_direction_sketch_routes_pg.py
Needs M4D2_DATABASE_URL pointing at a database migrated with `python -m omni_prod.migrate` (049 included). Skipped, reported,
without one.

What is proved, on the unmodified routes, supervisor, store and library (no model, no queue: OMNI_REDIS_URL is a closed port):
  * a first Hebrew request makes the reply carry one `direction_sketch` action; the same direction is offered once;
  * from the reply to a 200 from the page route takes seconds, with no worker at all, and the page carries the business
    name, the palette's colour, the pair's fonts and the draft ribbon;
  * a sketch changes nothing that decides a build: no row of the plan, contract, approval, build or credit tables, the
    brief's revision and fingerprint unchanged, whatever the customer then says ("כן, זה הכיוון");
  * a project that already has a version gets no sketch (`already_built`);
  * the page's headers (sandbox with no scripts, same-origin frame, no store, no index);
  * another account gets the unknown-project answer on all three routes; a sketch id of another project is a 404."""
from __future__ import annotations

import os
import re
import sys
import time
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
            missing = [t for t in ('creator_projects', 'intake_messages', 'direction_sketches')
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
SALON = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה". טלפון 04-5551234'

if _SKIP is None:
    for name in ('OMNI_ENV', 'OMNI_GENERATED_APP_TOKEN_SECRET', 'OMNI_INTAKE_MODEL', 'OMNI_INTAKE_VIA_WORKER',
                 'OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_MEDIA_READER', 'OMNI_SESSION_COOKIE_SECURE',
                 *[n for n in os.environ if n.endswith(('_API_KEY', '_API_TOKEN'))]):
        os.environ.pop(name, None)
    os.environ.update({
        'VERCEL_ENV': 'production', 'OMNI_CREATOR_PERSISTENCE': 'postgres', 'OMNI_DATABASE_URL': DATABASE_URL,
        'OMNI_SECRET_KEY': 'direction-sketch-routes-' + 'k' * 40, 'OMNI_ALLOWED_ORIGINS': ORIGIN,
        'OMNI_BILLING_ADMIN_KEY': 'sketch-routes-billing-admin-key', 'OMNI_REDIS_URL': 'redis://127.0.0.1:1/0',
        'PREVIEW_DOMAIN_TEMPLATE': 'https://{preview_id}.preview.148ai.test',
        'OMNI_DIRECTION_SKETCH': 'on', 'OMNI_SITE_LIBRARY': 'on'})
    from fastapi.testclient import TestClient

    import app as served
    from omni_prod import investor_app as IA
    from omni_prod.memory_adapters import MemoryArtifactStore
    from omni_prod.workspace import PostgresProjectWorkspace

    IA._v28.engine.workspace = PostgresProjectWorkspace(IA._v28_pool, MemoryArtifactStore())

TABLES = ('build_jobs', 'build_requests', 'build_approvals', 'm5_build_contracts', 'execution_plans', 'credit_reservations',
          'project_versions')


def _browser():
    return TestClient(served.app, base_url=ORIGIN, raise_server_exceptions=False, headers=BROWSER)


class Customer:
    def __init__(self, name: str):
        self.browser = _browser()
        email = f'{name}-{uuid.uuid4().hex[:10]}@sketch.example'
        reg = self.browser.post('/api/v28/auth/register', json={'email': email, 'password': 'Sketch-routes-123!'})
        assert reg.status_code == 200, reg.text[:300]
        self.token, self.account_id = reg.json()['token'], reg.json()['user']['id']
        sub = TestClient(served.app, raise_server_exceptions=False).post(
            '/api/v28/admin/subscription', json={'user_id': self.account_id, 'plan': 'business'},
            headers={'Authorization': 'Bearer ' + self.token, 'X-148AI-Billing-Admin-Key': 'sketch-routes-billing-admin-key'})
        assert sub.status_code == 200, sub.text[:300]
        self.project = self.browser.post('/api/v28/projects', json={'title': f'Project {name}'}).json()['id']

    def say(self, message: str, **kw):
        r = self.browser.post(f'/api/v28/projects/{self.project}/conversation', json={'message': message, **kw})
        assert r.status_code == 200, (r.status_code, r.text[:400])
        return r.json()

    def offers(self, turn: dict) -> list[dict]:
        return [a for a in ((turn.get('turn') or {}).get('actions') or []) if a.get('type') == 'direction_sketch']


def _counts() -> dict:
    with IA._v28_pool.connection() as conn:
        present = {t for (t,) in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'").fetchall()}
        return {t: conn.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in TABLES if t in present}


@pytest.fixture(scope='module')
def world():
    a, b = Customer('alice'), Customer('bob')
    yield {'A': a, 'B': b}
    IA._v28_pool.close()


def test_a_first_request_is_offered_a_sketch_once_and_a_new_direction_is_offered_again(world):
    a = world['A']
    first = a.say(SALON)
    offers = a.offers(first)
    assert len(offers) == 1, first['turn']['actions']
    assert re.fullmatch(r'[0-9a-f]{64}', offers[0]['direction_fp']) and offers[0]['brief_revision'] >= 1
    again = a.say('בבקשה שיהיה כתוב שאנחנו פתוחים בערבים')                # same direction: no second offer
    assert a.offers(again) == []
    blue = a.say('הצבע הראשי יהיה כחול')                                  # a named colour changes the direction
    assert len(a.offers(blue)) == 1 and a.offers(blue)[0]['direction_fp'] != offers[0]['direction_fp']
    messages = a.browser.get(f'/api/v28/projects/{a.project}/conversation').json()['messages']
    seen = [x['direction_fp'] for m in messages for x in (m.get('actions') or []) if x.get('type') == 'direction_sketch']
    assert len(seen) == len(set(seen)) == 2


def test_from_the_reply_to_the_page_takes_seconds_with_no_worker_and_the_page_shows_the_direction(world):
    a = world['A']
    started = time.monotonic()
    made = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={})
    assert made.status_code == 200, made.text[:400]
    body = made.json()
    sketch = body['sketch']
    page = a.browser.get(f"/api/v28/projects/{a.project}/sketches/{sketch['id']}/page")
    elapsed = time.monotonic() - started
    assert page.status_code == 200 and elapsed < 5, (page.status_code, elapsed)
    assert sketch['draft'] is True and sketch['state'] in ('structure', 'failed')       # no model, no worker: structure only
    html = page.text
    assert 'סטודיו נועה' in html and 'draft-ribbon' in html and 'סקיצה' in html
    assert sketch['direction']['colours']['--color-primary'] in html.lower()
    from omni_prod import typography as T
    for role in ('display', 'body'):
        assert T.pair(sketch['direction']['pair'])[role]['family'].replace(' ', '+') in html
    assert [x for x in re.findall(r'<section[^>]* id="([a-z]+)"', html)][1:] == [k for k in sketch['direction']['sections'] if k != 'hero']
    # the page route's own headers
    csp = page.headers['content-security-policy']
    assert 'sandbox' in csp and 'allow-scripts' not in csp and 'allow-same-origin' not in csp and "script-src" not in csp
    assert "frame-ancestors 'self'" in csp and "default-src 'none'" in csp
    assert page.headers['x-frame-options'] == 'SAMEORIGIN' and 'no-store' in page.headers['cache-control']
    assert 'noindex' in page.headers['x-robots-tag'] and page.headers['cross-origin-resource-policy'] == 'same-origin'
    assert page.headers['content-type'].startswith('text/html')
    # idempotent: the same direction is the same sketch
    twice = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={}).json()
    assert twice['sketch']['id'] == sketch['id']
    got = a.browser.get(f"/api/v28/projects/{a.project}/sketches/{sketch['id']}")
    assert got.status_code == 200 and got.json()['sketch']['id'] == sketch['id']


def test_a_sketch_changes_nothing_that_decides_a_build(world):
    a = world['A']
    row = IA._brief_repo().latest(a.project)
    brief_before = (row.revision, row.fingerprint)
    counts_before = _counts()
    made = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={}).json()['sketch']
    a.browser.get(f"/api/v28/projects/{a.project}/sketches/{made['id']}")
    a.browser.get(f"/api/v28/projects/{a.project}/sketches/{made['id']}/page")
    row = IA._brief_repo().latest(a.project)
    assert (row.revision, row.fingerprint) == brief_before             # the three routes wrote nothing to the brief
    said = a.say('כן, זה הכיוון')
    assert not any(x.get('type') in ('approve_build', 'approve_spec') and x.get('approved') for x in ((said.get('turn') or {}).get('actions') or []))
    assert _counts() == counts_before
    row = IA._brief_repo().latest(a.project)
    assert row.fingerprint == brief_before[1]                          # a typed "yes" changes no decision of the brief
    for table in ('build_jobs', 'build_approvals', 'credit_reservations'):
        assert counts_before.get(table, 0) == 0


def test_a_project_that_already_has_a_version_gets_no_sketch_and_no_offer(world):
    a = world['A']
    with mock.patch.object(IA, '_project_context', lambda key: (lambda project_id: {'latest_version_id': 'v_built'})):
        r = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={})
        assert r.status_code == 409 and r.json()['detail'] == {'error': 'not_ready', 'reason': 'already_built'}, r.text[:300]
        turn = a.say('עוד משהו קטן: שיהיה כתוב "מספרה בחיפה" בראש העמוד')
        assert a.offers(turn) == []
        record = [m for m in a.browser.get(f'/api/v28/projects/{a.project}/conversation').json()['messages']][-1]
        assert record['role'] == 'assistant'


def test_a_stale_revision_is_refused_and_nothing_from_the_client_decides_the_direction(world):
    a = world['A']
    r = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={'brief_revision': 99999})
    assert r.status_code == 409 and r.json()['detail']['error'] == 'brief_stale'
    r = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={'palette': 'counsel', 'direction': 'bold', 'colours': ['#000000']})
    assert r.status_code == 200 and r.json()['sketch']['direction']['palette'] != 'counsel'


def test_another_account_gets_the_unknown_project_answer_on_all_three_routes(world):
    a, b = world['A'], world['B']
    made = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={}).json()['sketch']['id']
    unknown_project = 'prj_' + uuid.uuid4().hex[:12]
    for method, tail in (('post', 'sketches'), ('get', f'sketches/{made}'), ('get', f'sketches/{made}/page')):
        kw = {'json': {}} if method == 'post' else {}
        theirs = getattr(b.browser, method)(f'/api/v28/projects/{a.project}/{tail}', **kw)
        nothing = getattr(b.browser, method)(f'/api/v28/projects/{unknown_project}/{tail}', **kw)
        assert (theirs.status_code, theirs.json()) == (nothing.status_code, nothing.json()), (method, tail)
        assert made not in theirs.text and 'סטודיו' not in theirs.text
        anonymous = getattr(_browser(), method)(f'/api/v28/projects/{a.project}/{tail}', **kw)
        assert anonymous.status_code in (401, 403) and 'סטודיו' not in anonymous.text


def test_a_sketch_id_of_another_project_is_a_404_like_an_id_that_never_existed(world):
    a, b = world['A'], world['B']
    b.say(SALON)
    made = a.browser.post(f'/api/v28/projects/{a.project}/sketches', json={}).json()['sketch']['id']
    never = 'skt_' + uuid.uuid4().hex[:24]
    for tail in ('', '/page'):
        foreign = b.browser.get(f'/api/v28/projects/{b.project}/sketches/{made}{tail}')
        unknown = b.browser.get(f'/api/v28/projects/{b.project}/sketches/{never}{tail}')
        assert (foreign.status_code, foreign.json()) == (unknown.status_code, unknown.json()) and foreign.status_code == 404
        malformed = b.browser.get(f'/api/v28/projects/{b.project}/sketches/{"not-an-id"}{tail}')
        assert malformed.status_code == 404
    reads = IA._v28_pool.connection()
    with reads as conn:
        rows = conn.execute('SELECT count(*) FROM direction_sketches WHERE project_id = %s', (b.project,)).fetchone()[0]
    assert rows <= 1                       # B made no sketch of A's: any row of B's own project is B's


def test_a_non_hebrew_site_or_an_app_gets_a_named_reason_not_a_sketch(world):
    c = Customer('carol')
    c.say('I want a website for my law firm Cohen and Co. Phone 03-5551234.')
    r = c.browser.post(f'/api/v28/projects/{c.project}/sketches', json={})
    assert r.status_code == 409 and r.json()['detail']['reason'] in ('not_hebrew', 'no_name'), r.text[:300]   # the conversation may add Hebrew words to the request; the unit test names not_hebrew
    d = Customer('dave')
    d.say('אני רוצה אפליקציה לניהול מלאי עם התחברות ודוחות')
    r = d.browser.post(f'/api/v28/projects/{d.project}/sketches', json={})
    assert r.status_code == 409 and r.json()['detail']['reason'] in ('not_a_site', 'not_content_site'), r.text[:300]


def test_with_the_model_route_on_and_the_queue_down_the_sketch_is_still_there_and_the_money_is_given_back(world):
    c = Customer('erin')
    c.say(SALON)
    env = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_ZERO_COST_MODE': '0',
           'OMNI_ALLOW_EXTERNAL_FALLBACK': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15', 'OMNI_INTAKE_DAILY_BUDGET_USD': '5',
           'GEMINI_API_KEY': 'test-only-not-a-key'}
    with mock.patch.dict(os.environ, env):
        started = time.monotonic()
        made = c.browser.post(f'/api/v28/projects/{c.project}/sketches', json={})
        assert made.status_code == 200, made.text[:400]
        body = made.json()
        page = c.browser.get(f"/api/v28/projects/{c.project}/sketches/{body['sketch']['id']}/page")
    assert page.status_code == 200 and time.monotonic() - started < 5
    assert body['words']['state'] == 'failed' and body['words']['reason'] == 'queue_unavailable', body['words']
    assert body['sketch']['state'] == 'failed' and 'סטודיו נועה' in page.text
    with IA._v28_pool.connection() as conn:
        states = conn.execute("SELECT state, quote->>'task' FROM intake_reservations WHERE account_id = %s AND quote->>'task' = 'direction_sketch'",
                              (c.account_id,)).fetchall()
        credits = conn.execute('SELECT count(*) FROM credit_reservations WHERE account_id = %s', (c.account_id,)).fetchone()[0]
    assert states == [('RELEASED', 'direction_sketch')] and credits == 0
