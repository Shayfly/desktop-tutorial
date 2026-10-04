"""M5 remediation: provider artifact downloads are SSRF-hardened."""
from __future__ import annotations

import http.server
import json
import threading
import unittest
from urllib import request

from omni_prod.safe_fetch import (
    SafeFetcher, UnsafeURL, _GuardedHTTPConnection, is_public_address, validate_public_url)


def resolver_for(mapping):
    def resolve(host, port, proto=None):
        return [(2, 1, 6, "", (mapping[host], port))]
    return resolve


PUBLIC = resolver_for({"cdn.provider.example": "93.184.216.34", "images.provider.example": "93.184.216.35",
                       "evil.example": "10.0.0.5", "rebind.example": "169.254.169.254"})


class _Resp:
    def __init__(self, body=b"\x89PNG\r\n\x1a\nrest", headers=None, url=None):
        self._body, self.headers, self.url = body, headers or {"Content-Type": "image/png"}, url
    def read(self, n=-1): return self._body if n < 0 else self._body[:n]
    def __enter__(self): return self
    def __exit__(self, *a): return False


class UrlValidationTests(unittest.TestCase):
    def test_localhost_rejected(self):
        for url in ("https://localhost/x.png", "https://LOCALHOST./x", "https://foo.localhost/x",
                    "https://metadata.google.internal/computeMetadata/v1/"):
            with self.subTest(url=url), self.assertRaises(UnsafeURL):
                validate_public_url(url, resolver=PUBLIC)

    def test_loopback_metadata_private_and_link_local_literals_rejected(self):
        for url in ("https://127.0.0.1/x", "https://127.10.0.1/x", "https://[::1]/x", "https://169.254.169.254/latest/meta-data/",
                    "https://10.1.2.3/x", "https://172.16.0.9/x", "https://192.168.1.1/x", "https://[fe80::1]/x",
                    "https://[fd00::1]/x", "https://100.64.0.1/x", "https://0.0.0.0/x", "https://[::ffff:127.0.0.1]/x"):
            with self.subTest(url=url), self.assertRaises(UnsafeURL):
                validate_public_url(url, resolver=PUBLIC)

    def test_names_resolving_to_internal_addresses_rejected(self):
        with self.assertRaises(UnsafeURL):
            validate_public_url("https://evil.example/x.png", resolver=PUBLIC)
        with self.assertRaises(UnsafeURL):
            validate_public_url("https://rebind.example/x.png", resolver=PUBLIC)

    def test_scheme_credentials_and_allowlist(self):
        with self.assertRaises(UnsafeURL):
            validate_public_url("http://cdn.provider.example/x.png", resolver=PUBLIC)
        with self.assertRaises(UnsafeURL):
            validate_public_url("ftp://cdn.provider.example/x.png", resolver=PUBLIC)
        with self.assertRaises(UnsafeURL):
            validate_public_url("https://user:pw@cdn.provider.example/x.png", resolver=PUBLIC)
        with self.assertRaises(UnsafeURL):
            validate_public_url("https://cdn.provider.example/x.png", allowed_hosts=("images.provider.example",),
                                resolver=PUBLIC)

    def test_valid_provider_url_accepted(self):
        host, addrs = validate_public_url("https://cdn.provider.example/out/1.png",
                                          allowed_hosts=("provider.example",), resolver=PUBLIC)
        self.assertEqual(host, "cdn.provider.example")
        self.assertEqual(addrs, ("93.184.216.34",))
        self.assertTrue(is_public_address("93.184.216.34"))


