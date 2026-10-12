"""Equipment loans (hand-written UI-test fixture, not model output)."""
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.path = '/templates/index.html'
        elif self.path == '/edit':
            self.path = '/templates/edit.html'
        return super().do_GET()


ThreadingHTTPServer(('127.0.0.1', int(os.getenv('PORT', '8000'))), H).serve_forever()
