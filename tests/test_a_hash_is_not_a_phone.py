"""A hash is not a phone (found 2026-11-17 while following "148 דלתות"): the fact canon read a phone number out of
the brief's hex fingerprint ("fingerprint e029093349ecb315" -> +97229093349). Whether a brief got an invented phone
depended on its hash."""
import unittest

from omni_prod.fact_canon import build_canon


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
