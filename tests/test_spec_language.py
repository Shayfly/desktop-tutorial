"""The spec is written in the customer's language (founder feedback 2026-10-07)."""
import unittest
from omni_prod.autonomous_agents import _ARCHITECT_SYSTEM
from omni_prod.product_evolution import _EVOLUTION_SYSTEM


class SpecLanguageTests(unittest.TestCase):
    def test_architect_writes_in_the_request_language(self):
        self.assertIn("same language as the user's request", _ARCHITECT_SYSTEM)

    def test_evolution_keeps_the_spec_language(self):
        self.assertIn('same language as the existing spec', _EVOLUTION_SYSTEM)


if __name__ == '__main__':
    unittest.main()


class TestableCriteriaTests(unittest.TestCase):
    """bld_85cc573b473341e9b3f10d248d743ff1: untestable criteria (Lighthouse,
    coverage %, localStorage, JS dialogs) exhausted five repair rounds."""

    def test_architect_requires_sandbox_testable_criteria(self):
        for needle in ('no browser and no network', 'Lighthouse', 'test-coverage percentages', 'browser storage'):
            self.assertIn(needle, _ARCHITECT_SYSTEM)

    def test_build_repair_sees_the_manifest_content(self):
        from omni_prod.autonomous_core import AutonomousProductEngine
        summary = AutonomousProductEngine._summary({'.omni/project.json': '{"verify": []}', 'app.py': 'x = 1'})
        entries = {e['path']: e for e in summary['files']}
        self.assertEqual(entries['.omni/project.json']['content'], '{"verify": []}')


class ContractRoundTripTests(__import__('unittest').TestCase):
    """Founder build 2026-10-08: HTTP 500 'build contract fingerprint mismatch'
    when the 80-char title was cut right after a space."""

    def test_every_prompt_prefix_round_trips(self):
        import json
        from omni_prod.build_contract import BuildContract
        from omni_prod.product_architect import ProductArchitect
        prompt = ('אתר בעברית לניהול רשימת משימות לצוות קטן: טופס להוספת משימה עם שם, אחראי ותאריך יעד, '
                  'טבלה של כל המשימות, כפתור לסימון משימה כבוצעה, כפתור מחיקה ליד כל משימה, וסינון לפי אחראי.')
        words = prompt.split()
        for n in range(3, len(words) + 1):
            c = ProductArchitect().compile(' '.join(words[:n]), project_id='prj_x', contract_version=1)
            again = BuildContract.from_dict(json.loads(json.dumps(c.to_dict(), ensure_ascii=False)))
            self.assertEqual(again.contract_fingerprint, c.contract_fingerprint)
