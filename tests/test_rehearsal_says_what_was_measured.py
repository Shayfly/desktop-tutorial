"""A calibration report says what the gate measured, not only where (2026-11-17: the butcher and the cafe both
reported MEASURE on paragraphs, and the notice had no number to calibrate the limit against)."""
import json
import unittest

from omni_prod import rehearsal as R

REPORT = {'prompt': 'x', 'g_apple': {'mode': 'warn', 'contract': {'fingerprint': 'abc'}, 'last': {
    'status': 'fail', 'reason': None, 'not_run': [],
    'static': [{'code': 'PX_OFF_SCALE', 'where': '.phone-link { line-height: 44px }', 'why': '44px is not on the scale'}],
    'render': [{'code': 'MEASURE', 'width': 1440, 'selector': 'p.story-text', 'why': '96 characters a line'}],
    'reviewers': []}}}


class TheNoticeCarriesTheMeasurement(unittest.TestCase):
    def note(self):
        found = [line for line in R.annotations(REPORT) if 'title=g-apple::' in line]
        self.assertEqual(len(found), 1)
        return json.loads(found[0].split('::', 2)[2].replace('%0A', '\n').replace('%25', '%'))

    def test_a_render_finding_says_what_was_measured(self):
        self.assertEqual(self.note()['render'], [['MEASURE', 1440, 'p.story-text', '96 characters a line']])

    def test_a_static_finding_says_why(self):
        self.assertEqual(self.note()['static'],
                         [['PX_OFF_SCALE', '.phone-link { line-height: 44px }', '44px is not on the scale']])


class TheHeroRule(unittest.TestCase):
    def test_the_generator_is_told_not_to_leave_half_the_hero_empty(self):
        """Three calibration builds of three got the same P1 from the typography reviewer."""
        from omni_prod.g_apple import contract as C
        prompt = R.approved_prompt('אתר לבית קפה בשם קפה נחמה, טלפון 03-5551234',
                                   {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
        rules = C.rules(C.build(prompt))
        self.assertIn('Never text in one half and an empty half beside it', rules)
        self.assertIn('centred as a block with a max-width', rules)


if __name__ == '__main__':
    unittest.main()
