"""SSRF-hardened HTTP GET for URLs that come from third parties.

Used for provider-returned artifact URLs (M5 Task 9 image outputs). Every
hop is checked:

* scheme must be https (http only when explicitly allowed);
* no userinfo in the URL; host must be present;
* names like ``localhost``/``*.localhost``/``*.internal``/``metadata*`` are refused;
* every address the host resolves to must be globally routable: loopback,
  RFC1918/ULA private, link-local (incl. 169.254.169.254 metadata), CGNAT,
  multicast, reserved and unspecified ranges are refused;
* optional host allowlist (exact host or subdomain of an allowed suffix);
* every redirect target is re-validated (max 3 redirects);
* the connected socket's peer address is checked again after connect, so a
  DNS answer that changes between validation and connection (rebinding)
  cannot reach an internal address;
* Content-Length and the streamed body are capped; Content-Type must be in the
  allowed set; a timeout applies to connect and read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import http.client
import ipaddress
import socket
import ssl
from typing import Callable, Iterable
from urllib import parse, request

__all__ = ["SafeFetcher", "UnsafeURL", "is_public_address", "validate_public_url"]

_BLOCKED_NAMES = ("localhost", "metadata", "metadata.google.internal", "instance-data")
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".localdomain", ".home.arpa")


class UnsafeURL(ValueError):
    """The URL (or a redirect / resolved address) is not safe to fetch."""


def is_public_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if (ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved
            or ip.is_unspecified):
        return False
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"):  # CGNAT
        return False
    return bool(ip.is_global)


def _host_allowed(host: str, allowed_hosts: Iterable[str]) -> bool:
    allowed = [h.strip().lower().lstrip(".") for h in allowed_hosts if h and h.strip()]
    if not allowed:
        return True
    return any(host == a or host.endswith("." + a) for a in allowed)


def validate_public_url(url: str, *, allow_http: bool = False, allowed_hosts: Iterable[str] = (),
                        resolver: Callable = socket.getaddrinfo) -> tuple[str, tuple[str, ...]]:
    parts = parse.urlsplit(url)
    schemes = {"https", "http"} if allow_http else {"https"}
    if parts.scheme.lower() not in schemes:
        raise UnsafeURL(f"scheme {parts.scheme or '(none)'} is not allowed")
    if parts.username is not None or parts.password is not None:
        raise UnsafeURL("credentials in URL are not allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UnsafeURL("URL has no host")
    if host in _BLOCKED_NAMES or host.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeURL(f"host {host} is internal")
    if not _host_allowed(host, allowed_hosts):
        raise UnsafeURL(f"host {host} is not in the provider allowlist")
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None
    if literal is not None:
        addresses = (str(literal),)
    else:
        try:
            infos = resolver(host, parts.port or (443 if parts.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        except (socket.gaierror, OSError) as exc:
            raise UnsafeURL(f"host {host} does not resolve") from exc
        addresses = tuple(sorted({info[4][0] for info in infos}))
        if not addresses:
            raise UnsafeURL(f"host {host} does not resolve")
    blocked = [a for a in addresses if not is_public_address(a)]
    if blocked:
        raise UnsafeURL(f"host {host} resolves to a non-public address")
    return host, addresses


class _PeerCheckMixin:
    def connect(self):  # type: ignore[override]
        super().connect()
        peer = self.sock.getpeername()[0] if self.sock is not None else ""
        if not is_public_address(peer):
            self.close()
            raise UnsafeURL("connected peer is not a public address")


class _GuardedHTTPSConnection(_PeerCheckMixin, http.client.HTTPSConnection):
    pass


class _GuardedHTTPConnection(_PeerCheckMixin, http.client.HTTPConnection):
    pass


@dataclass
class SafeFetcher:
    allowed_hosts: tuple[str, ...] = ()
    allowed_content_types: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp", "application/octet-stream")
    max_bytes: int = 20 * 1024 * 1024
    timeout_seconds: float = 30.0
    max_redirects: int = 3
    allow_http: bool = False
    resolver: Callable = socket.getaddrinfo
    urlopen: Callable | None = None  # injected transport for tests; validation still applies
    _ctx: ssl.SSLContext = field(default_factory=ssl.create_default_context, repr=False)

    def validate(self, url: str) -> None:
        validate_public_url(url, allow_http=self.allow_http, allowed_hosts=self.allowed_hosts, resolver=self.resolver)

    def _opener(self):
        fetcher = self

        class _Redirects(request.HTTPRedirectHandler):
            max_redirections = fetcher.max_redirects

            def redirect_request(self, req, fp, code, msg, headers, newurl):
                fetcher.validate(newurl)  # every hop is re-validated
                new = super().redirect_request(req, fp, code, msg, headers, newurl)
                if new is not None and parse.urlsplit(newurl).netloc != parse.urlsplit(req.full_url).netloc:
                    new.remove_header("Authorization")  # never forward credentials to another host
                return new

        class _HTTPS(request.HTTPSHandler):
            def https_open(self, req):
                return self.do_open(_GuardedHTTPSConnection, req, context=fetcher._ctx)

        class _HTTP(request.HTTPHandler):
            def http_open(self, req):
                return self.do_open(_GuardedHTTPConnection, req)

        return request.build_opener(_Redirects, _HTTPS, _HTTP)

    def redirect_handler(self):
        """Exposed for tests: the handler that validates redirect targets."""
        return [h for h in self._opener().handlers if isinstance(h, request.HTTPRedirectHandler)][0]

    def get(self, url: str, *, headers: dict | None = None) -> tuple[bytes, str]:
        self.validate(url)
        req = request.Request(url, headers=dict(headers or {}), method="GET")
        opener = self.urlopen or self._opener().open
        with opener(req, timeout=self.timeout_seconds) as resp:
            final_url = getattr(resp, "url", None) or (resp.geturl() if hasattr(resp, "geturl") else url)
            if final_url and final_url != url:
                self.validate(final_url)
            resp_headers = getattr(resp, "headers", {}) or {}
            get = getattr(resp_headers, "get", lambda *_: None)
            length = get("Content-Length")
            if length and str(length).isdigit() and int(length) > self.max_bytes:
                raise UnsafeURL(f"response larger than {self.max_bytes} bytes")
            content_type = str(get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if content_type not in self.allowed_content_types:
                raise UnsafeURL(f"content type {content_type or '(missing)'} is not allowed")
            data = resp.read(self.max_bytes + 1)
        if len(data) > self.max_bytes:
            raise UnsafeURL(f"response larger than {self.max_bytes} bytes")
        if not data:
            raise UnsafeURL("empty response")
        return data, content_type
