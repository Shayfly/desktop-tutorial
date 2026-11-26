"""The customer's own page structure reaches the generator, in order (conversation agent phase 3; production
2026-11-17, "148 דלתות": the owner wrote the page section by section and the architect's rewrite could drop it).
The excerpt is the production message's own lines (intake_messages, read only). The real build loop runs."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import page_outline as O
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import FilePatch

ROOT = Path(__file__).resolve().parent.parent
DOORS = '''הבריף — להעתקה
שם העסק: 148 דלתות בהנהלת: נסים אוחנה טלפון: 050-345-6723

מבנה הדף:
הירו — "דלת ממד פולימרית. 1,390 ₪ כולל הובלה והרכבה." כותרת משנה: בלי לצמצם את פתח החדר, אחריות שנה על ההתקנה.
למה דלת פולימרית — שישה יתרונות, מנוסחים כטענות עובדתיות ולא כסופרלטיבים (התוכן למטה).
מה כלול במחיר — הובלה, הרכבה, פירוק הדלת הישנה, אחריות שנה על ההתקנה. רשימה קצרה וברורה.
שאלות נפוצות — חמש, עם תשובות אמיתיות (למטה).
צור קשר — טלפון לחיץ, כפתור וואטסאפ גדול, שם, אזור. בלי טופס.
פוטר — 148 דלתות, בהנהלת נסים אוחנה, טלפון.

תוכן סקשן 2 — שישה יתרונות (מבוסס מקורות):
לא סופגת לחות ולא מתנפחת.'''
SPEC = ProductSpec.from_dict({
    'title': '148 דלתות', 'summary': 'אתר', 'stack': ['python'],
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
        return ExecutionReport(False, (), 'stopped')


class TheStructureReachesTheGenerator(unittest.TestCase):
    def test_the_production_structure_is_read_in_order_as_written(self):
        titles = [t for t, _ in O.outline(DOORS)]
        self.assertEqual(titles, ['הירו', 'למה דלת פולימרית', 'מה כלול במחיר', 'שאלות נפוצות', 'צור קשר', 'פוטר'])
        self.assertIn('1,390 ₪ כולל הובלה והרכבה', O.outline(DOORS)[0][1])

    def test_through_the_real_build_loop(self):
        generator = Generator()
        engine = AutonomousProductEngine(architect=Architect(), generator=generator, executor=Executor(),
                                         repairer=None, max_repair_rounds=0)
        self.assertEqual(len(O.install(engine, DOORS)), 6)
        engine.build(DOORS)
        given = generator.specs[0]
        req = [r for r in given.requirements if r.id == O.REQUIREMENT][0]
        self.assertTrue(req.mandatory)
        self.assertLess(req.text.index('"הירו"'), req.text.index('"שאלות נפוצות"'))
        crit = [a for a in given.acceptance if a.id == O.REQUIREMENT][0]
        self.assertIn('"למה דלת פולימרית"', crit.text)
        self.assertIn('in this order', crit.text)

    def test_no_structure_heading_no_requirement(self):
        self.assertEqual(O.outline('אתר לבית קפה עם תפריט ושעות פתיחה'), [])
        self.assertIs(O.with_outline(SPEC, []), SPEC)
        once = O.with_outline(SPEC, O.outline(DOORS))
        self.assertIs(O.with_outline(once, O.outline(DOORS)), once)

    def test_the_brief_block_is_not_read_as_the_customers_structure(self):
        text = 'אתר\n--- Approved project brief (binding) ---\nמבנה הדף:\nהירו — משהו'
        self.assertEqual(O.outline(text), [])

    def test_it_is_bounded_and_the_cut_is_said(self):
        # the owner, 2026-11-26: 60 sections (20 before); past them the customer is told too (tests/test_silent_cuts.py)
        many = 'מבנה הדף:\n' + '\n'.join(f'סקשן {i} — תוכן {i}' for i in range(O.MAX_SECTIONS + 10))
        with self.assertLogs('omni_prod.page_outline', 'WARNING'):
            self.assertEqual(len(O.outline(many)), O.MAX_SECTIONS)

    def test_no_architect_is_said(self):
        with self.assertLogs('omni_prod.page_outline', 'WARNING') as logs:
            O.install(SimpleNamespace(executor=Executor()), DOORS)
        self.assertIn('PAGE_OUTLINE_NOT_CARRIED', logs.output[0])

    def test_the_worker_and_the_rehearsal_install_it(self):
        worker = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertLess(worker.index('install_facts(engine, prompt)'), worker.index('install_page_outline(engine, prompt)'))
        self.assertIn("report['outline_carried']", (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
