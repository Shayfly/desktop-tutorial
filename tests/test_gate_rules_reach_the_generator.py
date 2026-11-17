"""The generator is told what the installed gates check (rehearsal 44043708644, the butcher, 2026-11-17: the share
gate failed a page for a missing og:title and nothing had told the generator a shared link needs one).

The text is each unit's own manifest description -- one source, nothing written twice. The real build loop runs."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import FilePatch
from omni_prod.skill_units import gate as G, manifest

SPEC = ProductSpec.from_dict({
    'title': 'קפה נחמה', 'summary': 'אתר לבית קפה', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'דף הבית מציג את שם בית הקפה', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'GET / returns 200 with the name'}]})


class Architect:
    def create_spec(self, prompt):
        return SPEC


class Generator:
    def __init__(self):
        self.specs = []

    def generate(self, spec):
        self.specs.append(spec)
        return (FilePatch('app.py', 'x = 1\n'),)


class Executor:
    def execute(self, *, repository, spec):
        return ExecutionReport(False, (), 'stopped here: this test is about what the generator was given')


def clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('OMNI_GATE_')}
    return mock.patch.dict(os.environ, env, clear=True)


class TheGeneratorIsToldTheChecks(unittest.TestCase):
    def test_through_the_real_build_loop_every_installed_unit_is_named_as_its_manifest_says(self):
        generator = Generator()
        engine = AutonomousProductEngine(architect=Architect(), generator=generator, executor=Executor(),
                                         repairer=None, max_repair_rounds=0)
        with clean_env():
            G.install_all(engine)
            engine.build('אתר לבית קפה')
        given = generator.specs[0]
        rules = [r for r in given.requirements if r.id == G.RULES_REQUIREMENT]
        self.assertEqual(len(rules), 1)
        self.assertEqual((rules[0].kind, rules[0].mandatory), ('quality', False))
        units = [u for g in G.WORKER_GATES for u in G.gate_units(g)]
        self.assertGreaterEqual(len(units), 30)
        for unit in units:
            self.assertIn('- ' + manifest(unit)['description'], rules[0].text, unit)
        self.assertEqual(rules[0].text.count('\n- '), len(units))               # nothing else, nothing twice
        self.assertIn('og:title', rules[0].text)                                # the check the butcher's page failed
        self.assertEqual([r.id for r in given.requirements][0], 'R1')           # the architect's own spec is kept
        self.assertEqual(len(given.acceptance), 1)                              # no criterion added
        self.assertTrue(engine.gate_rules_carried)

    def test_a_gate_that_is_off_is_left_out(self):
        with clean_env(), mock.patch.dict(os.environ, {'OMNI_GATE_SHARE': 'off'}):
            text = G.rules_text(G.WORKER_GATES)
        self.assertNotIn('og:title', text)
        self.assertIn(manifest(G.gate_units('G3')[0])['description'], text)
        with clean_env(), mock.patch.dict(os.environ, {f'OMNI_GATE_{g}': 'off' for g in G.WORKER_GATES}):
            self.assertEqual(G.rules_text(G.WORKER_GATES), '')
            self.assertIs(G.with_rules(SPEC, G.rules_text(G.WORKER_GATES)), SPEC)

    def test_it_is_added_once(self):
        with clean_env():
            once = G.with_rules(SPEC, G.rules_text(G.WORKER_GATES))
            self.assertIs(G.with_rules(once, G.rules_text(G.WORKER_GATES)), once)
            engine = SimpleNamespace(executor=Executor(), architect=Architect())
            G.install_all(engine)
            G.carry_rules(engine, G.WORKER_GATES)
        self.assertNotIsInstance(engine.architect._inner, G.GateRulesArchitect)

    def test_an_engine_with_no_architect_is_said(self):
        engine = SimpleNamespace(executor=Executor())
        with clean_env(), self.assertLogs(G.__name__, 'INFO') as logs:
            self.assertIs(G.carry_rules(engine, G.WORKER_GATES), False)
        self.assertIn('GATE_RULES carried=False', logs.output[-1])
        self.assertIs(engine.gate_rules_carried, False)


if __name__ == '__main__':
    unittest.main()
