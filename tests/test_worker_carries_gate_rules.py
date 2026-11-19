"""The worker -- not only the rehearsal -- tells the generator what the installed gates check.

#430 (2026-11-17) put the gates' checks into the spec, but only `install_all` carried them, and only the rehearsal
calls `install_all`; the worker installs each gate on its own line. Production since then (SELECT on
project_version_specs, 2026-11-19): 0 of the 5 stored specs carry PLATFORM-CHECKS, and SHARE failed all five builds
for a missing og:title / og:description -- a check the generator was never told about. Claude's bug (#430).

The real worker job runs (`_run_live_build_job`, the BuildHarness); the engine's build asks the architect the worker
left on it for the spec, as the core's _build does.
"""
import inspect
import os
import unittest
from unittest import mock

from omni_prod import worker_tasks
from omni_prod.skill_units import gate as G
from tests.test_gate_rules_reach_the_generator import SPEC, Architect
from tests.test_m3_preview_logic import BuildHarness


def clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('OMNI_GATE_')}
    return mock.patch.dict(os.environ, env, clear=True)


def worker_spec():
    """Run the real worker job; return the spec the engine's architect gave when the build started."""
    h = BuildHarness()
    h.engine.architect = Architect()
    h.engine.core.architect = Architect()
    given = []

    def build(prompt):
        given.append(h.engine.core.architect.create_spec(prompt))
        return h.result
    h.engine.build.side_effect = build
    with clean_env():
        status = h.run()
    return status, given, h.engine


class TheWorkerCarriesTheRules(unittest.TestCase):
    def test_the_spec_a_worker_build_starts_from_names_the_share_check(self):
        status, given, engine = worker_spec()
        self.assertEqual(status, 'ready')
        self.assertEqual(len(given), 1)
        rules = [r for r in given[0].requirements if r.id == G.RULES_REQUIREMENT]
        self.assertEqual(len(rules), 1, 'the worker build started from a spec with no platform checks')
        self.assertIn('og:title', rules[0].text)                                # the check SHARE failed 5 of 5 on
        self.assertEqual([r.id for r in given[0].requirements][0], 'R1')         # the architect's own spec is kept
        self.assertIs(engine.core.gate_rules_carried, True)

    def test_every_gate_the_worker_installs_is_in_the_rules(self):
        _, given, engine = worker_spec()
        text = [r for r in given[0].requirements if r.id == G.RULES_REQUIREMENT][0].text
        self.assertLessEqual(set(G.WORKER_GATES), set(engine.core.gate_modes))   # G8, A4, APPLE are not skill units
        for g in G.WORKER_GATES:
            for unit in G.gate_units(g):
                self.assertIn(G.manifest(unit)['description'], text, unit)

    def test_the_rules_are_carried_after_the_last_gate_and_before_the_build(self):
        src = inspect.getsource(worker_tasks._run_live_build_job)
        carry = src.index('carry_rules(engine, WORKER_GATES)')
        self.assertLess(src.index("install_skill_gate(engine, 'G5')"), carry)
        self.assertLess(carry, src.index('result = engine.build(build_prompt)'))


if __name__ == '__main__':
    unittest.main()