class RedirectTests(unittest.TestCase):
    def test_redirect_to_private_ip_rejected(self):
        handler = SafeFetcher(resolver=PUBLIC).redirect_handler()
        req = request.Request("https://cdn.provider.example/x.png")
        for target in ("https://10.0.0.5/x.png", "https://169.254.169.254/latest/", "https://evil.example/x",
                       "http://cdn.provider.example/x.png"):
            with self.subTest(target=target), self.assertRaises(UnsafeURL):
                handler.redirect_request(req, None, 302, "Found", {}, target)

    def test_valid_redirect_strips_credentials_across_hosts(self):
        handler = SafeFetcher(resolver=PUBLIC).redirect_handler()
        req = request.Request("https://cdn.provider.example/x.png", headers={"Authorization": "Bearer k"})
        new = handler.redirect_request(req, None, 302, "Found", {}, "https://images.provider.example/y.png")
        self.assertEqual(new.full_url, "https://images.provider.example/y.png")
        self.assertIsNone(new.get_header("Authorization"))

    def test_final_url_after_transport_is_revalidated(self):
        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp(url="https://10.0.0.5/x.png"))
        with self.assertRaises(UnsafeURL):
            fetcher.get("https://cdn.provider.example/x.png")


class ResponseLimitTests(unittest.TestCase):
    def test_content_type_validated(self):
        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp(headers={"Content-Type": "text/html"}))
        with self.assertRaises(UnsafeURL):
            fetcher.get("https://cdn.provider.example/x.png")

    def test_size_limits_header_and_body(self):
        big_header = SafeFetcher(resolver=PUBLIC, max_bytes=10, urlopen=lambda req, timeout: _Resp(
            headers={"Content-Type": "image/png", "Content-Length": "999"}))
        with self.assertRaises(UnsafeURL):
            big_header.get("https://cdn.provider.example/x.png")
        big_body = SafeFetcher(resolver=PUBLIC, max_bytes=4, urlopen=lambda req, timeout: _Resp())
        with self.assertRaises(UnsafeURL):
            big_body.get("https://cdn.provider.example/x.png")

    def test_valid_download(self):
        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp())
        data, ctype = fetcher.get("https://cdn.provider.example/x.png")
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertEqual(ctype, "image/png")
        self.assertEqual(fetcher.timeout_seconds, 30.0)


class PeerCheckTests(unittest.TestCase):
    """A real loopback server: even if DNS validation were bypassed (rebinding),
    the connection-level peer check refuses an internal address."""

    def test_connection_to_loopback_peer_is_refused(self):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b"secret")
            def log_message(self, *a): pass
        server = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            conn = _GuardedHTTPConnection("127.0.0.1", server.server_port, timeout=3)
            with self.assertRaises(UnsafeURL):
                conn.connect()
        finally:
            server.shutdown()
            server.server_close()


class ProviderIntegrationTests(unittest.TestCase):
    def test_image_provider_refuses_internal_output_url(self):
        try:
            from tests.test_m5_media_provider_adapters import FakePredictionAPI, REQ, _provider
        except ModuleNotFoundError:
            from test_m5_media_provider_adapters import FakePredictionAPI, REQ, _provider
        api = FakePredictionAPI()
        original = api._prediction
        api._prediction = lambda pid, status: {**original(pid, status),
                                               **({"output": ["https://169.254.169.254/latest/meta-data/"]}
                                                  if status == "succeeded" else {})}
        provider = _provider(api)
        handle = provider.submit(REQ, idempotency_key="cap_ssrf")
        while not provider.poll(handle).terminal:
            pass
        with self.assertRaises(ValueError) as ctx:
            provider.collect(handle)
        self.assertIn("rejected", str(ctx.exception))

    def test_output_host_allowlist_is_configurable(self):
        from omni_prod.providers.image_provider import ImageProviderConfig, MemorySubmissionJournal, PredictionImageProvider
        try:
            from tests.test_m5_media_provider_adapters import ENV
        except ModuleNotFoundError:
            from test_m5_media_provider_adapters import ENV
        env = dict(ENV, OMNI_IMAGE_PROVIDER_OUTPUT_HOSTS="delivery.images.example")
        provider = PredictionImageProvider(config=ImageProviderConfig.from_env(env), resolve_reference=lambda r: "k",
                                           journal=MemorySubmissionJournal())
        self.assertEqual(provider.fetcher.allowed_hosts, ("delivery.images.example", "images.example"))


if __name__ == "__main__":
    unittest.main()
