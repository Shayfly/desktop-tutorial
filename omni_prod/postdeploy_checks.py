"""Post-deploy verification against the real pre-staging infrastructure.

Founder approval 2026-10-09 13:38: after the merge, verify on the real server
before anything is called LIVE. Runs inside the deployed worker image on the
worker host (`.github/workflows/postdeploy-checks.yml`) with the real
environment: Neon Postgres, Upstash Redis, R2, the real preview worker,
Caddy edge and build worker. The 148AI API is served by this same image's
code under uvicorn on localhost (the Vercel deployment is behind Vercel
Authentication and not reachable from the runner); the Vercel edge itself is
checked separately (GET of the deployed assets/routes).

Uses one synthetic account (`qa-postdeploy-*@example.com`, internal QA
entitlement) and synthetic data only. Never prints secrets. Stages:

  free          migrations, builder health, existing data intact, refused
                publish/demo paths, preview + persistent data across restart
                and a new version, journal endpoints. $0.
  cancel-setup  (build worker stopped by the workflow) two builds through
                discovery -> plan -> approval -> build; A is stopped while
                queued via the API, B gets a stop flag as if the stop arrived
                after the worker claimed it. $0.
  cancel-verify (worker started) B must end CANCELLED before any model call,
                both reservations RELEASED, journal readable incrementally.
  paid-create   (worker stopped) one build through discovery -> approval.
  paid-verify   after the build ran in a one-off worker with a hard model
                ceiling: status, browser check, QA review, cost settlement,
                version, preview, acceptance stored, page responsive,
                persistent data storage, restart.

Each stage prints `::notice|::error title=postdeploy <check>::...` lines and a
final JSON summary; state between stages is kept in /out/state.json.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from urllib import error as urlerror
from urllib import request as urlrequest

STATE_PATH = os.getenv('POSTDEPLOY_STATE', '/out/state.json')
PORT = int(os.getenv('POSTDEPLOY_PORT', '18080'))
BASE = f'http://127.0.0.1:{PORT}'
RESULTS: list[dict] = []

FIXTURE_APP = r'''
import http.server, os, pathlib
DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
VERSION = "%s"
class H(http.server.BaseHTTPRequestHandler):
    def _send(self, body):
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _count(self):
        return int(DATA.read_text()) if DATA.exists() else 0
    def do_GET(self):
        self._send(VERSION + ":" + str(self._count()) if self.path == "/count" else "ok")
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))  # never leave a body on a kept-alive connection
        if self.path != "/hit-postdeploy":
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        DATA.write_text(str(self._count() + 1)); self._send("hit")
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''


def fixture(version: str) -> dict[str, str]:
    return {'app.py': FIXTURE_APP % version,
            '.omni/project.json': json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim',
                                              'start': ['python', 'app.py'], 'port': 8000, 'health_path': '/'})}


def record(check: str, ok: bool, detail='') -> bool:
    detail = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, default=str)
    RESULTS.append({'check': check, 'ok': bool(ok), 'detail': detail[:900]})
    if not ok:  # GitHub keeps only 10 annotations per step: failures individually, passes in one summary
        body = ('FAIL ' + detail)[:1500].replace('%', '%25').replace('\n', '%0A')
        print(f'::error title=postdeploy {check}::{body}', flush=True)
    return ok


def load_state() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f)


# ---------------------------------------------------------------- HTTP ------
def http(method: str, url: str, body=None, token: str | None = None, timeout: float = 60.0, headers=None):
    data = None if body is None else json.dumps(body).encode()
    headers = dict(headers or {})
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urlrequest.Request(url, data=data, method=method, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', 'replace')
            status = resp.status
    except urlerror.HTTPError as exc:
        raw, status = exc.read().decode('utf-8', 'replace'), exc.code
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, raw


def api(method, path, body=None, token=None, timeout=60.0):
    return http(method, BASE + path, body, token, timeout)


def start_api() -> None:
    import uvicorn
    from .investor_app import app
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=PORT, log_level='warning'))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(120):
        try:
            if http('GET', BASE + '/api/v28/m5/status', timeout=3)[0] == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError('local API did not start')


def pool():
    from .investor_app import _v28_pool
    return _v28_pool


def sql(query: str, params=()):
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if cur.description else []


def sql_write(query: str, params=()):
    with pool().connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount


# ------------------------------------------------------------ helpers -------
def new_account(state: dict) -> str:
    if state.get('token'):
        return state['token']
    email = f'qa-postdeploy-{uuid.uuid4().hex[:10]}@example.com'
    password = 'pd-' + uuid.uuid4().hex
    status, body = api('POST', '/api/v28/auth/register', {'email': email, 'password': password})
    if status != 200:
        raise RuntimeError(f'register failed: {status} {body}')
    from .entitlements import grant
    with pool().connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                grant(cur, email=email, reason='post-deploy verification 2026-10-09 (synthetic account)',
                      granted_by='claude:postdeploy')
    state.update(email=email, token=body['token'], account_id=(body.get('user') or {}).get('id'))
    return state['token']


def new_project(token: str, title: str) -> str:
    status, body = api('POST', '/api/v28/projects', {'title': title}, token)
    if status != 200:
        raise RuntimeError(f'create project failed: {status} {body}')
    return body.get('id') or body.get('project_id') or body['project']['id']


def internal_key(token: str, project_id: str) -> str:
    from .investor_app import _v28
    return _v28.resolve_project_key(token=token, project_id=project_id)[1]


def wait(fn, seconds: float, every: float = 2.0):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        last = fn()
        if last is not None and last is not False:
            return last
        time.sleep(every)
    return None


def preview_launch(token, project_id, version_id, seconds=150):
    status, body = api('POST', f'/api/v28/projects/{project_id}/versions/{version_id}/previews', None, token)
    if status not in (200, 202):
        return None, f'launch {status} {body}'
    pid = body['preview_id']

    def poll():
        s, b = api('GET', f'/api/v28/projects/{project_id}/previews/{pid}', None, token)
        if s == 200 and b.get('status') in ('RUNNING', 'FAILED', 'NOT_PREVIEWABLE', 'EXPIRED', 'STOPPED'):
            return b
        return None
    view = wait(poll, seconds)
    return view, None if view else 'preview did not settle'


def preview_header(token, project_id, view) -> dict:
    """The owner's access token for a private preview, as the router header."""
    from urllib.parse import parse_qs, urlsplit
    from .preview_access import HEADER, QUERY_PARAM
    s, d = api('POST', f"/api/v28/projects/{project_id}/previews/{view['id']}/access", None, token)
    if s != 200:
        raise RuntimeError(f'preview access {s} {d}')
    return {HEADER: parse_qs(urlsplit(d['url']).query)[QUERY_PARAM][0]}


