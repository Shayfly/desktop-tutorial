#!/usr/bin/env python3
"""Run a command with NO network at the operating-system level (C34, owner + Matt 2026-10-21).

    python3 tools/netns_run.py -- python -m unittest discover -s tests

The command runs in a fresh Linux network namespace (`unshare --net`) that has only a loopback interface, brought up
here. Every process inside, including subprocesses that never import omni_prod (curl, a shell, `python -I`), has no
route out: a connect fails at once with ENETUNREACH and a name lookup fails. That is the network-level block; the
Python guard (omni_prod/hermetic.py, OMNI_TEST_HERMETIC=1, set here too) only adds a loud HermeticViolation for
in-process code.

Fail closed: if a namespace cannot be created, or the namespace still has an interface other than loopback, or a
connect to a non-loopback address does not fail, this exits 3 and runs nothing. There is no fallback to "unisolated".
Install dependencies BEFORE calling this (there is no network inside).
"""
from __future__ import annotations

import errno
import fcntl
import os
import shutil
import socket
import struct
import subprocess
import sys

INSIDE = 'OMNI_TEST_NETNS_INSIDE'
PROBE_ADDR = ('203.0.113.10', 443)      # TEST-NET-3: never routable, used only to prove there is no route at all


def die(msg: str) -> None:
    print(f'netns_run: FAIL CLOSED: {msg}', file=sys.stderr, flush=True)
    sys.exit(3)


def interfaces() -> list[str]:
    with open('/proc/net/dev', encoding='utf-8') as fh:
        return sorted(line.split(':', 1)[0].strip() for line in fh.readlines()[2:] if ':' in line)


def loopback_up() -> None:
    siocgifflags, siocsifflags, iff_up = 0x8913, 0x8914, 0x1
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        flags = struct.unpack('16sH', fcntl.ioctl(s, siocgifflags, struct.pack('16sH', b'lo', 0)))[1]
        fcntl.ioctl(s, siocsifflags, struct.pack('16sH', b'lo', flags | iff_up))
    finally:
        s.close()


def verify_isolated() -> None:
    names = interfaces()
    if names != ['lo']:
        die(f'the namespace has interfaces {names}, expected only lo')
    s = socket.socket()
    s.settimeout(2)
    try:
        code = s.connect_ex(PROBE_ADDR)
    finally:
        s.close()
    if code != errno.ENETUNREACH:
        die(f'connect to {PROBE_ADDR} returned {code} ({errno.errorcode.get(code, "?")}), expected ENETUNREACH')


def main(argv: list[str]) -> int:
    if '--' not in argv:
        die('usage: netns_run.py -- <command ...>')
    cmd = argv[argv.index('--') + 1:]
    if not cmd:
        die('no command')
    if os.environ.get(INSIDE) == '1':
        loopback_up()
        verify_isolated()
        env = {k: v for k, v in os.environ.items() if k != INSIDE and k.lower() not in (
            'http_proxy', 'https_proxy', 'all_proxy')}
        env.update({'OMNI_TEST_HERMETIC': '1', 'OMNI_TEST_NETNS': '1'})
        print(f'netns_run: isolated (interfaces {interfaces()}; {PROBE_ADDR[0]} unreachable); running {cmd[0]}',
              file=sys.stderr, flush=True)
        os.execvpe(cmd[0], cmd, env)
    unshare = shutil.which('unshare')
    if not unshare:
        die('unshare is not installed')
    flags = ['--net'] if os.geteuid() == 0 else ['--net', '--map-root-user']
    env = dict(os.environ, **{INSIDE: '1'})
    try:
        return subprocess.call([unshare, *flags, sys.executable, os.path.abspath(__file__), '--', *cmd], env=env)
    except OSError as exc:
        die(f'unshare failed: {exc}')
    return 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
