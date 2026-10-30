"""OMNI_INTAKE_CALL_BUDGET_USD is read by omni_prod/intake/mode.py; .env.example must name it (2026-10-30), with the
code default, and say what it does (a pre-check, not a per-message cap)."""
from __future__ import annotations

import re
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TheIntakeBudgetsAreDocumented(unittest.TestCase):
    def test_every_intake_budget_the_code_reads_is_in_the_example(self):
        code = (ROOT / 'omni_prod' / 'intake' / 'mode.py').read_text(encoding='utf-8')
        example = (ROOT / '.env.example').read_text(encoding='utf-8')
        names = set(re.findall(r"_money\('(OMNI_INTAKE_[A-Z_]+)'", code))
        self.assertEqual(names, {'OMNI_INTAKE_MODEL_BUDGET_USD', 'OMNI_INTAKE_DAILY_BUDGET_USD',
                                 'OMNI_INTAKE_CALL_BUDGET_USD'})
        for name in names:
            self.assertRegex(example, rf'(?m)^{name}=')

    def test_the_call_budget_example_is_the_code_default_and_says_pre_check(self):
        from omni_prod.intake.mode import DEFAULT_CALL_RESERVE
        example = (ROOT / '.env.example').read_text(encoding='utf-8')
        value = re.search(r'(?m)^OMNI_INTAKE_CALL_BUDGET_USD=(.*)$', example).group(1)
        self.assertEqual(Decimal(value), Decimal(str(DEFAULT_CALL_RESERVE)))
        self.assertIn('PRE-CHECK only', example)
        self.assertIn('The real cap is OMNI_INTAKE_MODEL_BUDGET_USD (per project)', example)

    def test_the_default_lets_one_venice_message_pass_the_pre_check(self):
        # Owner 2026-10-30: 0.01; one Venice message was quoted 0.00555 (pg evidence, 2026-10-28).
        from omni_prod.intake.mode import DEFAULT_CALL_RESERVE
        self.assertEqual(DEFAULT_CALL_RESERVE, Decimal('0.01'))
        self.assertGreater(DEFAULT_CALL_RESERVE, Decimal('0.00555'))

    def test_the_gate_compares_the_fixed_unit_never_a_prompt_estimate(self):
        # GATE-001: same spend, very different prompts -> same answer; resolve() takes no prompt at all.
        import inspect
        from omni_prod.intake import mode as M
        self.assertFalse({'prompt', 'message', 'quote', 'estimate'} & set(inspect.signature(M.resolve).parameters))


if __name__ == '__main__':
    unittest.main()