def preview_stop(token, project_id, preview_id):
    api('DELETE', f'/api/v28/projects/{project_id}/previews/{preview_id}', None, token)

    def poll():
        s, b = api('GET', f'/api/v28/projects/{project_id}/previews/{preview_id}', None, token)
        return b if s == 200 and b.get('status') in ('STOPPED', 'EXPIRED') else None
    return wait(poll, 90)


def run_discovery(token, project_id, prompt) -> tuple[int, dict]:
    status, view = api('POST', f'/api/v28/projects/{project_id}/discovery?lang=he',
                       {'prompt': prompt, 'mode': 'recommend', 'request_key': uuid.uuid4().hex}, token)
    if status != 200:
        raise RuntimeError(f'discovery start {status} {view}')
    for _ in range(20):
        if view.get('complete'):
            return view['brief']['revision'], view
        answers = {}
        for q in view.get('questions') or []:
            if q.get('delegable'):
                answers[q['id']] = '__delegate__'
            elif q.get('suggested'):
                answers[q['id']] = str(q['suggested'])
            elif q.get('options'):
                answers[q['id']] = q['options'][0]['value']
            else:
                answers[q['id']] = '__delegate__'
        status, view = api('POST', f'/api/v28/projects/{project_id}/discovery/answers?lang=he',
                           {'revision': view['brief']['revision'], 'answers': answers,
                            'request_key': uuid.uuid4().hex}, token)
        if status != 200:
            raise RuntimeError(f'discovery answers {status} {view}')
    raise RuntimeError('discovery did not complete')


