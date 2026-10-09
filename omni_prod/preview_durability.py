"""Self-test: a preview's product data survives a restart and a new version.

Directive 2026-10-09 §13 asks to prove each data layer separately: the
platform's Postgres and R2 say nothing about whether the *generated app's*
data is kept. This runs on the preview host (deploy-worker) with the real
DockerPreviewProvider and no model calls ($0):

  1. version A starts with the project's data directory, records two hits;
  2. A is removed (a preview stop / expiry / host restart looks the same);
  3. version B (different code) starts for the same project and must read 2;
  4. a scratch copy (persistent=False, what acceptance probes use) must read
     0 -- synthetic test records never reach the product's data;
  5. a different project must read 0 -- no data shared between projects.

Everything it created is removed, the data directories included.
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from urllib import request as urlrequest

_APP = r'''
import http.server, os, pathlib
DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
VERSION = "%s"
class H(http.server.BaseHTTPRequestHandler):
    def _send(self, body):
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _count(self):
        return int(DATA.read_text()) if DATA.exists() else 0
    def do_GET(self):
        self._send(VERSION + ":" + str(self._count()) if self.path == "/count" else "ok")
    def do_POST(self):
        DATA.write_text(str(self._count() + 1)); self._send("hit")
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''


def fixture_repository(version: str) -> dict[str, str]:
    return {
        'app.py': _APP % version,
        '.omni/project.json': json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim',
                                          'start': ['python', 'app.py'], 'port': 8000, 'health_path': '/'}),
    }


def _http(method: str, url: str, timeout: float = 5.0) -> str:
    req = urlrequest.Request(url, method=method, data=b'' if method == 'POST' else None)
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode()


def _wait(url: str, seconds: float = 40.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            _http('GET', url, timeout=2)
            return
        except Exception:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


def selftest(provider, *, probe_host: str = '127.0.0.1', http=_http, wait=_wait) -> dict:
    from .preview_runtime import project_data_dir
    if not getattr(provider, 'persistent_data', False):
        return {'status': 'NOT_CONFIGURED', 'detail': 'OMNI_PREVIEW_DATA_ROOT is not set: preview data is temporary'}
    project = f'selftest-{uuid.uuid4().hex[:12]}'
    other = project + '-other'
    started, seen = [], {}

    def run(tag, version, *, project_id=project, persistent=True):
        s = provider.start(preview_id=f'prv_selftest{uuid.uuid4().hex[:8]}{tag}', project_id=project_id,
                           version_id=version, repository=fixture_repository(version), persistent=persistent)
        started.append(s)
        if s.host_port is None:
            raise RuntimeError(f'{tag}: container exited at start')
        base = f'http://{probe_host}:{s.host_port}'
        wait(base + '/')
        return s, base

    def remove(s):
        provider.stop(s.container_id)
        provider.remove_workdir(s.workdir)

    try:
        a, base = run('a', 'v1')
        http('POST', base + '/hit'); http('POST', base + '/hit')
        seen['v1_before_stop'] = http('GET', base + '/count')
        remove(a)
        b, base = run('b', 'v2')
        seen['v2_after_restart'] = http('GET', base + '/count')
        scratch, base = run('q', 'v2', persistent=False)
        seen['scratch_copy'] = http('GET', base + '/count')
        foreign, base = run('o', 'v2', project_id=other)
        seen['other_project'] = http('GET', base + '/count')
        ok = (seen['v1_before_stop'] == 'v1:2' and seen['v2_after_restart'] == 'v2:2'
              and seen['scratch_copy'] == 'v2:0' and seen['other_project'] == 'v2:0')
        return {'status': 'PASS' if ok else 'FAIL', 'seen': seen}
    except Exception as exc:
        return {'status': 'ERROR', 'seen': seen, 'detail': f'{type(exc).__name__}: {exc}'[:300]}
    finally:
        for s in started:
            try:
                remove(s)
            except Exception:
                pass
        for pid in (project, other):
            shutil.rmtree(project_data_dir(provider.data_root, pid), ignore_errors=True)


def main() -> int:
    import os
    from .preview_runtime import DockerPreviewProvider
    result = selftest(DockerPreviewProvider(workspace=None),
                      probe_host=os.getenv('OMNI_PREVIEW_PROBE_HOST', '127.0.0.1'))
    level = 'notice' if result['status'] == 'PASS' else 'warning'
    print(f"::{level} title=preview-data::{result['status']} {json.dumps(result, ensure_ascii=False)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
