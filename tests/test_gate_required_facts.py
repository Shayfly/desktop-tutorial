"""Michael 2026-11-14: "עובדה שנדרשה ולא הופיעה בדף = חוסם, לא רק עובדה מומצאת."

The truth gate (skills_runtime._invented_contact, skill.copy_quality) blocked only facts the page INVENTED. Now a fact
the customer GAVE -- a phone, a street address, an opening-hours day (a closed day included) -- that the visible page
leaves out blocks too. JSON-LD or <meta> does not count; a tel: link does (it is the call button).

Real rows: the butcher's served page of 2026-11-14 (build bld_83529c13, round 1) and the approved brief it was built
from (revision 8), tests/fixtures/butcher_served_page_2026_11_14.json. The served page shows every given fact and
passes; the same page with one section taken out (labelled per test) blocks."""
import json
import re
import unittest
from pathlib import Path

from omni_prod import discovery as d
from omni_prod.fact_canon import build_canon
from omni_prod.skills_runtime import _invented_contact

FX = json.loads((Path(__file__).parent / 'fixtures' / 'butcher_served_page_2026_11_14.json').read_text(encoding='utf-8'))


def canon():
    brief = d.Brief.from_dict(FX['brief'])
    assert brief.fingerprint() == FX['brief_fingerprint']                     # the export is faithful
    return build_canon(brief.prompt + '\n' + d.requirements_text(brief))     # the build's request


def blocking(page):
    found = _invented_contact({}, {'rendered_pages': {'/': page}, 'canon': canon()})
    return [f.problem for f in found if f.severity == 'blocking']


def without(pattern):
    page, n = re.subn(pattern, '', FX['page'], flags=re.S)
    assert n, pattern
    return page


HOURS = r'<section class="card" aria-labelledby="hours-heading">.*?</section>'


class GivenFactsMustBeShown(unittest.TestCase):
    def test_the_served_page_shows_every_given_fact_and_passes(self):
        self.assertEqual(blocking(FX['page']), [])

    def test_without_the_hours_section_it_blocks_day_by_day(self):
        problems = blocking(without(HOURS))
        self.assertEqual(len(problems), 1)
        self.assertIn('facts the customer gave are missing from the page', problems[0])
        for day in ('ראשון 07:00-19:00', 'שישי 07:00-14:00'):
            self.assertIn(day, problems[0])

    def test_hours_only_in_json_ld_do_not_count(self):
        self.assertIn('Su-Th 07:00-19:00', FX['page'])                       # the served page has them there too
        self.assertTrue(blocking(without(HOURS)))

    def test_a_closed_day_left_out_blocks(self):
        page = without(r'<tr>\s*<th scope="row">שבת</th>\s*<td>שבת סגור</td>\s*</tr>')
        problems = blocking(page)
        self.assertEqual(len(problems), 1)
        self.assertIn('hours שבת סגור', problems[0])

    def test_without_the_address_it_blocks(self):
        page = FX['page'].replace('רחוב נתיב המזלות 22, ירושלים', 'ירושלים')
        self.assertTrue(any('address' in p for p in blocking(page)))

    def test_without_any_phone_or_call_link_it_blocks(self):
        page = re.sub(r'(?:\+972|0)504000162', '', FX['page'])
        self.assertTrue(any('phone +972504000162' in p for p in blocking(page)))


if __name__ == '__main__':
    unittest.main()
