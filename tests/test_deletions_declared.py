"""Michael 2026-11-15: a deletion declaration is bound to the change it declares (deleted_sha256), never to the path
forever. Real path: a real git repository in a temp dir, the anchor commit and a head commit, and the real script
(scripts/deletions_declared.py, the code identity.yml runs). The #371 case: a file with an old allowance for one
replaced line gets a NEW deletion -- the old allowance must not cover it."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deletions_declared as DD  # noqa: E402


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp()
        git(self.dir, 'init', '-q', '-b', 'main')
        git(self.dir, 'config', 'user.email', 't@example.com')
        git(self.dir, 'config', 'user.name', 't')

    def commit(self, files: dict) -> str:
        for name, text in files.items():
            p = Path(self.dir) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        git(self.dir, 'add', '-A')
        git(self.dir, 'commit', '-q', '-m', 'c')
        return git(self.dir, 'rev-parse', 'HEAD')


def run(repo, anchor, allowed):
    decl = Path(repo.dir) / 'decl.json'
    decl.write_text(json.dumps({'allowed': allowed}))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = DD.main([anchor], cwd=repo.dir, declarations=decl)
    return rc, out.getvalue()


SIGNED = {'author': 'claude', 'reviewer': 'michael', 'reviewed_at': '2026-11-15'}


class BoundToTheChange(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.anchor = self.repo.commit({'t.py': 'a = 1\nb = 2\nc = 3\n', 'keep.py': 'x\n'})

    def digest_of(self, path):
        return DD.digest(DD.deleted_lines(self.anchor, path, cwd=self.repo.dir))

    def test_a_declaration_with_the_digest_of_this_change_passes(self):
        self.repo.commit({'t.py': 'a = 1\nb = 20\nc = 3\n'})
        rc, out = run(self.repo, self.anchor, {'t.py': {'reason': 'b changed', 'deleted_sha256': self.digest_of('t.py'), **SIGNED}})
        self.assertEqual(rc, 0, out)
        self.assertEqual(DD.deleted_lines(self.anchor, 't.py', cwd=self.repo.dir), ['b = 2'])

    def test_an_old_allowance_on_the_same_file_does_not_cover_a_new_change(self):
        old = DD.digest(['b = 2'])                                         # declared for an earlier change
        self.repo.commit({'t.py': 'a = 1\nb = 2\nc = 30\n'})                 # a new deletion: c = 3
        rc, out = run(self.repo, self.anchor, {'t.py': {'reason': 'b changed (#335)', 'deleted_sha256': old, **SIGNED}})
        self.assertEqual(rc, 1, out)
        self.assertIn('none matches: t.py', out)

    def test_a_path_only_declaration_covers_nothing(self):
        self.repo.commit({'t.py': 'a = 1\nc = 3\n'})
        rc, out = run(self.repo, self.anchor, {'t.py': {'reason': 'any change, forever', **SIGNED}})
        self.assertEqual(rc, 1, out)
        self.assertIn('no digest', out)

    def test_one_of_several_declarations_for_the_path_may_match(self):
        self.repo.commit({'t.py': 'b = 2\nc = 3\n'})
        rc, out = run(self.repo, self.anchor, {'t.py': [
            {'reason': 'older', 'deleted_sha256': DD.digest(['zzz']), **SIGNED},
            {'reason': 'a removed', 'deleted_sha256': self.digest_of('t.py'), **SIGNED}]})
        self.assertEqual(rc, 0, out)
        self.assertIn('a removed', out)

    def test_the_matching_declaration_still_needs_a_reviewer(self):
        self.repo.commit({'t.py': 'a = 1\nc = 3\n'})
        rc, out = run(self.repo, self.anchor, {'t.py': {'reason': 'b removed', 'deleted_sha256': self.digest_of('t.py'),
                                                        'author': 'claude', 'reviewer': '', 'reviewed_at': ''}})
        self.assertEqual(rc, 1, out)
        self.assertIn('have no reviewer note', out)

    def test_an_undeclared_file_fails_and_additions_need_nothing(self):
        self.repo.commit({'t.py': 'a = 1\nb = 2\nc = 3\nd = 4\n', 'keep.py': ''})
        rc, out = run(self.repo, self.anchor, {})
        self.assertEqual(rc, 1, out)
        self.assertIn('keep.py without a declared reason', out)
        self.assertNotIn('t.py', out.split('without a declared reason')[0].split('::error')[-1])

    def test_the_digest_helper_prints_what_to_declare(self):
        self.repo.commit({'t.py': 'a = 1\nc = 3\n'})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            DD.main([self.anchor, '--digest', 't.py'], cwd=self.repo.dir)
        self.assertEqual(out.getvalue().strip(), DD.digest(['b = 2']))


class TheAnchorIsTheMergeBaseParent(unittest.TestCase):
    """#371, 2026-11-15: the event's base.sha was f02404a while main had moved to be831c6 (#374 merged), so #374's own
    deletions were charged to #371. Reproduced: main moves after the branch, GitHub-style merge commit checked out."""
    def test_a_stale_base_charges_mains_changes_to_the_pr_and_the_merge_parent_does_not(self):
        repo = Repo()
        stale = repo.commit({'mine.py': 'a\n', 'theirs.py': 'x = 1\ny = 2\n'})
        git(repo.dir, 'checkout', '-q', '-b', 'pr')
        repo.commit({'mine.py': 'a\nb\n'})                              # the PR only adds
        git(repo.dir, 'checkout', '-q', 'main')
        main_tip = repo.commit({'theirs.py': 'x = 1\n'})                 # another PR, merged later, deletes y = 2
        git(repo.dir, 'checkout', '-q', '--detach', main_tip)
        git(repo.dir, 'merge', '-q', '--no-ff', '--no-edit', 'pr')       # what refs/pull/N/merge is
        self.assertEqual(DD.files_with_deletions(stale, cwd=repo.dir), ['theirs.py'])     # the bug
        anchor = DD.rolling_anchor(stale, cwd=repo.dir)
        self.assertEqual(anchor, main_tip)
        self.assertEqual(DD.files_with_deletions(anchor, cwd=repo.dir), [])               # only the PR's change

    def test_without_a_merge_commit_the_given_base_is_used(self):
        repo = Repo()
        base = repo.commit({'a.py': 'a\n'})
        repo.commit({'a.py': 'b\n'})
        self.assertEqual(DD.rolling_anchor(base, cwd=repo.dir), base)

    def test_the_workflow_takes_its_anchor_from_the_script(self):
        wf = (ROOT / '.github' / 'workflows' / 'identity.yml').read_text()
        self.assertIn('rolling="$(python3 scripts/deletions_declared.py --anchor "${PR_BASE:-}")"', wf)


class TheRealFile(unittest.TestCase):
    def test_the_path_only_entries_of_the_real_file_cover_nothing_new(self):
        allowed = json.loads((ROOT / 'docs' / 'identity' / 'allowed-deletions.json').read_text())['allowed']
        for path in allowed:
            _, undeclared, stale, _ = DD.judge(allowed, {path: DD.digest(['a line deleted by a future change'])})
            self.assertEqual((undeclared, len(stale)), ([], 1), path)

    def test_the_workflow_runs_this_script(self):
        wf = (ROOT / '.github' / 'workflows' / 'identity.yml').read_text()
        self.assertIn('python3 scripts/deletions_declared.py "$ANCHOR"', wf)
        self.assertNotIn('allowed.get(p)', wf)


if __name__ == '__main__':
    unittest.main()