def plan_and_build(token, project_id, revision, prompt) -> dict:
    status, plan = api('POST', f'/api/v28/projects/{project_id}/build-contracts',
                       {'prompt': prompt, 'brief_revision': revision}, token)
    if status != 200 or not plan.get('can_build'):
        info = {k: plan.get(k) for k in ('status', 'can_build', 'blockers', 'economics', 'durable_backend')} \
            if isinstance(plan, dict) else plan
        raise RuntimeError(f'plan {status} {json.dumps(info, ensure_ascii=False, default=str)[:1200]}')
    status, appr = api('POST', f'/api/v28/projects/{project_id}/approvals',
                       {'build_contract_id': plan['build_contract_id'], 'brief_revision': revision}, token)
    if status != 200:
        raise RuntimeError(f'approval {status} {appr}')
    status, build = api('POST', f'/api/v28/projects/{project_id}/builds',
                        {'prompt': prompt, 'build_contract_id': plan['build_contract_id'],
                         'approval_id': appr['approval_id']}, token)
    if status not in (200, 202):
        raise RuntimeError(f'build {status} {build}')
    return {'build_id': build['build_id'], 'plan': plan.get('build_contract_id'), 'approval': appr['approval_id']}


def reservation(build_id):
    rows = sql('SELECT status, estimated_provider_cost_usd, actual_provider_cost_usd, settled_provider_cost_usd, '
               'funding_source FROM credit_reservations WHERE build_id = %s', (build_id,))
    if not rows:
        return None
    r = rows[0]
    return {'status': r[0], 'estimated': str(r[1]), 'actual': None if r[2] is None else str(r[2]),
            'settled': None if r[3] is None else str(r[3]), 'funding': r[4]}


