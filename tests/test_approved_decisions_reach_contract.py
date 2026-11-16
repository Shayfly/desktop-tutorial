"""Fixture FIRST (Michael 2026-11-11): an approved customer capability decision ("ובלי תשלום"-type) must reach the
Build Contract. On main it did not: product_architect read the decisions from `clean`, whose newlines were collapsed,
so the line-anchored "Approved project brief" marker never matched and every approved decision was dropped.

Gate for the fix: (1) the decision reaches the contract; (2) a request WITHOUT decisions is byte-identical (contract
fingerprints pinned from main before the fix); (3) the explicit-request guard still keeps a clear ask."""
from __future__ import annotations

import unittest

from omni_prod import discovery as d
from omni_prod.product_architect import ProductArchitect

CREATED = '2026-11-11T00:00:00+00:00'


def contract(brief):
    return ProductArchitect().compile(brief.prompt + '\n' + d.requirements_text(brief), project_id='p',
                                      contract_version=1, created_at=CREATED)


def extra(c):
    return [r.key for r in c.capability_plan.requirements if not r.key.startswith(('software.', 'target.'))]


class DecisionReachesContract(unittest.TestCase):
    def test_pay_at_the_counter_is_not_an_online_payment(self):
        b = d.start('דף לבית הקפה שלנו "קפה נחת", עם התפריט והשעות. התשלום רק בקופה במקום, לא באתר.')
        self.assertIn('integration.payment', extra(contract(b)))          # the keyword alone finds "תשלום"
        b.semantic_decisions = [{'key': 'integration.payment', 'decision': 'not_required',
                                 'evidence': 'התשלום רק בקופה במקום', 'reason': 'payment happens at the counter'}]
        c = contract(b)
        self.assertNotIn('integration.payment', extra(c))
        self.assertNotIn('payments', c.required_integrations)

    def test_a_clear_ask_is_still_kept(self):
        b = d.start('דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי')
        b.semantic_decisions = [{'key': 'integration.payment', 'decision': 'not_required',
                                 'evidence': 'תשלום אונליין', 'reason': 'model guess'}]
        self.assertIn('integration.payment', extra(contract(b)))


# Pinned on origin/main before the fix: a request with no decisions must not change by one byte.
GOLDEN = {
    # #335 (c), Michael 2026-11-13: this request asks for call and WhatsApp buttons with no phone, so its approved
    # spec now carries "Not given by the customer ... phone -- show no call or WhatsApp button" (was 65d1b847...)
    'תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים". שיהיה כפתור להתקשר וכפתור וואטסאפ.':
        # 2026-11-13 (the cafe fix): no waiver was given, so the spec lists the phone as MISSING instead of
        # saying "approved without it" (was 8734a337...)
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was 0c291947...)
        'sha256:7ad9ea46ba89c4411413f108350ec985e231bf5b557d3e15dfe63dead926ec10',
    'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was d2b57978...)
        'sha256:99a3ccd75d2a90bf4c3f66c34520ab1db558f457ade93e925769060d618f5e06',
    'Build a team task tracker web app: users sign up and log in, create projects, add tasks with due dates':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was 13cf3807...)
        'sha256:051707d17377223b8d574b2c167335795288a95ceb4acff620ca435eef383dc7',
    'דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was 3eb15832...)
        'sha256:6ab2a7a305f33642ecce95003b154f522896db595f5deb95a561479cc8e84831',
}


class NoDecisionsUnchanged(unittest.TestCase):
    def test_contracts_without_decisions_are_byte_identical(self):
        for prompt, fingerprint in GOLDEN.items():
            with self.subTest(prompt=prompt[:30]):
                self.assertEqual(contract(d.start(prompt)).contract_fingerprint, fingerprint)


if __name__ == '__main__':
    unittest.main()
