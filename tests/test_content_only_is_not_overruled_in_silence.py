"""A content-only answer is not overruled in silence, and a hash is not a phone (production 2026-11-17, "148 דלתות").

1. The owner answered "אתר תוכן בלבד: כן", was then asked "האם יישמרו פרטים אישיים?", answered "כן", and the first
   answer was dropped without a word: the brief said "persistence: records" and the site became a leads database.
   A site that stores nothing from its visitors stores no personal details, so the question is not asked after it.
2. Found while fixing 1: the fact canon read a phone number out of the brief's hex fingerprint
   ("fingerprint e029093349ecb315" -> +97229093349). Whether a brief got an invented phone depended on its hash."""
import unittest

from omni_prod import discovery as d
from omni_prod.fact_canon import build_canon

PROMPT = 'אתר לחברת דלתות מקצועית, טלפון 050-345-6723'


def walk(first: dict):
    """The real catalogue walk: the customer's answers in `first` (in order), every other question delegated."""
    b = d.start(PROMPT)
    asked = []
    for _ in range(40):
        must = d.must_ask(b)
        group = must[:1] if must else (d.next_group(b)[1] or [])[:1]
        if not group:
            break
        q = group[0]
        asked.append(q.id)
        b = d.answer(b, {q.id: first.get(q.id, d.DELEGATE)})
    return b, asked


class ContentOnlyHolds(unittest.TestCase):
    def test_after_content_only_yes_personal_data_is_not_asked_and_the_site_stores_nothing(self):
        b = d.start(PROMPT)
        b = d.answer(b, {'content_only': 'yes'})                     # the production order: content_only first
        self.assertNotIn('personal_data', [q.id for q in d.pending(b)])
        text = d.requirements_text(b)
        self.assertIn('"persistence":"none"', text)
        self.assertIn('CONTENT-ONLY website', text)
        self.assertIn('Do not store personal or contact details of people.', text)
        self.assertNotIn('"persistence":"records"', text)

    def test_personal_data_yes_first_still_means_a_site_that_stores(self):
        b, asked = walk({'login': 'none', 'personal_data': 'yes', 'audience': 'internal'})
        self.assertIn('personal_data', asked)
        self.assertNotIn('content_only', asked)
        self.assertIn('"persistence":"records"', d.requirements_text(b))

    def test_the_approval_summary_says_personal_details_are_not_stored(self):
        b = d.answer(d.start(PROMPT), {'content_only': 'yes', 'login': 'none'})
        self.assertIn('שמירת פרטים אישיים', d.summary(b, 'he')['excluded'])


class AHashIsNotAPhone(unittest.TestCase):
    def test_the_production_fingerprint_reads_no_phone(self):
        self.assertEqual(build_canon('--- Approved project brief (binding; fingerprint e029093349ecb315) ---')
                         .values('phone'), set())
        self.assertEqual(build_canon('sha256:7ad9ea46ba89c4411413f108350ec985e231bf5b557d3e15dfe63dead926ec10')
                         .values('phone'), set())

    def test_real_phones_are_still_read(self):
        for text, phone in (('טלפון 050-345-6723', '+972503456723'), ('03-5551234', '+97235551234'),
                            ('דלת ב-1390 ש"ח, 054-7712345', '+972547712345'), ('0504000162', '+972504000162')):
            self.assertEqual(build_canon(text).values('phone'), {phone}, text)


if __name__ == '__main__':
    unittest.main()