# -------------------------------------------------------------- stages ------
def stage_free(state: dict) -> None:
    # Migrations
    rows = sql('SELECT version, name FROM schema_migrations ORDER BY version')
    versions = [r[0] for r in rows]
    cols = sql("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND "
               "((table_name='build_jobs' AND column_name IN ('cancel_requested_at','cancel_requested_by')) OR "
               "(table_name='project_previews' AND column_name='data_storage'))")
    events_table = sql("SELECT to_regclass('public.build_events') IS NOT NULL")[0][0]
    access_table = sql("SELECT to_regclass('public.preview_access_tokens') IS NOT NULL")[0][0]
    expected = max(int(p.name.split('_', 1)[0]) for p in __import__('pathlib').Path(__file__).resolve().parents[1]
                   .joinpath('infra', 'postgres').glob('*.sql')) if __import__('pathlib').Path(__file__).resolve()\
        .parents[1].joinpath('infra', 'postgres').exists() else max(versions)
    record('migrations', max(versions) == expected and 31 in versions and len(cols) == 3 and events_table
           and (max(versions) < 32 or access_table),
           f'{len(versions)} applied, latest {max(versions)} ({rows[-1][1]}); 031 columns {len(cols)}/3; '
           f'build_events={events_table}')

    # Builder health: an RQ worker registered on the build queue, sandbox runner answers.
    from redis import Redis
    from rq import Worker
    redis = Redis.from_url(os.environ['OMNI_REDIS_URL'])
    build_workers = [w for w in Worker.all(connection=redis) if 'omni-builds' in w.queue_names()]
    sandbox = os.getenv('POSTDEPLOY_SANDBOX_HEALTH', 'unknown')  # measured by the workflow on the host
    record('builder health', bool(build_workers) and sandbox == '200',
           f'build workers={len(build_workers)} states={[w.get_state() for w in build_workers]} sandbox-runner={sandbox}')

    # Existing data intact: every version's artifact loads and matches its checksum.
    from .investor_app import _v28
    from .workspace import _checksum
    ws = _v28.engine.workspace
    projects = sql("SELECT count(*) FROM creator_projects WHERE title NOT LIKE 'postdeploy%%'")[0][0]
    vrows = sql("SELECT id, project_id, repository_sha256 FROM project_versions ORDER BY created_at DESC LIMIT 40")
    bad = []
    for vid, pid, sha in vrows:
        try:
            repo = ws.get(project_id=pid, version_id=vid).repository()
            if _checksum(repo) != sha:
                bad.append(f'{vid}: checksum')
        except Exception as exc:
            bad.append(f'{vid}: {type(exc).__name__}')
    total_versions = sql('SELECT count(*) FROM project_versions')[0][0]
    record('existing versions intact', not bad,
           f'{projects} projects, {total_versions} versions; newest {len(vrows)} loaded from storage and '
           f'checksummed; failures={bad[:5]}')

    # Refused demo/publish paths (durable mode).
    refused = {}
    for path, body in (('/api/demo/build', {'prompt': 'post deploy check'}), ('/api/v25/build', {'prompt': 'post deploy check'}),
                       ('/api/v26/projects/p/build', {'prompt': 'post deploy check'}),
                       ('/api/v27/projects/p/build', {'prompt': 'post deploy check'}),
                       ('/api/v25/projects/p/promote', None), ('/api/v26/projects/p/promote', None),
                       ('/api/v27/projects/p/promote', None), ('/api/v28/projects/p/promote', None)):
        refused[path] = api('POST', path, body)[0]
    ok = all(v == 410 for k, v in refused.items() if k.endswith('/build')) and \
        all(v == 501 for k, v in refused.items() if k.endswith('/promote'))
    record('demo/publish refused', ok, refused)

    # Synthetic account, project list, journal endpoints on an empty project.
    token = new_account(state)
    project = new_project(token, 'postdeploy fixture')
    state['fixture_project'] = project
    s, listed = api('GET', '/api/v28/projects', None, token)
    s2, latest = api('GET', f'/api/v28/projects/{project}/builds/latest', None, token)
    record('projects load + journal endpoint', s == 200 and any(p.get('id') == project for p in listed.get('projects', []))
           and s2 == 200 and latest == {'build': None}, f'projects={s} latest={s2} {latest}')

    # Preview + persistent data across restart and a new version (real preview worker and edge).
    key = internal_key(token, project)
    v1 = ws.commit(project_id=key, repository=fixture('v1'), message='postdeploy fixture v1 (synthetic)')
    view, err = preview_launch(token, project, v1.id)
    if not view or view.get('status') != 'RUNNING':
        record('preview creation', False, err or view)
        return
    record('preview creation', True, f"{view['id']} RUNNING data_storage={view.get('data_storage')} url={view['preview_url']}")
    url = view['preview_url'].rstrip('/')
    anon = http('GET', url + '/count')
    record('preview is private by default', anon[0] == 401 and view.get('access_mode') == 'PRIVATE',
           f"anonymous GET -> {anon[0]}; access_mode={view.get('access_mode')}")
    hdr = preview_header(token, project, view)
    http('POST', url + '/hit-postdeploy', {}, headers=hdr); http('POST', url + '/hit-postdeploy', {}, headers=hdr)
    first = http('GET', url + '/count', headers=hdr)[1]
    preview_stop(token, project, view['id'])
    view2, err = preview_launch(token, project, v1.id)
    after_restart = (http('GET', view2['preview_url'].rstrip('/') + '/count',
                          headers=preview_header(token, project, view2))[1] if view2 else err)
    record('data survives preview restart', first == 'v1:2' and after_restart == 'v1:2'
           and (view2 or {}).get('data_storage') == 'persistent',
           f'before={first} after_restart={after_restart} data_storage={(view2 or {}).get("data_storage")}')
    if view2:
        preview_stop(token, project, view2['id'])
    v2 = ws.commit(project_id=key, repository=fixture('v2'), message='postdeploy fixture v2 (synthetic)')
    view3, err = preview_launch(token, project, v2.id)
    after_version = (http('GET', view3['preview_url'].rstrip('/') + '/count',
                          headers=preview_header(token, project, view3))[1] if view3 else err)
    if view3:
        s_sh, sh = api('POST', f"/api/v28/projects/{project}/previews/{view3['id']}/sharing", {'mode': 'SHARED'}, token)
        from urllib.parse import parse_qs, urlsplit
        from .preview_access import HEADER, QUERY_PARAM
        share_tok = parse_qs(urlsplit((sh or {}).get('share_url', '')).query).get(QUERY_PARAM, [''])[0]
        shared = http('GET', view3['preview_url'].rstrip('/') + '/count', headers={HEADER: share_tok})[0]
        api('POST', f"/api/v28/projects/{project}/previews/{view3['id']}/sharing", {'mode': 'PRIVATE'}, token)
        time.sleep(6)  # router caches mode/token decisions for a few seconds
        revoked = http('GET', view3['preview_url'].rstrip('/') + '/count', headers={HEADER: share_tok})[0]
        record('share link works only while shared', s_sh == 200 and shared == 200 and revoked == 401,
               f'sharing={s_sh} shared GET={shared} after PRIVATE={revoked}')
    record('data survives a new version', after_version == 'v2:2', f'new version {v2.id} reads {after_version}')
    if view3:
        preview_stop(token, project, view3['id'])
    s, hist = api('GET', f'/api/v28/projects/{project}/history', None, token)
    record('versions listed', s == 200 and len(hist.get('versions', [])) == 2, f'history={s} versions={len(hist.get("versions", []))}')


