"""The generator gets the design contract AS WRITTEN (rehearsal 44043708644, the butcher, 2026-11-17: the contract
was only in the prompt; the architect rewrote it; the generator never saw it and the page failed CONTRACT_MISSING).

The real autonomous_core loop runs here with the real install: what the generator receives is what is asserted."""
import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from omni_prod import g_apple as A
from omni_prod import rehearsal
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.g_apple import contract as C
from omni_prod.product_spec import ProductSpec

CAFE = ('אתר לבית קפה שכונתי בתל אביב בשם קפה נחמה: תפריט עם מחירים, הסיפור שלנו, שעות פתיחה 07:00 עד 19:00, '
        'טלפון 03-5551234, כתובת אבן גבירול 100 תל אביב')
PROMPT = rehearsal.approved_prompt(CAFE, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
CONTRACT = C.build(PROMPT)
SPEC = ProductSpec.from_dict({
    'title': 'קפה נחמה', 'summary': 'אתר לבית קפה', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'דף הבית מציג את שם בית הקפה', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'GET / returns 200 with the name'}]})


class Architect:
    """An architect that, like the real one, writes the spec in its own words: nothing of the prompt survives."""
    def __init__(self):
        self.prompts = []

    def create_spec(self, prompt):
        self.prompts.append(prompt)
        return SPEC


class Generator:
    def __init__(self):
        self.specs = []

    def generate(self, spec):
        self.specs.append(spec)
        from omni_prod.repository_patch import FilePatch
        return (FilePatch('app.py', 'x = 1\n'),)


class Executor:
    last_shots = {}

    def execute(self, *, repository, spec):
        return ExecutionReport(False, (), 'stopped here: this test is about what the generator was given')


def install(engine):
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('OMNI_GATE_APPLE', None)
        return A.install(engine, prompt=PROMPT)


class TheGeneratorGetsTheContractAsWritten(unittest.TestCase):
    def test_through_the_real_build_loop(self):
        architect, generator = Architect(), Generator()
        engine = AutonomousProductEngine(architect=architect, generator=generator, executor=Executor(), repairer=None,
                                         max_repair_rounds=0)
        prompt = install(engine)
        engine.build(prompt)
        given = generator.specs[0]
        carried = [r for r in given.requirements if r.id == A.CONTRACT_REQUIREMENT]
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0].text, C.rules(CONTRACT))                  # word for word
        self.assertIn(CONTRACT['css'], json.dumps(given.to_dict(), ensure_ascii=False).replace('\\n', '\n'))
        self.assertTrue(carried[0].mandatory)
        self.assertEqual([r.id for r in given.requirements][0], 'R1')         # the architect's own spec is kept
        self.assertTrue(A.report(engine)['carried'])

    def test_the_mandatory_requirement_has_a_criterion_a_sandbox_test_can_check(self):
        spec = A.with_contract(SPEC, CONTRACT)
        criterion = [a for a in spec.acceptance if a.requirement_id == A.CONTRACT_REQUIREMENT]
        self.assertEqual(len(criterion), 1)
        self.assertIn(f"--color-primary: {CONTRACT['tokens']['--color-primary']}", criterion[0].text)
        self.assertIn(f"--color-primary: {CONTRACT['tokens']['--color-primary']}", CONTRACT['css'])
        self.assertIn('GET / returns 200', criterion[0].text)

    def test_it_is_added_once(self):
        once = A.with_contract(SPEC, CONTRACT)
        self.assertIs(A.with_contract(once, CONTRACT), once)
        engine = SimpleNamespace(executor=Executor(), architect=Architect())
        install(engine)
        install(engine)
        self.assertIsInstance(engine.architect, A.ContractArchitect)
        self.assertNotIsInstance(engine.architect._inner, A.ContractArchitect)

    def test_an_engine_with_no_architect_is_said_not_assumed(self):
        engine = SimpleNamespace(executor=Executor())
        with self.assertLogs(A.__name__, 'WARNING') as logs:
            install(engine)
        self.assertIn('APPLE_CONTRACT_NOT_CARRIED', logs.output[0])
        self.assertIs(A.report(engine)['carried'], False)

    def test_without_a_contract_the_spec_is_untouched(self):
        architect = Architect()
        engine = SimpleNamespace(executor=Executor(), architect=architect)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_APPLE', None)
            A.install(engine, prompt=CAFE)                                    # a raw request: no Design line
        self.assertIs(engine.architect, architect)
        with mock.patch.dict(os.environ, {'OMNI_GATE_APPLE': 'off'}), self.assertLogs(A.__name__, 'WARNING'):
            A.install(engine, prompt=PROMPT)
        self.assertIs(engine.architect, architect)

    def test_the_generator_is_told_to_leave_no_browser_default_margin(self):
        """The same rehearsal: 24 OFF_GRID findings on headings and links nobody had styled."""
        rules = C.rules(CONTRACT)
        self.assertIn('margin: 0 and padding: 0 on h1, h2, h3, h4, p, ul, ol, li and figure', rules)
        self.assertIn('a browser default margin is not on the grid', rules)


class TheReviewersKnowWhatTheyAreShown(unittest.TestCase):
    def test_both_are_told_the_screenshots_are_the_first_screen_only(self):
        """The same rehearsal: a section below the first screen was reported as missing from the page."""
        from omni_prod.g_apple import reviewers as V
        self.assertEqual(set(V.SYSTEM), {'typography_layout', 'brand_category'})
        for name, text in V.SYSTEM.items():
            self.assertIn('ONLY the first screen', text, name)
            self.assertIn('Never report content as missing because it is not in a screenshot', text, name)
            self.assertIn('Answer ONE JSON object', text, name)               # the answer shape is still asked for


if __name__ == '__main__':
    unittest.main()
