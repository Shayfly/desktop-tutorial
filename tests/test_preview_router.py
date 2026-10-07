"""Preview router: host -> preview id -> local container port (real HTTP)."""
import http.client
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from omni_prod.preview_router import RouteTable, make_handler, preview_id_for_host
from omni_prod.preview_runtime import external_preview_url, preview_host_label, preview_id_from_host_label

SUFFIX = '151-145-89-132.sslip.io'
PID = 'prv_0123456789abcdef0123456789abcdef'


class _App(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = f'league table {self.path}'.encode()
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers['Content-Length']); data = self.rfile.read(n)
        self.send_response(201); self.send_header('Content-Length', str(len(data))); self.end_headers()
        self.wfile.write(data)


def _serve(handler):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.app = _serve(_App)
        app_port = self.app.server_address[1]
        routes = RouteTable(lambda pid: ('oracle-worker-01', app_port) if pid == PID else None, 'oracle-worker-01')
        self.router = _serve(make_handler(routes, SUFFIX))
        self.host = f'{preview_host_label(PID)}.{SUFFIX}'

    def tearDown(self):
        self.app.shutdown(); self.router.shutdown()

    def _req(self, method, path, host, body=None):
        c = http.client.HTTPConnection('127.0.0.1', self.router.server_address[1], timeout=5)
        c.request(method, path, body=body, headers={'Host': host})
        r = c.getresponse(); data = r.read(); c.close()
        return r.status, data

    def test_url_uses_a_dns_safe_label_and_round_trips(self):
        url = external_preview_url(PID, 'https://{preview_id}.' + SUFFIX)
        self.assertEqual(url, f'https://prv-0123456789abcdef0123456789abcdef.{SUFFIX}')
        self.assertEqual(preview_id_from_host_label('prv-0123456789abcdef0123456789abcdef'), PID)
        self.assertIsNone(preview_id_for_host('evil.example.com', SUFFIX))
        self.assertIsNone(preview_id_for_host(f'a.{self.host}', SUFFIX))

    def test_proxies_get_and_post_to_the_preview(self):
        self.assertEqual(self._req('GET', '/standings?x=1', self.host), (200, b'league table /standings?x=1'))
        self.assertEqual(self._req('POST', '/teams', self.host, b'{"name":"A"}'), (201, b'{"name":"A"}'))

    def test_caddy_ask_only_for_running_previews(self):
        self.assertEqual(self._req('GET', f'/_caddy_ask?domain={self.host}', 'x')[0], 200)
        self.assertEqual(self._req('GET', f'/_caddy_ask?domain=prv-ffffffffffffffff.{SUFFIX}', 'x')[0], 404)
        self.assertEqual(self._req('GET', '/_caddy_ask?domain=example.com', 'x')[0], 404)

    def test_unknown_preview_is_404_and_route_owned_by_other_host_is_ignored(self):
        self.assertEqual(self._req('GET', '/', f'prv-ffffffffffffffff.{SUFFIX}')[0], 404)
        other = RouteTable(lambda pid: ('another-host', 1), 'oracle-worker-01')
        self.assertIsNone(other.port_for(PID))


if __name__ == '__main__':
    unittest.main()