CANCEL_PROMPT = ('אתר בעברית לרשימת קניות משפחתית: הוספת פריט עם כמות, סימון שנקנה ומחיקה. בלי התחברות משתמשים. '
                 '(בדיקת עצירה סינתטית)')


def stage_cancel_setup(state: dict) -> None:
    token = new_account(state)
    project = new_project(token, 'postdeploy cancel')
    revision, _ = run_discovery(token, project, CANCEL_PROMPT)
    a = plan_and_build(token, project, revision, CANCEL_PROMPT)
    s, out = api('POST', f'/api/v28/projects/{project}/builds/{a["build_id"]}/cancel', None, token)
    row = sql('SELECT status, error_code FROM build_jobs WHERE id = %s', (a['build_id'],))[0]
    res = reservation(a['build_id'])
    record('queued build cancelled', s == 200 and out.get('outcome') == 'cancelled' and row[0] == 'cancelled'
           and (res or {}).get('status') == 'RELEASED', f'api={s} {out} row={row} reservation={res}')
    revision, _ = run_discovery(token, project, CANCEL_PROMPT + ' ב')
    b = plan_and_build(token, project, revision, CANCEL_PROMPT + ' ב')
    # Simulates a stop that arrives after the worker claimed the build: the
    # worker must stop at its first step boundary, before any model call.
    sql_write('UPDATE build_jobs SET cancel_requested_at = now(), cancel_requested_by = %s WHERE id = %s AND status = %s',
              ('postdeploy-check', b['build_id'], 'queued'))
    state.update(cancel_project=project, build_a=a['build_id'], build_b=b['build_id'])


def stage_cancel_verify(state: dict) -> None:
    token, project, b = state['token'], state['cancel_project'], state['build_b']

    def poll():
        s, d = api('GET', f'/api/v28/projects/{project}/builds/{b}', None, token)
        return d if s == 200 and d.get('status') in ('ready', 'failed', 'cancelled') else None
    # A job pushed while the worker was stopped can be lost to the stopped
    # worker's open read; the janitor re-dispatches it after 3 minutes.
    d = wait(poll, 480, 5) or {}
    res = reservation(b)
    # Worker-side evidence (the API view strips the economics keys).
    row = sql("SELECT evidence_json->>'external_model_calls', evidence_json->>'billing', evidence_json->>'provider_spend_usd', "
              "started_at IS NOT NULL FROM build_jobs WHERE id = %s", (b,))[0]
    record('running build stops at the next step', d.get('status') == 'cancelled' and d.get('error_code') == 'cancelled_by_user'
           and row[0] == '0' and row[1] == 'released' and row[3] and (res or {}).get('status') == 'RELEASED',
           f"status={d.get('status')} code={d.get('error_code')} claimed_by_worker={row[3]} model_calls={row[0]} "
           f"billing={row[1]} spend={row[2]} reservation={res}")
    s, log = api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after=0', None, token)
    events = (log or {}).get('events') or []
    later = api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after={events[0]["seq"]}', None, token)[1] if events else {}
    s2, latest = api('GET', f'/api/v28/projects/{project}/builds/latest', None, token)
    record('journal resumes after refresh', s == 200 and any(e['kind'] == 'cancel' for e in events)
           and len((later or {}).get('events', [])) == len(events) - 1 and (latest or {}).get('build', {}).get('build_id') == b,
           [f"{e['kind']}: {e['message']}" for e in events][:8])
    other = new_project(token, 'postdeploy other')
    s3, _ = api('POST', f'/api/v28/projects/{other}/builds/{b}/cancel', None, token)
    record('cancel is owner/project scoped', s3 == 404, f'cancel via another project -> {s3}')


