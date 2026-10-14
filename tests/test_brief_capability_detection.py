"""The brief 148AI writes must not invent capabilities (post-deploy check
2026-10-09: "reject ... with a clear message" -> messaging, "Logo" -> image
generation; every discovery build was blocked with cost_quote_unknown)."""
import unittest

from omni_prod import discovery as d
from omni_prod.product_architect import ProductArchitect


def _approved_prompt(prompt, overrides=None):
    b = d.start(prompt, 'recommend')
    for _ in range(20):
        _, qs = d.next_group(b)
        if not qs:
            break
        answers = {}
        for q in qs:
            if overrides and q.field in overrides:
                answers[q.id] = overrides[q.field]
            elif q.delegable:
                answers[q.id] = d.DELEGATE
            else:
                answers[q.id] = b.hints.get(q.field) or (q.options[0].value if q.options else d.DELEGATE)
        b = d.answer(b, answers)
    return b.prompt + '\n' + d.requirements_text(b)


def _keys(contract):
    plan = contract.capability_plan.to_dict()
    return {r['key'] for r in plan['requirements']}


class BriefDoesNotInventCapabilities(unittest.TestCase):
    def test_family_shopping_list_needs_only_the_web_pipeline(self):
        c = ProductArchitect().compile(_approved_prompt(
            'אתר בעברית לרשימת קניות משפחתית: הוספת פריט עם כמות, סימון שנקנה ומחיקה. בלי התחברות משתמשים.'),
            project_id='p', contract_version=1)
        self.assertEqual(c.status.value, 'READY')
        self.assertNotIn('integration.messaging', _keys(c))
        self.assertNotIn('media.image.generate', _keys(c))
        self.assertEqual(tuple(c.required_integrations), ())

    def test_the_brief_still_binds_the_contract_prompt(self):
        c = ProductArchitect().compile(_approved_prompt('אתר בעברית לניהול תורים למספרה קטנה עם ביטול תור'),
                                       project_id='p', contract_version=1)
        self.assertIn(d.BRIEF_MARKER, c.prompt)

    def test_users_own_words_still_count(self):
        c = ProductArchitect().compile(_approved_prompt(
            'אתר בעברית לתורים עם שליחת הודעות whatsapp ללקוח לפני התור'), project_id='p', contract_version=1)
        self.assertIn('integration.messaging', _keys(c))

    def test_detection_text_keeps_the_sign_in_decision(self):
        text = 'tasks app\n' + d.BRIEF_MARKER + ' (binding) ---\nSign-in: simple sign-in, all users have the same rights.'
        self.assertEqual(d.detection_text(text), 'tasks app login')
        self.assertEqual(d.detection_text('no brief here'), 'no brief here')


if __name__ == '__main__':
    unittest.main()
