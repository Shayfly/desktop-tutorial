"""The rehearsal can build from an approved brief, as a customer's build does (calibration, 2026-11-17).

Rehearsals 44025252867 and 44025259144 got a raw request: a cafe's page was contracted as an app ("missing required
behavior kinds: auth, data_create, role") and its phone number was called invented. The real discovery functions and
the real contract compile run here."""
import unittest
from pathlib import Path

from omni_prod import rehearsal as R
from omni_prod.product_architect import ProductArchitect

CAFE = ('אתר לבית קפה שכונתי בתל אביב בשם קפה נחמה: תפריט עם מחירים, הסיפור שלנו, שעות פתיחה 07:00-19:00, '
        'טלפון 03-5551234, כתובת אבן גבירול 100 תל אביב')
ANSWERS = {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'}
ROOT = Path(__file__).resolve().parent.parent


class TheApprovedBrief(unittest.TestCase):
    def test_the_prompt_carries_the_brief_block_and_the_customers_decision(self):
        prompt = R.approved_prompt(CAFE, ANSWERS)
        self.assertTrue(prompt.startswith(CAFE))
        self.assertIn('--- Approved project brief (binding; fingerprint ', prompt)
        self.assertIn('"persistence":"none"', prompt)
        self.assertIn('03-5551234', prompt.split('--- Approved project brief')[1])     # the customer's own facts

    def test_with_the_brief_a_cafe_page_is_not_contracted_as_an_app(self):
        compile_ = lambda text: ProductArchitect().compile(text, project_id='t', contract_version=1)
        with_brief = compile_(R.approved_prompt(CAFE, ANSWERS))
        self.assertEqual([q.id for q in with_brief.unresolved_questions], [])
        self.assertEqual(with_brief.to_dict().get('artifact_class'), 'page')

    def test_a_question_only_the_customer_may_answer_is_never_guessed(self):
        with self.assertRaises(ValueError) as ctx:
            R.approved_prompt(CAFE, {})
        self.assertIn('pass it in answers', str(ctx.exception))
        with self.assertRaises(ValueError):
            R.approved_prompt(CAFE, {'login': 'none', 'personal_data': 'no'})          # content_only still missing

    def test_main_builds_from_the_brief_when_answers_are_given_and_from_the_raw_request_when_not(self):
        import io
        import json
        from contextlib import redirect_stdout
        from unittest import mock
        seen = []
        fake = lambda prompt: seen.append(prompt) or {'outcome': 'ready', 'quality': {'passed': True}}
        with mock.patch.object(R, 'run', fake), mock.patch.object(R, 'annotations', lambda report: []), \
                redirect_stdout(io.StringIO()) as out:
            self.assertEqual(R.main([CAFE, json.dumps(ANSWERS)]), 0)
            self.assertEqual(R.main([CAFE, '']), 0)
            self.assertEqual(R.main([CAFE]), 0)
        self.assertIn('--- Approved project brief', seen[0])
        self.assertEqual(seen[1:], [CAFE, CAFE])
        self.assertIn('"brief_mode": true', out.getvalue().splitlines()[0])
        with self.assertRaises(ValueError):
            R.main([CAFE, '["not", "an", "object"]'])

    def test_the_walk_is_bounded(self):
        self.assertLessEqual(R.MAX_BRIEF_STEPS, 60)

    def test_the_workflow_passes_the_answers_and_an_empty_value_is_the_raw_request(self):
        wf = (ROOT / '.github' / 'workflows' / 'golden-rehearsal.yml').read_text(encoding='utf-8')
        self.assertIn('ANSWERS: ${{ inputs.answers }}', wf)
        self.assertIn('main([os.environ["PROMPT"], os.environ.get("ANSWERS", "")])', wf)
        src = (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertIn('prompt, brief_mode = argv[0], len(argv) > 1 and bool(argv[1].strip())', src)
        self.assertIn("report['brief_mode'] = brief_mode", src)


if __name__ == '__main__':
    unittest.main()