PAID_PROMPT = ('אתר בעברית לניהול תורים למספרה קטנה: טופס קביעת תור עם שם, טלפון, תאריך ושעה, רשימת התורים הקרובים '
               'ממוינת לפי זמן, ביטול תור, ומניעת שני תורים באותה שעה. בלי התחברות משתמשים.')


def stage_paid_create(state: dict) -> None:
    token = new_account(state)
    project = new_project(token, 'postdeploy paid build')
    revision, view = run_discovery(token, project, PAID_PROMPT)
    record('discovery', True, f"revision {revision}; summary: {json.dumps(view.get('summary'), ensure_ascii=False)[:500]}")
    built = plan_and_build(token, project, revision, PAID_PROMPT)
    record('approval -> build queued', True, built)
    state.update(paid_project=project, paid_build=built['build_id'])


def stage_paid_verify(state: dict) -> None:
    token, project, b = state['token'], state['paid_project'], state['paid_build']
    s, d = api('GET', f'/api/v28/projects/{project}/builds/{b}', None, token)
    ev = d.get('evidence') or {}
    res = reservation(b)
    usage = ev.get('provider_usage') or {}
    record('paid build outcome', d.get('status') == 'ready',
           f"status={d.get('status')} code={d.get('error_code')} repairs={d.get('repair_rounds')} "
           f"version={d.get('result_version_id')} message={str(d.get('error_message'))[:300]}")
    record('cost settlement', res is not None and res['status'] in ('SETTLED', 'RELEASED'),
           f"authorized_spend={ev.get('provider_spend_usd')} calls={ev.get('external_model_calls')} "
           f"binding={ev.get('model_budget_binding')} reservation={res} usage={json.dumps(usage, default=str)[:500]}")
    bc = ev.get('browser_check')
    record('browser check in the build', isinstance(bc, dict) and bc.get('status') == 'passed', bc)
    reviews = ev.get('product_review') or []
    record('QA review in the build', bool(reviews), [{k: r.get(k) for k in ('round', 'reviewer', 'model', 'blocking')} for r in reviews][:3])
    s, log = api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after=0', None, token)
    events = (log or {}).get('events') or []
    record('build journal', len(events) >= 3, [f"{e['kind']}: {e['message']}" for e in events][:14])
    vid = d.get('result_version_id')
    if not vid:
        return
    view, err = preview_launch(token, project, vid, seconds=240)
    if not view or view.get('status') != 'RUNNING':
        record('preview of the built version', False, err or view)
        return
    record('preview of the built version', True, f"{view['id']} data_storage={view.get('data_storage')} "
                                                  f"acceptance={view.get('acceptance_status')} {view.get('acceptance_summary')}")
    # Acceptance runs after RUNNING on a scratch copy; wait for it to be stored.
    def accepted():
        s, v = api('GET', f"/api/v28/projects/{project}/previews/{view['id']}", None, token)
        return v if s == 200 and v.get('acceptance_status') not in (None, 'NOT_CONFIGURED', 'PENDING') else None
    v2 = wait(accepted, 180, 4) or {}
    page = http('GET', view['preview_url'], timeout=20, headers=preview_header(token, project, view))
    s_again, v3 = api('GET', f"/api/v28/projects/{project}/previews/{view['id']}", None, token)
    record('acceptance stored, page responsive afterwards',
           bool(v2) and page[0] == 200 and (v3 or {}).get('status') == 'RUNNING',
           f"acceptance={v2.get('acceptance_status')} summary={str(v2.get('acceptance_summary'))[:300]} "
           f"GET /={page[0]} preview={(v3 or {}).get('status')} data_storage={(v3 or {}).get('data_storage')}")
    preview_stop(token, project, view['id'])
    view4, err = preview_launch(token, project, vid, seconds=240)
    record('built version restarts', bool(view4) and view4.get('status') == 'RUNNING' and view4.get('data_storage') == 'persistent',
           f"{(view4 or {}).get('status')} data_storage={(view4 or {}).get('data_storage')} {err or ''}")
    state['paid_preview'] = (view4 or {}).get('preview_url')


