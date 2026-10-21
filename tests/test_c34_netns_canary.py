"""C34, network level (Matt 2026-10-21): a SUBPROCESS that never touches the Python guard cannot get out either.

tools/netns_run.py runs a command in a network namespace with only loopback. Here a child is started through it, and
that child starts its own grandchild with `python -I -S` (no site, no omni_prod, no OMNI_TEST_HERMETIC, so nothing of
the in-process guard applies) which tries a raw connect and a DNS lookup. Both must fail loudly; loopback must work.

Where namespaces are unavailable the test SKIPS, unless OMNI_TEST_REQUIRE_NETNS=1 (CI), where it FAILS: CI never
claims isolation it does not have.
"""
import json
import os
import shutil
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'netns_run.py'

GRANDCHILD = textwrap.dedent(r'''
    import errno, json, socket, http.server, threading, urllib.request
    out = {}
    with open('/proc/net/dev') as fh:
        out['interfaces'] = sorted(l.split(':', 1)[0].strip() for l in fh.readlines()[2:] if ':' in l)
    for name, addr in (('raw_ip', ('1.1.1.1', 443)), ('test_net', ('203.0.113.10', 443))):
        s = socket.socket(); s.settimeout(3)
        code = s.connect_ex(addr); s.close()
        out[name] = errno.errorcode.get(code, str(code)) if code else 'CONNECTED'
    try:
        socket.getaddrinfo('api.replicate.com', 443)
        out['dns'] = 'RESOLVED'
    except OSError as exc:
        out['dns'] = type(exc).__name__
    srv = http.server.HTTPServer(('127.0.0.1', 0), http.server.BaseHTTPRequestHandler)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/', timeout=3)
    except urllib.error.HTTPError as exc:
        out['loopback'] = exc.code                     # 501 from BaseHTTPRequestHandler = the server answered
    except Exception as exc:
        out['loopback'] = type(exc).__name__
    out['guard_env'] = __import__('os').environ.get('OMNI_TEST_HERMETIC')
    print('GRANDCHILD ' + json.dumps(out))
''')

# the child, inside the namespace, launches the grandchild WITHOUT the hermetic variable and without site/omni_prod
CHILD = ('import os, subprocess, sys\n'
         'env = {k: v for k, v in os.environ.items() if not k.startswith("OMNI_TEST")}\n'
         'p = subprocess.run([sys.executable, "-I", "-S", "-c", sys.argv[1]], capture_output=True, text=True, env=env)\n'
         'print(p.stdout, end=""); print(p.stderr, end="", file=sys.stderr)\n')


def netns_available() -> bool:
    if not shutil.which('unshare'):
        return False
    flags = ['--net'] if os.geteuid() == 0 else ['--net', '--map-root-user']
    return subprocess.run(['unshare', *flags, 'true'], capture_output=True).returncode == 0


class C34NetworkNamespaceCanary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('OMNI_TEST_NETNS') == '1':
            # Already inside tools/netns_run.py (the CI suite runs there): the child is started right here, so the
            # proof is about THIS environment, the one the whole suite ran in.
            env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy')}
            p = subprocess.run([sys.executable, '-c', CHILD, GRANDCHILD], capture_output=True, text=True, timeout=120,
                               env=env)
            cls.stderr = None                      # no runner was started here: that check does not apply
            line = next((l for l in p.stdout.splitlines() if l.startswith('GRANDCHILD ')), None)
            assert line, f'no result: rc={p.returncode} {p.stdout[-1500:]} {p.stderr[-1500:]}'
            cls.out = json.loads(line[len('GRANDCHILD '):])
            return
        if not netns_available():
            if os.environ.get('OMNI_TEST_REQUIRE_NETNS') == '1':
                raise AssertionError('OMNI_TEST_REQUIRE_NETNS=1 but no network namespace can be created here')
            raise unittest.SkipTest('network namespaces are not available here')
        env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy')}
        p = subprocess.run([sys.executable, str(RUNNER), '--', sys.executable, '-c', CHILD, GRANDCHILD],
                           capture_output=True, text=True, timeout=120, env=env)
        cls.stderr = p.stderr
        line = next((l for l in p.stdout.splitlines() if l.startswith('GRANDCHILD ')), None)
        assert line, f'no result: rc={p.returncode} {p.stdout[-1500:]} {p.stderr[-1500:]}'
        cls.out = json.loads(line[len('GRANDCHILD '):])

    def test_the_subprocess_is_outside_the_python_guard(self):
        self.assertIsNone(self.out['guard_env'])          # proves the guard plays no part in what follows

    def test_only_loopback_exists(self):
        self.assertEqual(self.out['interfaces'], ['lo'])

    def test_a_raw_connect_fails_loudly(self):
        self.assertEqual(self.out['raw_ip'], 'ENETUNREACH')
        self.assertEqual(self.out['test_net'], 'ENETUNREACH')

    def test_a_name_lookup_fails(self):
        self.assertNotEqual(self.out['dns'], 'RESOLVED')

    def test_loopback_still_works(self):
        self.assertEqual(self.out['loopback'], 501)

    def test_the_runner_says_it_is_isolated(self):
        if self.stderr is None:
            self.skipTest('the suite itself runs inside netns_run; its banner is in the CI log')
        self.assertIn("netns_run: isolated (interfaces ['lo']", self.stderr)


class NetnsRunnerFailsClosed(unittest.TestCase):
    def test_without_a_command_it_runs_nothing(self):
        p = subprocess.run([sys.executable, str(RUNNER)], capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 3)
        self.assertIn('FAIL CLOSED', p.stderr)

    def test_inside_a_namespace_that_still_has_a_route_it_refuses(self):
        # Simulate "inside" without a namespace: the host has more than loopback, so verify_isolated must refuse.
        if os.environ.get('OMNI_TEST_NETNS') == '1':
            self.skipTest('already inside an isolated namespace: there is no route here to be refused')
        env = dict(os.environ, OMNI_TEST_NETNS_INSIDE='1')
        p = subprocess.run([sys.executable, str(RUNNER), '--', 'true'], capture_output=True, text=True, timeout=30,
                           env=env)
        if 'interfaces [' not in p.stderr and p.returncode == 0:
            self.fail('ran the command although the process was not isolated')
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn('FAIL CLOSED', p.stderr)


if __name__ == '__main__':
    unittest.main()
