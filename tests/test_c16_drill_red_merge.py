"""C16 drill (monthly; founder 2026-10-21; this run 2026-11-21): an isolated PR whose required checks are RED on purpose.

It fails ONLY on the drill branch (drill/c16-red-merge-2026-11), so `test` is red on the PR. If it were ever merged by
mistake it would pass on main and change nothing else: the PR adds this file only.
The drill: a non-admin identity (the bot's GITHUB_TOKEN) tries to merge this PR -> GitHub must refuse (HTTP 405).
"""
import os
import unittest

DRILL_BRANCH = 'drill/c16-red-merge-2026-11'


class C16DrillRedMerge(unittest.TestCase):
    def test_red_on_the_drill_branch_only(self):
        ref = os.environ.get('GITHUB_HEAD_REF') or os.environ.get('GITHUB_REF_NAME') or ''
        self.assertNotEqual(ref, DRILL_BRANCH, 'C16 drill: this PR is red on purpose and must not be mergeable')


if __name__ == '__main__':
    unittest.main()