CRASH_PROMPT = ('אתר בעברית לרשימת ספרים לקריאה: הוספת ספר עם שם וסופר, רשימה, וסימון שנקרא. בלי התחברות משתמשים. '
                '(בדיקת התאוששות מקריסה)')


def stage_crash_create(state: dict) -> None:
    token = new_account(state)
    project = new_project(token, 'postdeploy crash')
    revision, _ = run_discovery(token, project, CRASH_PROMPT)
    built = plan_and_build(token, project, revision, CRASH_PROMPT)
    state.update(crash_project=project, crash_build=built['build_id'])

    def first_model_call():
        s, d = api('GET', f"/api/v28/projects/{project}/builds/{built['build_id']}/events?after=0", None, state['token'])
        return any(e['kind'] == 'model' for e in (d or {}).get('events', [])) or None
    record('crash: build reached its first model call', bool(wait(first_model_call, 300, 2)), built['build_id'])


def stage_crash_verify(state: dict) -> None:
    token, project, b = state['token'], state['crash_project'], state['crash_build']

    def done():
        s, d = api('GET', f'/api/v28/projects/{project}/builds/{b}', None, token)
        return d if s == 200 and d.get('status') in ('ready', 'failed', 'cancelled') else None
    d = wait(done, 1500, 10) or {}
    row = sql('SELECT recovery_attempts, evidence_json->>\'provider_spend_usd\' FROM build_jobs WHERE id = %s', (b,))[0]
    events = (api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after=0', None, token)[1] or {}).get('events', [])
    record('crash: build recovered after its worker was killed',
           d.get('status') == 'ready' and row[0] == 1 and any(e['kind'] == 'info' for e in events),
           f"status={d.get('status')} code={d.get('error_code')} recovery_attempts={row[0]} spend_after_recovery={row[1]} "
           f"reservation={reservation(b)} events={[e['message'] for e in events if e['kind'] in ('info', 'phase')][-4:]}")


STAGES = {'free': stage_free, 'cancel-setup': stage_cancel_setup, 'cancel-verify': stage_cancel_verify,
          'paid-create': stage_paid_create, 'paid-verify': stage_paid_verify,
          'crash-create': stage_crash_create, 'crash-verify': stage_crash_verify}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    stage = argv[0] if argv else 'free'
    state = load_state()
    start_api()
    try:
        STAGES[stage](state)
    except Exception as exc:
        record(f'{stage} aborted', False, f'{type(exc).__name__}: {exc}')
    finally:
        save_state(state)
    failed = [r['check'] for r in RESULTS if not r['ok']]
    lines = '\n'.join(f"{'PASS' if r['ok'] else 'FAIL'} {r['check']}: {r['detail'][:420]}" for r in RESULTS)
    print(f'::notice title=postdeploy {stage} summary::' + lines[:3800].replace('%', '%25').replace('\n', '%0A'), flush=True)
    print('POSTDEPLOY ' + json.dumps({'stage': stage, 'passed': len(RESULTS) - len(failed), 'failed': failed},
                                     ensure_ascii=False), flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
