"""C34 (owner 2026-10-21): hermetic tests. A test tries to reach a provider and proves nothing left the process.

Each case runs in a fresh child process with OMNI_TEST_HERMETIC=1. Before omni_prod is imported, the child replaces the
REAL socket connect and getaddrinfo with recorders that never touch the network: so even if the hermetic guard were
broken, this test makes no real request; it would only see the recorder called and go red.
"""
import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHILD = textwrap.dedent(r'''
    import json, socket, sys
    case = sys.argv[1]
    LEFT = []                                         # anything that reached the "real" network layer
    if case != 'loopback':                            # recorders instead of the real network: no egress even if broken
        def fake_connect(self, address):
            LEFT.append(['connect', str(address)]); raise OSError('recorder: would have left the process')
        def fake_getaddrinfo(host, *a, **k):
            LEFT.append(['dns', str(host)]); raise socket.gaierror('recorder: would have resolved')
        socket.socket.connect = fake_connect
        socket.socket.connect_ex = lambda self, address: (fake_connect(self, address), 1)[1]
        socket.getaddrinfo = fake_getaddrinfo
    import omni_prod                                    # installs the hermetic guard (OMNI_TEST_HERMETIC=1)
    from omni_prod import hermetic
    out = {'installed': getattr(socket.socket, '_omni_hermetic', False)}
    if case == 'provider':
        from omni_prod.providers.replicate_connection import check_replicate_connection
        out['result'] = check_replicate_connection({'REPLICATE_API_TOKEN': 'r8_' + 'a' * 37})['status']
        from urllib import request, error
        try:
            request.urlopen('https://api.openai.com/v1/models', timeout=5)
            out['urlopen'] = 'returned'
        except error.URLError as exc:
            out['urlopen'] = type(exc.reason).__name__
        try:                                            # a literal IP needs no DNS: only the connect guard stops it
            raw = socket.socket(); raw.settimeout(5)
            raw.connect(('203.0.113.10', 443))           # TEST-NET-3, never routable anyway; no getaddrinfo call
            out['raw_ip'] = 'connected'
        except OSError as exc:
            out['raw_ip'] = type(exc).__name__
    elif case == 'loopback':                            # hermetic is not "fail everything": loopback still works
        import http.server, threading
        from urllib import request
        srv = http.server.HTTPServer(('127.0.0.1', 0), http.server.SimpleHTTPRequestHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out['loopback_status'] = request.urlopen(f'http://127.0.0.1:{srv.server_port}/', timeout=5).status
        srv.shutdown()
    out['attempts'] = [[str(h), p] for h, p in hermetic.ATTEMPTS]
    out['left'] = LEFT
    print('C34 ' + json.dumps(out))
''')


def run(case, *, hermetic='1'):
    env = {k: v for k, v in os.environ.items() if not k.startswith('OMNI_TEST_HERMETIC')}
    env.update({'OMNI_TEST_HERMETIC': hermetic, 'PYTHONPATH': str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')})
    p = subprocess.run([sys.executable, '-c', CHILD, case], capture_output=True, text=True, timeout=120, env=env, cwd=ROOT)
    line = next((l for l in p.stdout.splitlines() if l.startswith('C34 ')), None)
    assert line, f'child failed: {p.stdout[-2000:]} {p.stderr[-2000:]}'
    return json.loads(line[4:])


class C34HermeticCanary(unittest.TestCase):
    def test_a_provider_call_never_leaves_the_process(self):
        out = run('provider')
        self.assertTrue(out['installed'])
        self.assertEqual(out['left'], [])                                         # nothing reached the network layer
        self.assertIn('api.replicate.com', [h for h, _ in out['attempts']])     # it DID try, and was refused
        self.assertIn('api.openai.com', [h for h, _ in out['attempts']])
        self.assertEqual(out['result'], 'BLOCKED')                               # a refused call is never a success
        self.assertEqual(out['urlopen'], 'HermeticViolation')
        self.assertEqual(out['raw_ip'], 'HermeticViolation')
        self.assertIn('203.0.113.10', [h for h, _ in out['attempts']])

    def test_loopback_still_works(self):
        out = run('loopback')
        self.assertEqual(out['loopback_status'], 200)
        self.assertEqual(out['attempts'], [])

    def test_off_unless_exactly_1(self):
        out = run('provider', hermetic='0')
        self.assertFalse(out['installed'])
        self.assertTrue(out['left'])                    # without the guard the recorder sees the attempt (no real egress)

    def test_a_hermetic_worker_cannot_reach_its_queue_host(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('OMNI_TEST_HERMETIC')}
        env.update({'OMNI_TEST_HERMETIC': '1', 'OMNI_REDIS_URL': 'redis://queue.example.invalid:6379/0',
                    'PYTHONPATH': str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')})
        code = ('import omni_prod, socket\n'
                'from omni_prod import hermetic\n'
                'try:\n'
                '    from omni_prod.worker import main; main()\n'
                'except BaseException as exc:\n'
                '    print("WORKER", type(exc).__name__, str(exc)[:200], [h for h, _ in hermetic.ATTEMPTS])\n')
        p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=120, env=env, cwd=ROOT)
        if "No module named 'redis'" in p.stdout + p.stderr or "No module named 'rq'" in p.stdout + p.stderr:
            self.skipTest('redis client not installed here')
        self.assertIn('queue.example.invalid', p.stdout, p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
