import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Serves page.html from this directory: the test writes either the page with the hiding idiom or its rewrite.
PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html'), encoding='utf-8').read()


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = PAGE.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


HTTPServer(('127.0.0.1', int(os.environ['PORT'])), H).serve_forever()
