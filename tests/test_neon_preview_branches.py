"""Preview-branch hygiene: what is deleted, what is never touched, and the alert."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
import neon_preview_branches as N  # noqa: E402

NOW = dt.datetime(2026, 11, 11, 18, 0, tzinfo=dt.timezone.utc)


def br(name, created='2026-11-01T00:00:00Z', **kw):
    return {'id': 'br-' + name.replace('/', '-'), 'name': name, 'created_at': created, **kw}


BRANCHES = [br('main', default=True, primary=True), br('backup-before-042'),
            br('preview/fix/old-merged'), br('preview/fix/open-one'),
            br('preview/fix/brand-new', created='2026-11-11T17:30:00Z'),
            br('preview/fix/protected', protected=True)]


class Plan(unittest.TestCase):
    def test_prune_deletes_only_previews_without_an_open_pr(self):
        delete, keep = N.plan(BRANCHES, {'fix/open-one'}, only=None, min_age_hours=1, now=NOW)
        self.assertEqual([b['name'] for b in delete], ['preview/fix/old-merged'])
        self.assertEqual(sorted((b['name'], why) for b, why in keep),
                         [('preview/fix/brand-new', 'younger than the minimum age'),
                          ('preview/fix/open-one', 'open PR'), ('preview/fix/protected', 'protected')])

    def test_main_and_backups_are_never_candidates(self):
        delete, keep = N.plan(BRANCHES, set(), only=None, min_age_hours=0, now=NOW)
        names = {b['name'] for b in delete} | {b['name'] for b, _ in keep}
        self.assertNotIn('main', names)
        self.assertNotIn('backup-before-042', names)

    def test_pr_closed_deletes_exactly_that_branch(self):
        delete, _ = N.plan(BRANCHES, set(), only='fix/brand-new', min_age_hours=1, now=NOW)
        self.assertEqual([b['name'] for b in delete], ['preview/fix/brand-new'])   # age does not protect it then

    def test_pr_closed_never_deletes_a_protected_one(self):
        delete, keep = N.plan(BRANCHES, set(), only='fix/protected', min_age_hours=1, now=NOW)
        self.assertEqual(delete, [])


MIGRATION_AT = dt.datetime(2026, 11, 3, 20, 29, 38, tzinfo=dt.timezone.utc)   # 042 landed in main


class ResetRule(unittest.TestCase):
    """Michael 2026-11-11: a preview branch whose data was taken from main before the latest migration is reset."""

    def test_data_from_before_the_migration_is_reset(self):
        old = br('preview/fix/reconciler', created='2026-11-02T22:28:55Z', parent_id='br-main')
        new = br('preview/fix/new', created='2026-11-05T00:00:00Z', parent_id='br-main')
        self.assertEqual([b['name'] for b in N.needs_reset([old, new], MIGRATION_AT)], ['preview/fix/reconciler'])

    def test_a_branch_reset_after_the_migration_is_not_reset_again(self):
        b = br('preview/fix/reconciler', created='2026-11-02T22:28:55Z', parent_id='br-main',
               last_reset_at='2026-11-11T19:00:00Z')
        self.assertEqual(N.needs_reset([b], MIGRATION_AT), [])

    def test_never_main_backups_or_protected(self):
        branches = [br('main', created='2026-10-25T00:00:00Z', default=True, primary=True),
                    br('backup-before-042', created='2026-11-01T00:00:00Z', parent_id='br-main'),
                    br('preview/fix/p', created='2026-11-01T00:00:00Z', parent_id='br-main', protected=True)]
        self.assertEqual(N.needs_reset(branches, MIGRATION_AT), [])


class Workflow(unittest.TestCase):
    def test_the_secret_never_meets_pr_code(self):
        wf = (pathlib.Path(__file__).resolve().parents[1] / '.github/workflows/neon-preview-branches.yml').read_text()
        self.assertIn('pull_request_target', wf)
        self.assertNotIn('github.event.pull_request.head.sha', wf)    # no checkout of the PR head
        self.assertIn('persist-credentials: false', wf)
        self.assertIn('default: "false"', wf)                           # dispatch is a dry run by default

    def test_the_reset_runs_when_a_migration_lands_and_reads_its_time_from_git(self):
        wf = (pathlib.Path(__file__).resolve().parents[1] / '.github/workflows/neon-preview-branches.yml').read_text()
        self.assertIn("paths: ['infra/postgres/**']", wf)
        self.assertIn('fetch-depth: 0', wf)
        self.assertIn('--diff-filter=A --format=%cI', wf)


if __name__ == '__main__':
    unittest.main()
