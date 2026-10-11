"""Preview host for the local UI test.

Stands in for the preview WORKER only (no Docker daemon here): it starts the
stored version's app as a local process instead of a container, then records
the runtime and marks the preview RUNNING through the real repository. The
ROUTER in front is the real code: omni_prod.preview_inspector wrapping
omni_prod.preview_router, with real PreviewAccess tokens, over TLS on :443."""
import os, ssl, subprocess, sys, tempfile, threading, time, urllib.request
sys.path.insert(0, sys.argv[1])
from http.server import ThreadingHTTPServer
from common import DB, LocalFileStore
from omni_prod.db import DatabasePool
from omni_prod.preview_access import PreviewAccess
from omni_prod.preview_inspector import make_inspecting_handler
from omni_prod.preview_repository import PostgresPreviewRepository
from omni_prod.preview_router import RouteTable
from omni_prod.preview_runtime import external_preview_url
from omni_prod.workspace import PostgresProjectWorkspace

pool = DatabasePool(DB)
repo = PostgresPreviewRepository(pool)
ws = PostgresProjectWorkspace(pool, LocalFileStore())
TEMPLATE = os.environ['PREVIEW_DOMAIN_TEMPLATE']
procs = []


def free_port():
    import socket
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def launcher():
    while True:
        with pool.connection() as conn:
            rows = conn.execute("SELECT id, project_id, version_id FROM project_previews WHERE status = 'STARTING' "
                                "AND internal_container_id IS NULL").fetchall()
        for pid, project, version in rows:
            files = ws.get(project_id=project, version_id=version).repository()
            d = tempfile.mkdtemp(prefix='prv-')
            for path, content in files.items():
                p = os.path.join(d, path); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'w').write(content)
            port = free_port()
            proc = subprocess.Popen([sys.executable, 'app.py'], cwd=d, env={**os.environ, 'PORT': str(port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            procs.append(proc)
            repo.record_runtime(pid, container_id=f'local-process-{proc.pid}', runtime_host='127.0.0.1',
                                host_port=port, workdir=d)
            for _ in range(50):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1); break
                except Exception:
                    time.sleep(0.1)
            repo.mark_running(pid, url=external_preview_url(pid, TEMPLATE))
            print('preview running', pid, port, flush=True)
        time.sleep(0.5)


threading.Thread(target=launcher, daemon=True).start()
handler = make_inspecting_handler(RouteTable(repo.get_route, '127.0.0.1'), 'prv.148ai.test',
                                  access=PreviewAccess(pool), enabled=True, origins=['http://127.0.0.1:8148'])
srv = ThreadingHTTPServer(('127.0.0.1', 443), handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain('tls.crt', 'tls.key')
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
print('router on https://*.prv.148ai.test (127.0.0.1:443)', flush=True)
srv.serve_forever()
