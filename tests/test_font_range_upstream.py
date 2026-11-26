"""F2 (release review of 550320c): the live font-range test fails only when an upstream change breaks a page of ours,
and says every other upstream difference as a ::notice (tests/test_font_pair_range_live.upstream_findings).

Found: test_the_allowed_list_is_what_google_fonts_states_today compared 62 families with google/fonts main by exact
equality, on every pull request (browser-python's font-range job), so any upstream change -- a new classification, a
new subset, an extra weight -- turned every PR red. The comparison runs offline here, on the real function, with the
recorded entries of omni_prod/typography/font_pairs.json; the live job keeps its no-skip rule."""
from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path

import yaml

from omni_prod import typography as T
from tests.test_font_pair_range_live import DRIFT_KEYS, upstream_findings, write_notices

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'Heebo'


def recorded(family=FAMILY):
    entry = T._LIBRARY['families'][family]
    return {'name': family, **{k: entry[k] for k in ('licence', 'categories', 'classifications', 'scripts', 'weights')},
            'source': entry['source']}


def live_as_recorded(family=FAMILY):
    return {k: copy.deepcopy(v) for k, v in recorded(family).items() if k != 'source'}


class WhatBreaksAPageFails(unittest.TestCase):
    def test_the_same_as_recorded_is_nothing(self):
        r = recorded()
        self.assertEqual(upstream_findings(FAMILY, r, live_as_recorded(), r['weights'], set(r['weights'])), ([], []))

    def test_missing_or_renamed_or_not_served_or_another_licence_breaks(self):
        r = recorded()
        cases = {'missing': (None, r['weights']), 'renamed': ({**live_as_recorded(), 'name': 'Heebo Sans'}, r['weights']),
                 'no weight served': ({**live_as_recorded(), 'weights': []}, r['weights']),
                 'a loaded weight not served': (live_as_recorded(), [400]),
                 'licence': ({**live_as_recorded(), 'licence': 'APACHE2'}, r['weights'])}
        for what, (live, letters) in cases.items():
            with self.subTest(what):
                breaks, _ = upstream_findings(FAMILY, r, live, letters, {400, 700})
                self.assertTrue(breaks, what)

    def test_every_other_upstream_difference_is_a_notice_not_a_failure(self):
        r = recorded()
        changes = {'classifications': r['classifications'] + ['DISPLAY'], 'categories': r['categories'] + ['SERIF'],
                   'scripts': r['scripts'][:1], 'weights': r['weights'][:1]}
        self.assertEqual(set(changes), set(DRIFT_KEYS))
        for key, value in changes.items():
            with self.subTest(key):
                breaks, drift = upstream_findings(FAMILY, r, {**live_as_recorded(), key: value}, [400, 700],
                                                  set(r['weights']))
                self.assertEqual(breaks, [])
                self.assertEqual(len(drift), 1)
                self.assertTrue(drift[0].startswith(key + ':'))

    def test_the_notices_are_workflow_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'n.txt')
            write_notices(['Heebo: classifications: recorded [], upstream [\'DISPLAY\']'], path)
            self.assertEqual(Path(path).read_text(encoding='utf-8'),
                             "::notice title=font-range upstream::Heebo: classifications: recorded [], upstream "
                             "['DISPLAY']\n")


class TheJobPrintsThem(unittest.TestCase):
    def test_the_step_runs_always_after_the_tests_and_the_no_skip_rule_stays(self):
        job = yaml.safe_load((ROOT / '.github/workflows/browser-python.yml').read_text(encoding='utf-8'))['jobs']['font-range']
        names = [s.get('name') for s in job['steps']]
        at = names.index('Upstream differences (notices)')
        self.assertEqual(names[at - 1], 'Font range tests')
        self.assertEqual(job['steps'][at]['if'], 'always()')
        self.assertIn('cat font-range-notices.txt', job['steps'][at]['run'])
        self.assertIn('No test may be skipped', names[at + 1:])


if __name__ == '__main__':
    unittest.main()
