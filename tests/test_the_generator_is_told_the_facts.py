"""The generator is told the customer's facts before it writes (2026-11-17: three calibration builds of four paid a
repair round for "facts the customer gave are missing from the page: address ..."; the review checked a canon the
generator had never seen). The real build loop runs; the request is the butcher calibration request."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import fact_canon as F
from omni_prod import rehearsal as R
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import FilePatch

ROOT = Path(__file__).resolve().parent.parent
BUTCHER = ('אתר תדמית בעברית לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456. שעות פתיחה: ראשון עד חמישי '
           '8:00 עד 19:00, שישי 7:00 עד 14:00. בלי התחברות משתמשים ובלי הזמנות אונליין.')
PROMPT = R.approved_prompt(BUTCHER, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
SPEC = ProductSpec.from_dict({
    'title': 'בשר השכונה', 'summary': 'אתר לאטליז', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'דף הבית', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'GET / returns 200'}]})


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
        return ExecutionReport(False, (), 'stopped: this test is about what the generator was given')


class TheFactsReachTheGenerator(unittest.TestCase):
    def test_through_the_real_build_loop(self):
        generator = Generator()
        engine = AutonomousProductEngine(architect=Architect(), generator=generator, executor=Executor(),
                                         repairer=None, max_repair_rounds=0)
        facts = F.install_facts(engine, PROMPT)
        engine.build(PROMPT)
        given = generator.specs[0]
        req = [r for r in given.requirements if r.id == F.FACTS_REQUIREMENT]
        self.assertEqual(len(req), 1)
        self.assertTrue(req[0].mandatory)
        for said in ('04-8123456', 'רחוב הרצל 12, חיפה', 'ראשון עד חמישי 8:00 עד 19:00', 'שישי 7:00 עד 14:00'):
            self.assertIn(said, req[0].text)
        crit = [a for a in given.acceptance if a.id == F.FACTS_REQUIREMENT][0]
        self.assertIn('"04-8123456"', crit.text)
        self.assertIn('"רחוב הרצל 12, חיפה"', crit.text)
        self.assertEqual(len(facts), 4)

    def test_the_facts_are_the_canon_the_review_reads(self):
        canon = F.build_canon(PROMPT)
        shown = dict(F.facts_to_show(PROMPT))
        self.assertIn(shown['phone'], [f.source_ref for f in canon.facts if f.key == 'phone'])
        self.assertIn(shown['address'], [f.source_ref for f in canon.facts if f.key == 'address'])

    def test_no_facts_no_requirement_and_added_once(self):
        self.assertEqual(F.facts_to_show('אתר לבית קפה'), [])
        self.assertIs(F.with_facts(SPEC, []), SPEC)
        once = F.with_facts(SPEC, F.facts_to_show(PROMPT))
        self.assertIs(F.with_facts(once, F.facts_to_show(PROMPT)), once)

    def test_hours_alone_get_a_criterion_too(self):
        spec = F.with_facts(SPEC, F.facts_to_show('שעות פתיחה: ראשון עד חמישי 8:00 עד 19:00'))
        crit = [a for a in spec.acceptance if a.id == F.FACTS_REQUIREMENT][0]
        self.assertIn('8:00 עד 19:00', crit.text)

    def test_no_architect_is_said(self):
        with self.assertLogs('omni_prod.fact_canon', 'WARNING') as logs:
            F.install_facts(SimpleNamespace(executor=Executor()), PROMPT)
        self.assertIn('FACTS_NOT_CARRIED', logs.output[0])

    def test_the_worker_and_the_rehearsal_install_it(self):
        worker = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertLess(worker.index('install_review_request(engine, prompt)'), worker.index('install_facts(engine, prompt)'))
        self.assertIn("report['facts_carried'] = len(install_facts(engine, prompt))",
                      (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
