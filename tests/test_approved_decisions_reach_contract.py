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
        'sha256:0c2919477294892d47c92ea8b2e0ce0fd6869175919fdb26729b422fd30dd301',
    'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון':
        'sha256:d2b5797832ca497631b873da796320b679b40f708661191d72d67ff69ee25439',
    'Build a team task tracker web app: users sign up and log in, create projects, add tasks with due dates':
        'sha256:13cf38076cffe1318b5b16aebc7de51b9b2e2e25317c66bd3b2f3ec7dfab8a8b',
    'דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי':
        'sha256:3eb158327ac74c76c640d3ee9ad7efcdfba337dd51c123370270a56459bccff4',
}


class NoDecisionsUnchanged(unittest.TestCase):
    def test_contracts_without_decisions_are_byte_identical(self):
        for prompt, fingerprint in GOLDEN.items():
            with self.subTest(prompt=prompt[:30]):
                self.assertEqual(contract(d.start(prompt)).contract_fingerprint, fingerprint)


if __name__ == '__main__':
    unittest.main()
