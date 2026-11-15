"""#378 (Michael 2026-11-15: a port collision is an environment bug, not a habit). The gate-regression test that
starts a real product used a fixed port (8765); two suites on one host made it fail. Each run now takes a port the OS
says is free (bind to port 0). This file holds the helper and the test that two runs at once do not collide."""
import socket
import unittest
from concurrent.futures import ThreadPoolExecutor


def free_port() -> int:
    """A port the OS says is free right now (bind to port 0), instead of a fixed number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TwoRunsAtOnce(unittest.TestCase):
    def test_two_runs_at_once_do_not_collide(self):
        from omni_prod.gate_regression import run
        from tests.test_frozen_run_conditions_20261110 import GateRegressionTool
        from tests.test_gate_mutations_20261110 import REQUEST
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(GateRegressionTool.product(free_port()), REQUEST), range(2)))
        self.assertEqual([r['served'] for r in results], [True, True], [r['smoke'] for r in results])


if __name__ == '__main__':
    unittest.main()
