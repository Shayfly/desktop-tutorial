"""Two-week rule: who is closed, who is never."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
import stale_prs as S  # noqa: E402

NOW = dt.datetime(2026, 11, 11, 20, 0, tzinfo=dt.timezone.utc)


def pr(n, opened, head='feat/x', labels=()):
    return {'number': n, 'title': f'pr {n}', 'created_at': opened, 'head': {'ref': head},
            'labels': [{'name': l} for l in labels]}


class Rule(unittest.TestCase):
    def test_two_weeks_old_is_closed_younger_is_kept(self):
        close, keep = S.stale([pr(1, '2026-10-28T19:00:00Z'), pr(2, '2026-10-29T21:00:00Z')], NOW)
        self.assertEqual([p['number'] for p in close], [1])
        self.assertEqual([p['number'] for p, _ in keep], [2])

    def test_exemptions(self):
        old = '2026-09-01T00:00:00Z'
        close, keep = S.stale([pr(3, old, head='ci/v24-report'), pr(4, old, labels=['keep-open'])], NOW)
        self.assertEqual(close, [])
        self.assertEqual(sorted(why for _, why in keep), ['bot report', 'keep-open'])

    def test_dispatch_is_a_dry_run_by_default_and_the_note_says_branch_kept(self):
        wf = (pathlib.Path(__file__).resolve().parents[1] / '.github/workflows/stale-prs.yml').read_text()
        self.assertIn('default: "false"', wf)
        self.assertIn('הענף נשאר', S.NOTE)


if __name__ == '__main__':
    unittest.main()
