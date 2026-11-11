"""STATUS.md and TASKS.md are append-only logs that every PR extends at the same trailing spot (2026-10-30: three PRs
re-conflicted each other on every merge). .gitattributes resolves those conflicts with the union driver; this test is
the guard that a resolution -- by hand or by the driver -- never leaves a marker or duplicates an entry."""
from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(r'^(<<<<<<< |=======$|>>>>>>> )', re.M)


class TheStatusDocs(unittest.TestCase):
    def test_no_conflict_marker_is_left(self):
        for name in ('STATUS.md', 'TASKS.md'):
            with self.subTest(name=name):
                self.assertIsNone(MARKER.search((ROOT / name).read_text(encoding='utf-8')))

    def test_no_dated_section_appears_twice_in_status(self):
        # '## ' headings are the dated entries; repeated '### ' sub-headings inside them are legitimate.
        headings = re.findall(r'^## .+$', (ROOT / 'STATUS.md').read_text(encoding='utf-8'), re.M)
        self.assertEqual([h for h, n in Counter(headings).items() if n > 1], [])

    def test_no_task_id_appears_twice(self):
        ids = re.findall(r'^\| ([A-Z][A-Z0-9-]+) \|', (ROOT / 'TASKS.md').read_text(encoding='utf-8'), re.M)
        self.assertGreater(len(ids), 0)
        self.assertEqual([i for i, n in Counter(ids).items() if n > 1], [])

    def test_the_union_driver_is_declared_for_both(self):
        attrs = (ROOT / '.gitattributes').read_text(encoding='utf-8')
        for name in ('STATUS.md', 'TASKS.md'):
            self.assertRegex(attrs, rf'(?m)^{re.escape(name)} merge=union$')


if __name__ == '__main__':
    unittest.main()
