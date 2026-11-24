"""A negated "store" answers the personal-data question even next to a "כן" that confirmed something else (production
2026-11-19, the owner's law-firm site: the question was asked three times). The messages are the owner's, verbatim."""
import unittest

from omni_prod import discovery as d
from omni_prod.intake import conversation_agent as A

PD = d.BY_ID['personal_data']
OWNER = ('כן, 03-5551234 נכון. לא לשמור פרטים, רק שהפנייה תגיע אליי.',
         'כן, אתר תוכן בלבד. הטופס יפתח וואטסאפ עם הפנייה, בלי לשמור כלום.')


class TheOwnersAnswersAreRead(unittest.TestCase):
    def test_both_production_answers_say_no(self):
        for text in OWNER:
            self.assertEqual(A.typed_choice(PD, text), 'no', text)

    def test_the_content_only_question_reads_the_second_as_yes(self):
        self.assertEqual(A.typed_choice(d.BY_ID['content_only'], OWNER[1]), 'yes')

    def test_storing_is_still_yes_and_an_unsure_answer_is_still_none(self):
        self.assertEqual(A.typed_choice(PD, 'כן, לשמור את הפרטים'), 'yes')
        self.assertIsNone(A.typed_choice(PD, 'כן... לא, לא יודע'))


if __name__ == '__main__':
    unittest.main()
