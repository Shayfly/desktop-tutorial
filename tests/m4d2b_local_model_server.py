"""Real local model server for M4D.2b item 3 ("EXECUTE THE ACTUAL RQ
PRODUCTION JOB"): implements the exact OpenAI-chat-completions-compatible
protocol `omni_prod.model_gateway.OpenAICompatibleGateway.complete()`
speaks -- `POST {base_url}/chat/completions` with a JSON body
`{model, messages, temperature, max_tokens}`, responding
`{"choices":[{"message":{"content": "<text>"}}]}`.

This is not a new, invented boundary. It is the REAL, already-documented
"local-first" gateway boundary this codebase ships for exactly this
purpose:

  - `omni_prod.model_runtime_config.ModelRuntimeConfig.from_env()`'s
    *primary* route defaults to
    `OMNI_LOCAL_MODEL_URL=http://127.0.0.1:8001/v1`, `external=False`
    -- i.e. production is designed, by default, to talk to a *local*
    model server, not a paid external one (`OMNI_ZERO_COST_MODE=1` and
    `OMNI_ALLOW_EXTERNAL_FALLBACK=0` are also both the defaults).
  - `omni_prod.routed_gateway.RoutedModelGateway.__init__` enforces this:
    `if primary.endpoint.external: raise ValueError('primary route must
    be local/self-hosted')`.

So this file stands up a real, independent HTTP server bound to a real
TCP port on loopback -- reachable by a genuinely separate OS process over
real sockets, not a monkeypatch of anything inside `omni_prod` -- and
points `OMNI_LOCAL_MODEL_URL` at it. It stands in for a real hosted LLM
only because this sandbox has no network route to one (a pre-existing,
already-disclosed constraint -- see STATUS.md's M4 section and
PATCH_APPLICATION_REPORT.md's M4D.2b section).

Deterministic-response protocol (disclosed, not hidden): this is not a
language model, so it cannot read natural-language text and "decide" a
classification the way a real model would. Instead it looks for a literal
marker embedded in the request content and returns a fixed, disclosed
response for it:

  - Classification requests (`ChangeClassifierAgent.classify()`; the user
    payload has 'approved_spec' + 'followup' keys): the followup text
    must contain `M4D2B_CLASSIFY:<category>` (category one of
    system_bug | missing_requirement | change_request | ambiguous). For
    the two free-repair categories it must also contain
    `M4D2B_IDS:<comma-separated-acceptance-ids>` -- real acceptance ids
    that exist in the spec being classified, since
    `ChangeAssessment.from_dict` requires non-empty, real ids for those
    two categories and would otherwise raise.
  - Repair requests (`RepairAgent.repair()`; the user payload has a
    'failures' key): always returns a fixed, trivial, real patch
    (`{"files":[{"path":"M4D2B_NOTES.md","content":"..."}]}`) that does
    not attempt to actually fix anything -- these requests exist, in
    M4D.2b's tests, specifically to reach (and honestly document) the
    real sandbox-executor Docker-image blocker described in
    PATCH_APPLICATION_REPORT.md's M4D.2b section, not to produce a
    passing candidate.

Anything else gets a 500 with a clear message, so a test that hits an
unsupported path fails loudly instead of silently getting a wrong answer.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _classification_content(followup: str) -> str:
    marker = 'M4D2B_CLASSIFY:'
    idx = followup.find(marker)
    if idx == -1:
        raise ValueError(f'no M4D2B_CLASSIFY: marker in followup: {followup!r}')
    rest = followup[idx + len(marker):]
    category = rest.split()[0].strip()
    ids: list[str] = []
    ids_marker = 'M4D2B_IDS:'
    j = followup.find(ids_marker)
    if j != -1:
        ids_rest = followup[j + len(ids_marker):]
        ids = [x for x in ids_rest.split()[0].strip().split(',') if x]
    return json.dumps({
        'category': category,
        'reason': f'm4d2b deterministic local test model: forced category={category!r}',
        'acceptance_ids': ids,
    })


def _repair_content() -> str:
    return json.dumps({
        'files': [{
            'path': 'M4D2B_NOTES.md',
            'content': (
                '# M4D.2b real-worker-execution test artifact\n\n'
                'This file was written by a deterministic local test model '
                'server standing in for a real LLM (no external provider is '
                'reachable from this sandbox). It intentionally does not fix '
                'anything real; this repair path exists to reach (and '
                'honestly document) the sandbox-executor Docker-image '
                'blocker, not to produce a passing candidate. See '
                'PATCH_APPLICATION_REPORT.md, M4D.2b section.\n'
            ),
        }],
    })


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):  # noqa: A002 - silence default stderr logging
        pass

    def do_POST(self):  # noqa: N802 - stdlib naming
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode('utf-8'))
            messages = body['messages']
            user_content = next(m['content'] for m in messages if m['role'] == 'user')
            payload = json.loads(user_content)
            if 'failures' in payload:
                content = _repair_content()
            elif 'followup' in payload and 'approved_spec' in payload:
                content = _classification_content(payload['followup'])
            else:
                raise ValueError(f'unsupported m4d2b local model request shape: keys={sorted(payload)}')
            response = {'choices': [{'message': {'content': content}}]}
            out = json.dumps(response).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as exc:  # pragma: no cover - defensive, surfaces as a real HTTP 500
            out = json.dumps({'error': f'{type(exc).__name__}: {exc}'}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)


class LocalModelServer:
    """Real HTTP server on a background thread. Use as a context manager or
    call start()/stop() directly. `base_url` is what to put in
    OMNI_LOCAL_MODEL_URL (includes the '/v1' suffix production expects)."""

    def __init__(self, host: str = '127.0.0.1', port: int = 8091):
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f'http://{self.host}:{self.port}/v1'

    def start(self) -> 'LocalModelServer':
        self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def __enter__(self) -> 'LocalModelServer':
        return self.start()

    def __exit__(self, *exc_info) -> None:
        self.stop()
