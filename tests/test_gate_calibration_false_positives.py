"""Gate calibration (2026-11-19): the two false findings in the calibration builds, on the production strings.

The calibrating gates' findings across the five builds that carry `evidence.skill_gates` (SELECT on build_jobs):
- HE_GENDER on bld_d36b3b4e: "פתיחת פניית שירות חדשה" -- a construct phrase; "חדשה" describes "פנייה" (feminine),
  so it is right. The probe judged it against "שירות".
- ADDRESS_INCOMPLETE on bld_d36b3b4e: where "תאריך שירות" -- the page's "כתובת" was a form field's <label> and the
  next text node was the next field's label. The served HTML of that build was not read; the form below rebuilds the
  structure the finding shows (a bare label, the next label after it).
The real errors the units exist for still fail.
"""
import unittest

from omni_prod.skill_units.he_gender.probe import probe as he_gender
from omni_prod.skill_units.links_address.probe import probe as address

PRODUCTION_HE = '<button>פתיחת פניית שירות חדשה</button>'
PRODUCTION_FORM = ('<form><label for="addr">כתובת</label><input id="addr" name="address">'
                   '<label for="when">תאריך שירות</label><input id="when" type="date"></form>')


class HebrewGender(unittest.TestCase):
    def test_the_production_construct_phrase_is_not_a_finding(self):
        self.assertEqual(he_gender(PRODUCTION_HE)['status'], 'pass')

    def test_construct_heads_of_the_adjectives_gender_are_ambiguous(self):
        for text in ('הזמנת משלוח מהירה', 'ארוחת שבוע טעימה', 'מנת בשר טרייה'):
            with self.subTest(text=text):
                self.assertEqual(he_gender(f'<p>{text}</p>')['status'], 'pass')

    def test_the_real_errors_still_fail(self):
        for text in ('מנה טעים', 'בשר טרייה', 'שירות חדשה', 'הבשר הטרייה', 'שתי מוצרים'):
            with self.subTest(text=text):
                self.assertEqual(he_gender(f'<p>{text}</p>')['code'], 'HE_GENDER')

    def test_a_head_of_the_other_gender_does_not_excuse_the_noun(self):
        # "חנות" is feminine, "בשר" masculine, "טרייה" feminine: the head agrees, so it is ambiguous -- not judged.
        # A masculine head with a feminine adjective is no excuse: "מחיר שירות חדשה" is still an error.
        self.assertEqual(he_gender('<p>מחיר שירות חדשה</p>')['code'], 'HE_GENDER')


class Address(unittest.TestCase):
    def test_a_form_field_label_is_not_an_address(self):
        self.assertEqual(address(PRODUCTION_FORM)['status'], 'pass')

    def test_a_shown_address_is_still_judged(self):
        self.assertEqual(address('<p>כתובת:</p><p>הרצל</p>')['code'], 'ADDRESS_INCOMPLETE')
        self.assertEqual(address('<p>כתובת: הרצל</p>')['code'], 'ADDRESS_INCOMPLETE')
        self.assertEqual(address('<p>כתובת: הרצל 12, חיפה</p>')['status'], 'pass')

    def test_a_label_with_its_address_inline_is_judged_even_beside_a_form(self):
        html = PRODUCTION_FORM + '<footer><p>כתובת: הרצל</p></footer>'
        self.assertEqual(address(html)['code'], 'ADDRESS_INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
