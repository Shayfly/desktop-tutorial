"""Hermetic mode, SOCKET LEVEL (owner 2026-10-21; scope corrected after Matt's review): OMNI_TEST_HERMETIC=1 makes
this Python process refuse outbound connections and name lookups, loudly (HermeticViolation).

What it is NOT: an operating-system block. A subprocess that does not import omni_prod (curl, a shell, `python -I`) is
not covered by it. The network-level block is tools/netns_run.py (a network namespace with only loopback), which CI
uses for the unit tests and which also sets this variable; this module adds the loud in-process error on top.

Not a "mocked provider": in-process code cannot reach the network, except loopback and Unix sockets (local test
servers, the CI Postgres/Redis on 127.0.0.1) and the hosts named in OMNI_TEST_HERMETIC_ALLOW (comma separated, e.g. the
compose service names `postgres,redis`). Proxy variables are removed: a loopback proxy
would otherwise tunnel out. Installed from omni_prod/__init__.py, so it covers every process that imports
the package when the variable is set: the test runner AND a worker started with it (`OMNI_TEST_HERMETIC=1 python -m
omni_prod.worker`). Off (no effect at all) unless the variable is exactly "1".

Name lookups of other hosts are refused too (no DNS query leaves). Every refused attempt is recorded in ATTEMPTS (host, port) and raised as HermeticViolation (a ConnectionRefusedError, so
callers see an ordinary connection failure, never a success). C34 is the canary: it tries to reach a provider and proves
nothing left the process.
"""
from __future__ import annotations

import ipaddress
import os
import socket

ENV = 'OMNI_TEST_HERMETIC'
ALLOW_ENV = 'OMNI_TEST_HERMETIC_ALLOW'
ATTEMPTS: list[tuple[str, object]] = []
_INSTALLED = '_omni_hermetic'
PROXY_VARS = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')


class HermeticViolation(ConnectionRefusedError):
    """An outbound connection was attempted in hermetic mode and refused before it left the process."""


def enabled(env=None) -> bool:
    return (os.environ if env is None else env).get(ENV) == '1'


def _allowed_names() -> set[str]:
    raw = os.environ.get(ALLOW_ENV, '')
    return {'localhost'} | {h.strip().lower() for h in raw.split(',') if h.strip()}


def _local(host) -> bool:
    if host is None:
        return False
    if isinstance(host, (bytes, bytearray)):
        host = host.decode(errors='replace')
    host = str(host).strip('[]').lower()
    if host in _allowed_names():
        return True
    try:
        return ipaddress.ip_address(host.split('%', 1)[0]).is_loopback
    except ValueError:
        return False


def _check(sock, address) -> None:
    if sock.family == getattr(socket, 'AF_UNIX', object()):
        return
    host, port = (address[0], address[1]) if isinstance(address, tuple) and len(address) >= 2 else (address, None)
    if not _local(host):
        ATTEMPTS.append((str(host), port))
        raise HermeticViolation(f'{ENV}=1: outbound connection to {host}:{port} refused (no network in hermetic tests)')


def install() -> bool:
    """Idempotent. Returns True when the guard is (now) active."""
    if not enabled():
        return False
    if getattr(socket.socket, _INSTALLED, False):
        return True
    # A proxy on loopback is still a way out: urllib/requests would tunnel through it. Hermetic means no proxy.
    for name in PROXY_VARS:
        os.environ.pop(name, None)
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def connect(self, address):
        _check(self, address)
        return original_connect(self, address)

    def connect_ex(self, address):
        _check(self, address)
        return original_connect_ex(self, address)

    original_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, *args, **kwargs):          # no DNS query leaves the process either
        if not _local(host) and host is not None:
            ATTEMPTS.append((str(host), args[0] if args else kwargs.get('port')))
            raise HermeticViolation(f'{ENV}=1: name lookup of {host} refused (no network in hermetic tests)')
        return original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
    socket.getaddrinfo = getaddrinfo
    setattr(socket.socket, _INSTALLED, True)
    return True
