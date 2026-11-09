"""CEO 2026-11-09 items 3-5: no invented contact details, RTL pages by construction, faithful colour summary."""
import unittest
from types import SimpleNamespace

from omni_prod import discovery as d
from omni_prod.intake.question_skills import checklist
from omni_prod.page_locale import ensure_rtl, install, rtl_language
from omni_prod.skills_runtime import _invented_contact, _rtl_for_hebrew

CAFE_PAGE = ('<!doctype html><html><head><title>קפה</title></head><body><h1>קפה "בוקר טוב"</h1>'
             '<a href="https://wa.me/972501234567">הזמנה ב-WhatsApp</a><h2>איך מגיעים</h2>'
             '<p>כתובת: רחוב הנביאים 12, חיפה</p><p>טלפון</p><a href="tel:050-1234567">050-1234567</a>'
             '<p>אספרסו כפול ₪ 10</p><p>א-ה 07:00-14:00</p></body></html>')


class InventedContactTests(unittest.TestCase):
    def test_cafe_invented_phone_and_street_block(self):
        found = _invented_contact({'index.html': CAFE_PAGE}, {'request': 'דף נחיתה לבית קפה שכונתי בחיפה'})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, 'blocking')
        self.assertIn('0501234567', found[0].problem)
        self.assertIn('רחוב הנביאים 12', found[0].problem)

    def test_details_from_the_request_pass_in_any_format(self):
        req = 'בית קפה. וואטסאפ +972-50-123-4567, כתובת רחוב הנביאים 12 חיפה'
        self.assertEqual(_invented_contact({'index.html': CAFE_PAGE}, {'request': req}), [])

    def test_prices_hours_and_scripts_are_not_phones(self):
        page = ('<html><body><p>₪ 98</p><p>08:00-14:00</p><p>2026</p>'
                '<script>const id = "0501234567";</script></body></html>')
        self.assertEqual(_invented_contact({'index.html': page}, {'request': 'קפה'}), [])

    def test_backend_files_are_not_scanned(self):
        self.assertEqual(_invented_contact({'app.py': 'PHONE = "050-1234567"'}, {'request': 'קפה'}), [])

    def test_intake_asks_for_real_contact_details(self):
        items = ' '.join(checklist('website'))
        self.assertIn('REAL phone/WhatsApp number', items)
        self.assertIn('only real ones', items)


class RtlByConstructionTests(unittest.TestCase):
    def test_language(self):
        self.assertEqual(rtl_language('דף לבית קפה'), 'he')
        self.assertEqual(rtl_language('موقع لمقهى'), 'ar')
        self.assertIsNone(rtl_language('a cafe landing page'))

    def test_adds_dir_and_lang_only_where_missing(self):
        repo = {'index.html': '<!doctype html>\n<html>\n<body>שלום</body></html>',
                'en.html': '<html lang="en" dir="ltr"><body>Hi</body></html>',
                'he.html': '<html lang="he"><body>x</body></html>',
                'app.py': 'HTML = "<html><body></body></html>"'}
        out = ensure_rtl(repo, 'he')
        self.assertIn('<html dir="rtl" lang="he">', out['index.html'])
        self.assertEqual(out['en.html'], repo['en.html'])
        self.assertIn('<html lang="he" dir="rtl">', out['he.html'])
        self.assertEqual(out['app.py'], repo['app.py'])          # strings inside code are never edited
        self.assertEqual(_rtl_for_hebrew(out, {'request': 'קפה'}), [])

    def test_install_chains_the_existing_transform_and_keeps_its_attributes(self):
        calls = []

        class Logo:
            uri = '/logo.png'
            def __call__(self, repo):
                calls.append(1)
                return {**repo, 'logo.txt': 'x'}
            def redact_text(self, t):
                return t

        core = SimpleNamespace(repository_transform=Logo())
        engine = SimpleNamespace(core=core)
        self.assertEqual(install(engine, 'אתר לבית קפה'), 'he')
        out = core.repository_transform({'index.html': '<html><body/></html>'})
        self.assertEqual(calls, [1])
        self.assertIn('logo.txt', out)
        self.assertIn('dir="rtl"', out['index.html'])
        self.assertEqual(core.repository_transform.uri, '/logo.png')
        self.assertTrue(hasattr(core.repository_transform, 'redact_text'))

    def test_install_without_transform_and_english_prompt(self):
        core = SimpleNamespace()
        install(core, 'אתר')
        self.assertFalse(hasattr(core.repository_transform, 'redact_text'))
        self.assertIn('dir="rtl"', core.repository_transform({'a.html': '<html></html>'})['a.html'])
        plain = SimpleNamespace()
        self.assertIsNone(install(plain, 'a cafe site'))
        self.assertFalse(hasattr(plain, 'repository_transform'))


class ColourSummaryTests(unittest.TestCase):
    def test_cafe_colours_are_all_kept(self):
        self.assertEqual(d.colour_palette('בצבעי חום, קרם וירוק'), ['brown', 'cream', 'green'])
        self.assertEqual(d.colour_palette('בצבעי חום, קרם וירוק', preserve_words=True), ['חום', 'קרם', 'ירוק'])

    def test_longest_name_wins_and_new_shades_have_css(self):
        self.assertEqual(d.colour_palette('כחול כהה ולבן'), ['navy', 'white'])
        self.assertEqual(d.palette_css("בז' ותכלת"), ['#e8dcc4', '#7dd3fc'])


if __name__ == '__main__':
    unittest.main()
