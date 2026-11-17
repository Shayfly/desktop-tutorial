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
        # 2026-11-16: the contract keeps the approved text's line breaks instead of one long line (was 7ad9ea46...)
        # 2026-11-17 DECISIONS 7: a florist is not a catalogue category; its colours now come from the nearest one
        # ("פרחים" is listed near furniture_interior) instead of "choose a palette" (was 0ccf837a...)
        'sha256:819fa719e42022fb786489e57c6252740e7a88bca72e3594f06c38f3064111e0',
    'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was d2b57978...)
        # 2026-11-16: the contract keeps the approved text's line breaks instead of one long line (was 99a3ccd7...)
        'sha256:25ba347e55f91c566d8d144842710c5e4c4956933c85e114128151c0f75b5b02',
    'Build a team task tracker web app: users sign up and log in, create projects, add tasks with due dates':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was 13cf3807...)
        # 2026-11-16: the contract keeps the approved text's line breaks instead of one long line (was 051707d1...)
        'sha256:39ae8a91350e10671b66fd074937a51fe7b24d975c58edcb256e1aa63cc1bf5d',
    'דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי':
        # 2026-11-16 warehouse 105: no colour stated -> the business category's palette, not blue (was 3eb15832...)
        # 2026-11-16: the contract keeps the approved text's line breaks instead of one long line (was 6ab2a7a3...)
        'sha256:903357297987bd003aff0910c2192c5815ffd46f60754e56fb6a42ded0bde2ec',
}


# The fingerprints pinned until 2026-11-16, when the contract stored its prompt as one long line. They are kept to
# prove that the line breaks are the ONLY thing that changed in these contracts (the test below).
ONE_LINE = {
    'תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים". שיהיה כפתור להתקשר וכפתור וואטסאפ.':
        # 2026-11-17 DECISIONS 7: the same one-line contract with the nearest category's colours (was 7ad9ea46...)
        'sha256:4a27b98fdbadc42088072c2c95a785108328171db30cbaeac4c96898928db699',
    'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון':
        'sha256:99a3ccd75d2a90bf4c3f66c34520ab1db558f457ade93e925769060d618f5e06',
    'Build a team task tracker web app: users sign up and log in, create projects, add tasks with due dates':
        'sha256:051707d17377223b8d574b2c167335795288a95ceb4acff620ca435eef383dc7',
    'דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי':
        'sha256:6ab2a7a305f33642ecce95003b154f522896db595f5deb95a561479cc8e84831',
}


class NoDecisionsUnchanged(unittest.TestCase):
    def test_contracts_without_decisions_are_byte_identical(self):
        for prompt, fingerprint in GOLDEN.items():
            with self.subTest(prompt=prompt[:30]):
                self.assertEqual(contract(d.start(prompt)).contract_fingerprint, fingerprint)

    def test_only_the_line_breaks_changed_on_2026_11_16(self):
        from omni_prod.build_contract import sha256_fingerprint
        self.assertEqual(set(ONE_LINE), set(GOLDEN))
        for prompt, before in ONE_LINE.items():
            with self.subTest(prompt=prompt[:30]):
                c = contract(d.start(prompt))
                self.assertIn('\n', c.prompt)
                payload = c._fingerprint_payload()
                payload['prompt'] = ' '.join(payload['prompt'].split())       # the prompt as it was stored before
                self.assertEqual(sha256_fingerprint(payload), before)         # every other field: byte for byte


if __name__ == '__main__':
    unittest.main()
