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


PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + bytes(range(256))      # NUL bytes: git calls it binary
TAR = b'\x1f\x8b\x08\x00' + bytes(range(255, -1, -1))


def commit_bytes(repo, files: dict, remove=()) -> str:
    for name, data in files.items():
        p = Path(repo.dir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name in remove:
        git(repo.dir, 'rm', '-q', name)
    git(repo.dir, 'add', '-A')
    git(repo.dir, 'commit', '-q', '-m', 'c')
    return git(repo.dir, 'rev-parse', 'HEAD')


class NoDeletingEvidence(unittest.TestCase):
    """Law 6 (audit 2026-11-25): numstat gives a binary "-" for its lines, so a deleted or rewritten image or archive
    under docs/evidence/ or smoke/ passed undeclared. Now it needs a declaration bound to the removed blob."""
    def setUp(self):
        self.repo = Repo()
        self.anchor = commit_bytes(self.repo, {'docs/evidence/shot.png': PNG, 'smoke/run.tar.gz': TAR, 't.py': b'a\n'})

    def blob(self, path):
        return git(self.repo.dir, 'rev-parse', f'{self.anchor}:{path}')

    def test_a_deleted_binary_evidence_file_fails_undeclared(self):
        commit_bytes(self.repo, {}, remove=['docs/evidence/shot.png'])
        self.assertEqual(DD.removed_binaries(self.anchor, cwd=self.repo.dir),
                         {'docs/evidence/shot.png': self.blob('docs/evidence/shot.png')})
        rc, out = run(self.repo, self.anchor, {})
        self.assertEqual(rc, 1, out)
        self.assertIn('::error title=no deleting evidence::binary docs/evidence/shot.png deleted or rewritten', out)

    def test_the_same_deletion_declared_by_its_blob_and_signed_passes(self):
        commit_bytes(self.repo, {}, remove=['docs/evidence/shot.png'])
        rc, out = run(self.repo, self.anchor, {'docs/evidence/shot.png': [
            {'reason': 'superseded screenshot', 'deleted_blob': self.blob('docs/evidence/shot.png'), **SIGNED}]})
        self.assertEqual(rc, 0, out)
        self.assertIn('::notice title=deletion (binary)::docs/evidence/shot.png: superseded screenshot', out)
        self.assertIn('1 binary file(s) deleted or rewritten', out)

    def test_a_rewritten_binary_needs_a_declaration_too(self):
        commit_bytes(self.repo, {'smoke/run.tar.gz': TAR + b'\x00more'})
        rc, out = run(self.repo, self.anchor, {})
        self.assertEqual(rc, 1, out)
        self.assertIn('binary smoke/run.tar.gz deleted or rewritten', out)
        rc, out = run(self.repo, self.anchor, {'smoke/run.tar.gz': {
            'reason': 'rerun archive', 'deleted_blob': self.blob('smoke/run.tar.gz'), **SIGNED}})
        self.assertEqual(rc, 0, out)

    def test_a_blob_declared_for_an_earlier_version_covers_nothing(self):
        version = Path(self.repo.dir) / 'v0.png'                           # an earlier version's blob, never committed
        version.write_bytes(PNG + b'v0')
        earlier = git(self.repo.dir, 'hash-object', str(version))
        version.unlink()
        commit_bytes(self.repo, {}, remove=['docs/evidence/shot.png'])
        rc, out = run(self.repo, self.anchor, {'docs/evidence/shot.png': {
            'reason': 'an earlier version', 'deleted_blob': earlier, **SIGNED}})
        self.assertEqual(rc, 1, out)
        self.assertIn('binary docs/evidence/shot.png (deleted', out)

    def test_a_line_digest_or_a_path_alone_covers_no_binary(self):
        commit_bytes(self.repo, {}, remove=['docs/evidence/shot.png'])
        for entry in ({'reason': 'digest of no lines', 'deleted_sha256': DD.digest([])},
                      {'reason': 'any change, forever'}):
            rc, out = run(self.repo, self.anchor, {'docs/evidence/shot.png': {**entry, **SIGNED}})
            self.assertEqual(rc, 1, (entry, out))

    def test_an_author_signed_binary_declaration_fails(self):
        commit_bytes(self.repo, {}, remove=['smoke/run.tar.gz'])
        rc, out = run(self.repo, self.anchor, {'smoke/run.tar.gz': {
            'reason': 'old run', 'deleted_blob': self.blob('smoke/run.tar.gz'),
            'author': 'codex', 'reviewer': 'codex', 'reviewed_at': '2026-11-25'}})
        self.assertEqual(rc, 1, out)
        self.assertIn('binary smoke/run.tar.gz: the declaration has no reviewer note', out)

    def test_an_added_binary_needs_nothing_and_a_moved_one_is_a_deletion(self):
        commit_bytes(self.repo, {'docs/evidence/new.png': PNG + b'new'})
        rc, out = run(self.repo, self.anchor, {})
        self.assertEqual(rc, 0, out)
        git(self.repo.dir, 'mv', 'docs/evidence/shot.png', 'docs/evidence/moved.png')
        commit_bytes(self.repo, {})
        self.assertEqual(list(DD.removed_binaries(self.anchor, cwd=self.repo.dir)), ['docs/evidence/shot.png'])

    def test_the_blob_helper_prints_what_to_declare_and_the_digest_helper_refuses_a_binary(self):
        commit_bytes(self.repo, {}, remove=['docs/evidence/shot.png'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            DD.main([self.anchor, '--blob', 'docs/evidence/shot.png'], cwd=self.repo.dir)
        self.assertEqual(out.getvalue().strip(), self.blob('docs/evidence/shot.png'))
        with self.assertRaisesRegex(SystemExit, 'is binary'):
            DD.main([self.anchor, '--digest', 'docs/evidence/shot.png'], cwd=self.repo.dir)


if __name__ == '__main__':
    unittest.main()
