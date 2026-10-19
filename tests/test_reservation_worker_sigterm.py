"""intake-maintain exits promptly and cleanly on SIGTERM (2026-10-19).

Before: `python -m omni_prod.intake.reservation_worker maintain --loop 10` ran `while True: ...; time.sleep()` with no
handler. As PID 1 in its container the default SIGTERM action does not apply, so `docker compose stop -t 1500` waited the
full deadline and SIGKILLed it (exit 137) -- deploy-worker run 39218374150. The handler makes the exit graceful even
without `init: true`: the loop finishes its current pass and returns 0. Exit code 0 (not -15) proves the handler ran.
No DB, no Redis, no network: the pool and the reservation service are fakes."""
import os
import signal
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXIT_WITHIN_SECONDS = 5

CHILD = textwrap.dedent('''
    import sys, time, types
    db = types.ModuleType('omni_prod.db')
    class DatabasePool:
        def __init__(self, url): pass
        def close(self): print('pool closed', flush=True)
    db.DatabasePool = DatabasePool
    sys.modules['omni_prod.db'] = db
    from omni_prod.intake import budget, reservation_worker
    PASS_SECONDS = float(sys.argv[1])
    class Svc:
        def __init__(self, pool): pass
        def relay_once(self, enqueue):
            print('pass start', flush=True); time.sleep(PASS_SECONDS); return 0
        def reconcile(self):
            print('pass done', flush=True); return 0
    budget.ReservationService = Svc
    raise SystemExit(reservation_worker.relay_main(['maintain', '--loop', '600']))
''')


class SigtermTests(unittest.TestCase):
    def _start(self, pass_seconds):
        env = {**os.environ, 'OMNI_DATABASE_URL': 'postgresql://fake/db', 'OMNI_REDIS_URL': 'redis://fake:6379/0',
               'PYTHONPATH': str(ROOT)}
        p = subprocess.Popen([sys.executable, '-c', CHILD, str(pass_seconds)], cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: p.poll() is None and p.kill())
        return p

    def _stop(self, p):
        t0 = time.monotonic()
        p.send_signal(signal.SIGTERM)
        out, err = p.communicate(timeout=EXIT_WITHIN_SECONDS + 5)
        return time.monotonic() - t0, out, err

    def test_sigterm_during_the_sleep_exits_0_within_seconds(self):
        p = self._start(0)
        self.assertEqual(p.stdout.readline().strip(), 'pass start')
        self.assertEqual(p.stdout.readline().strip(), 'pass done')        # first pass finished
        self.assertTrue(p.stdout.readline().startswith('intake maintain:'))   # now in the 600 s wait
        elapsed, out, err = self._stop(p)
        self.assertEqual(p.returncode, 0, err)
        self.assertLess(elapsed, EXIT_WITHIN_SECONDS)
        self.assertIn('stop signal received, exiting', out)
        self.assertIn('pool closed', out)

    def test_sigterm_mid_pass_lets_the_pass_finish_then_exits_0(self):
        p = self._start(1.5)
        self.assertEqual(p.stdout.readline().strip(), 'pass start')       # inside relay_once
        elapsed, out, err = self._stop(p)
        self.assertEqual(p.returncode, 0, err)
        self.assertLess(elapsed, EXIT_WITHIN_SECONDS)
        self.assertEqual(out.splitlines()[0], 'pass done')                 # never cut in the middle
        self.assertIn('intake maintain:', out)


if __name__ == '__main__':
    unittest.main()
