"""intake-maintain exits promptly and cleanly on SIGTERM (2026-10-19).

Before: `python -m omni_prod.intake.reservation_worker maintain --loop 10` ran `while True: ...; time.sleep()` with no
handler. As PID 1 in its container the default SIGTERM action does not apply, so `docker compose stop -t 1500` waited the
full deadline and SIGKILLed it (exit 137) -- deploy-worker run 39218374150. The handler makes the exit graceful even
without `init: true`: the loop finishes its current pass and returns 0. Exit code 0 (not -15) proves the handler ran.
No DB, no Redis, no network: the pool and the reservation service are fakes."""
import os
import signal
import selectors
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Scheduling allowance for loaded CI hosts; still far below the 600 s loop.
EXIT_WITHIN_SECONDS = 30
READ_WITHIN_SECONDS = 30

CHILD = textwrap.dedent('''
    import sys, signal, types
    # Observe the real handler, without replacing its behavior. The parent waits
    # for delivery before releasing the mid-pass barrier: no timed sleeps/races.
    register_signal = signal.signal
    def observe_signal(signum, handler):
        def observed(sig, frame):
            handler(sig, frame)
            print('signal handled', flush=True)
        return register_signal(signum, observed)
    signal.signal = observe_signal
    db = types.ModuleType('omni_prod.db')
    class DatabasePool:
        def __init__(self, url): pass
        def close(self): print('pool closed', flush=True)
    db.DatabasePool = DatabasePool
    sys.modules['omni_prod.db'] = db
    from omni_prod.intake import budget, reservation_worker
    HOLD_PASS = sys.argv[1] == 'hold'
    class Svc:
        def __init__(self, pool): pass
        def relay_once(self, enqueue):
            print('pass start', flush=True)
            if HOLD_PASS:
                assert sys.stdin.readline().strip() == 'release'
            return 0
        def reconcile(self):
            print('pass done', flush=True); return 0
    budget.ReservationService = Svc
    raise SystemExit(reservation_worker.relay_main(['maintain', '--loop', '600']))
''')


class SigtermTests(unittest.TestCase):
    def _start(self, phase):
        env = {**os.environ, 'OMNI_DATABASE_URL': 'postgresql://fake/db', 'OMNI_REDIS_URL': 'redis://fake:6379/0',
               'PYTHONPATH': str(ROOT)}
        p = subprocess.Popen([sys.executable, '-c', CHILD, phase], cwd=ROOT, env=env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        def cleanup():
            if p.poll() is None:
                p.kill()
            p.communicate()
        self.addCleanup(cleanup)
        return p

    def _line(self, p):
        # Unbuffered binary reads keep readiness checks honest, with a deadline
        # even if startup/phase signalling regresses. No unbounded readline.
        deadline, line = time.monotonic() + READ_WITHIN_SECONDS, bytearray()
        with selectors.DefaultSelector() as ready:
            ready.register(p.stdout, selectors.EVENT_READ)
            while not line.endswith(b'\n'):
                remaining = deadline - time.monotonic()
                self.assertTrue(remaining > 0 and ready.select(remaining), 'child phase marker timed out')
                chunk = os.read(p.stdout.fileno(), 1)
                self.assertTrue(chunk, 'child exited before its phase marker')
                line.extend(chunk)
        return line.decode().strip()

    def _stop(self, p, *, release_pass=False):
        t0 = time.monotonic()
        p.send_signal(signal.SIGTERM)
        self.assertEqual(self._line(p), 'signal handled')
        if release_pass:
            p.stdin.write(b'release\n')
            p.stdin.flush()
        out, err = p.communicate(timeout=EXIT_WITHIN_SECONDS + 5)
        return time.monotonic() - t0, out.decode(), err.decode()

    def test_sigterm_during_the_sleep_exits_0_within_seconds(self):
        p = self._start('sleep')
        self.assertEqual(self._line(p), 'pass start')
        self.assertEqual(self._line(p), 'pass done')        # first pass finished
        self.assertTrue(self._line(p).startswith('intake maintain:'))   # now in the 600 s wait
        elapsed, out, err = self._stop(p)
        self.assertEqual(p.returncode, 0, err)
        self.assertLess(elapsed, EXIT_WITHIN_SECONDS)
        self.assertIn('stop signal received, exiting', out)
        self.assertIn('pool closed', out)

    def test_sigterm_mid_pass_lets_the_pass_finish_then_exits_0(self):
        p = self._start('hold')
        self.assertEqual(self._line(p), 'pass start')       # inside relay_once
        elapsed, out, err = self._stop(p, release_pass=True)
        self.assertEqual(p.returncode, 0, err)
        self.assertLess(elapsed, EXIT_WITHIN_SECONDS)
        self.assertEqual(out.splitlines()[0], 'pass done')                 # never cut in the middle
        self.assertIn('intake maintain:', out)


if __name__ == '__main__':
    unittest.main()
