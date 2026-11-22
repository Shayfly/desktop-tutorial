"""Static content server for the Studio Noa salon website (stdlib only)."""
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

sys.path.insert(0, BASE_DIR)
from page import render_page  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("salon")

CONTENT_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Salon/1.0"

    def log_message(self, fmt, *args):  # route access log through logging
        log.info("%s %s", self.address_string(), fmt % args)

    def _send(self, status, body, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _not_found(self):
        body = json.dumps({"error": "הדף לא נמצא"}, ensure_ascii=False).encode("utf-8")
        self._send(404, body, "application/json; charset=utf-8")

    def _asset(self, name):
        if not name or "/" in name or "\\" in name or ".." in name or name.startswith("."):
            return self._not_found()
        path = os.path.join(ASSETS_DIR, name)
        real = os.path.realpath(path)
        if not real.startswith(os.path.realpath(ASSETS_DIR) + os.sep) or not os.path.isfile(real):
            return self._not_found()
        ext = os.path.splitext(real)[1].lower()
        ctype = CONTENT_TYPES.get(ext)
        if ctype is None:
            return self._not_found()
        with open(real, "rb") as fh:
            data = fh.read()
        self._send(200, data, ctype, {"Cache-Control": "public, max-age=3600"})

    def do_GET(self):
        try:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(200, render_page().encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/health":
                body = json.dumps({"status": "ok"}).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            elif path.startswith("/assets/"):
                self._asset(path[len("/assets/"):])
            else:
                self._not_found()
        except Exception:
            log.exception("unexpected error")
            body = json.dumps({"error": "שגיאה בשרת"}, ensure_ascii=False).encode("utf-8")
            self._send(500, body, "application/json; charset=utf-8")

    do_HEAD = do_GET

    def _method_not_allowed(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(min(length, 65536))
        body = json.dumps({"error": "הפעולה אינה נתמכת"}, ensure_ascii=False).encode("utf-8")
        self._send(405, body, "application/json; charset=utf-8", {"Allow": "GET, HEAD"})

    do_POST = _method_not_allowed
    do_PUT = _method_not_allowed
    do_DELETE = _method_not_allowed
    do_PATCH = _method_not_allowed


def make_server(port):
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main():
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(port)
    log.info("listening on 0.0.0.0:%d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
