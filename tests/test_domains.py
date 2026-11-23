"""The 30 domain files are something the engine reads (warehouse 127, acceptance 1).

"30 קבצי תחום עוברים סכמה אחת. שדה חסר נכשל בקול, עם שם התחום והשדה."

omni_prod.domains reads docs/domains/<slug>.md against the template in docs/domains/README.md. Every one of the 30
files passes; a file with a heading, a mandatory fact, a failure mode, the professional language, the legal section
or its references missing fails, and the message names the domain and the field. The mutations below are the five
the warehouse section lists, as far as acceptance 1 reaches (the build-side ones are acceptance 2).
"""
from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from omni_prod import domains as D

ROOT = Path(__file__).resolve().parents[1]


class EveryDomainPasses(unittest.TestCase):
    def test_there_are_thirty_and_each_passes_the_one_schema(self):
        found = D.all_domains()
        self.assertEqual(len(found), 30, [d.slug for d in found])
        self.assertEqual(D.check(), [])

    def test_every_domain_is_in_the_readme_table_and_the_table_has_no_stranger(self):
        readme = (D.DOCS / 'README.md').read_text(encoding='utf-8')
        listed = set(re.findall(r'\[([a-z-]+)\.md\]\(\1\.md\)', readme))
        self.assertEqual({d.slug for d in D.all_domains()}, listed)

    def test_each_domain_names_itself_and_carries_the_templates_headings_in_order(self):
        for d in D.all_domains():
            with self.subTest(d.slug):
                self.assertTrue(d.name)
                self.assertEqual([h for h in d.sections if h in D.HEADINGS], D.HEADINGS)

    def test_every_reference_was_checked_on_a_date_and_is_not_also_rejected(self):
        for d in D.all_domains():
            with self.subTest(d.slug):
                verified, rejected = d.references()
                self.assertGreaterEqual(len(verified), D.MIN_REFERENCES)
                self.assertLessEqual(len(verified), D.MAX_REFERENCES)
                self.assertEqual(set(verified) & set(rejected), set())


class AFaultIsCaughtLoudly(unittest.TestCase):
    """Each fault is planted in a COPY of the real files, and the message must name the domain and the field."""

    def plant(self, slug, edit):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(D.DOCS, tmp / 'domains')
        p = tmp / 'domains' / f'{slug}.md'
        p.write_text(edit(p.read_text(encoding='utf-8')), encoding='utf-8')
        found = [m for m in D.check(tmp / 'domains') if m.startswith(f'{slug}:')]
        self.assertTrue(found, f'the fault in {slug} was not caught')
        return ' | '.join(found)

    def test_a_domain_without_mandatory_facts_does_not_pass(self):
        out = self.plant('hair-salon', lambda s: re.sub(r'## 3\. Mandatory facts.*?(?=## 4\.)', '', s, flags=re.S))
        self.assertIn('3. Mandatory facts', out)

    def test_mandatory_facts_without_a_question_to_ask_does_not_pass(self):
        def edit(s):
            start = s.index('## 3. Mandatory facts'); end = s.index('## 4.')
            return s[:start] + '## 3. Mandatory facts\n\nThe usual ones.\n\n' + s[end:]
        self.assertIn('no question', self.plant('restaurant', edit))

    def test_a_section_that_is_never_empty_may_not_be_waived(self):
        def edit(s):
            start = s.index('## 7. Legal'); end = s.index('## 8.')
            return s[:start] + '## 7. Legal\n\nNothing for this domain. Not relevant.\n\n' + s[end:]
        out = self.plant('clinic', edit)
        self.assertIn('7. Legal', out)
        self.assertIn('never empty', out)

    def test_a_dead_reference_list_does_not_pass(self):
        def edit(s):
            start = s.index('## 9. References'); end = s.index('## 10.')
            return s[:start] + '## 9. References\n\nVerified: none yet.\n\n' + s[end:]
        self.assertIn('verified references', self.plant('dentist', edit))

    def test_a_rejected_site_counted_as_a_reference_does_not_pass(self):
        """The five-to-eight is on sites that loaded: a file whose references are all in the rejected list fails."""
        def edit(s):
            start = s.index('## 9. References'); end = s.index('## 10.')
            rows = '\n'.join(f'| {i} | https://example{i}.test | 2026-11-21 | observed |' for i in range(1, 7))
            return s[:start] + '## 9. References\n\nLoaded and not used:\n\n' + rows + '\n\n' + s[end:]
        self.assertIn('verified references', self.plant('lawyer', edit))

    def test_a_missing_heading_names_the_heading(self):
        out = self.plant('garage', lambda s: s.replace('## 5. Failure modes', '## 5. What breaks'))
        self.assertIn('missing heading "5. Failure modes"', out)


if __name__ == '__main__':
    unittest.main()
