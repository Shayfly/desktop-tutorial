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

    def test_at_most_one_reset_per_branch_per_hour(self):
        now = dt.datetime(2026, 11, 11, 20, 0, tzinfo=dt.timezone.utc)
        wave = dt.datetime(2026, 11, 11, 19, 50, tzinfo=dt.timezone.utc)          # a second migration, 10 min later
        b = br('preview/fix/x', created='2026-11-01T00:00:00Z', parent_id='br-main', last_reset_at='2026-11-11T19:30:00Z')
        self.assertEqual(N.needs_reset([b], wave, now), [])                       # reset 30 min ago: wait
        self.assertEqual(len(N.needs_reset([b], wave, now + dt.timedelta(hours=1))), 1)

    def test_the_latest_migration_is_read_from_git_not_written_down(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        latest, at = N.latest_migration_at(str(root), 'HEAD')
        newest = sorted(p.name for p in (root / 'infra' / 'postgres').glob('[0-9][0-9][0-9]_*.sql'))[-1]
        self.assertEqual(latest, newest)
        self.assertTrue(at, 'git gave no time for the newest migration')
        for f in ('tools/neon_preview_branches.py', 'tools/preview_db_prepare.py',
                  '.github/workflows/neon-preview-branches.yml', '.github/workflows/deployment-verify.yml'):
            self.assertNotRegex((root / f).read_text(), r'\b0[0-9]{2}_[a-z_]+\.sql', f)   # no migration named in code

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
        self.assertIn('--reset-before latest', wf)

    def test_verify_prepares_the_database_first(self):
        wf = (pathlib.Path(__file__).resolve().parents[1] / '.github/workflows/deployment-verify.yml').read_text()
        self.assertLess(wf.index('python tools/preview_db_prepare.py'), wf.index('python tools/deployment_verify.py'))
        self.assertIn("if: github.event_name == 'deployment_status'", wf)


class Prepare(unittest.TestCase):
    """The per-preview preparation: never a fork, never without the key, the PR's migrations after the reset."""

    def setUp(self):
        import preview_db_prepare as P
        self.P = P

    def test_a_commit_that_heads_no_branch_here_is_not_prepared(self):
        from unittest import mock
        with mock.patch.dict('os.environ', {'NEON_API_KEY': 'k', 'GH_TOKEN': 't'}), \
                mock.patch.object(self.P, 'branch_of', return_value=None), \
                mock.patch.object(self.P.N, 'neon_branches') as listing:
            self.assertEqual(self.P.main(['--project', 'p', '--repo', 'r', '--sha', 'a' * 40]), 0)
            listing.assert_not_called()

    def test_reset_then_the_prs_own_migrations(self):
        from unittest import mock
        calls = []
        branch = br('preview/fix/x', created='2026-11-01T00:00:00Z', parent_id='br-main')
        with mock.patch.dict('os.environ', {'NEON_API_KEY': 'k', 'GH_TOKEN': 't'}), \
                mock.patch.object(self.P, 'branch_of', return_value='fix/x'), \
                mock.patch.object(self.P.N, 'neon_branches', return_value=[branch]), \
                mock.patch.object(self.P.N, 'latest_migration_at', return_value=('043_x.sql', '2026-11-10T00:00:00Z')), \
                mock.patch.object(self.P.N, '_call_json', side_effect=lambda *a, **k: calls.append('reset') or (200, {})), \
                mock.patch.object(self.P, 'connection_uri', return_value='postgresql://u:p@h/db'), \
                mock.patch.object(self.P, 'apply_pr_migrations', side_effect=lambda sha, url: calls.append('migrate') or [43]):
            self.assertEqual(self.P.main(['--project', 'p', '--repo', 'r', '--sha', 'a' * 40]), 0)
        self.assertEqual(calls, ['reset', 'migrate'])


if __name__ == '__main__':
    unittest.main()
