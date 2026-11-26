"""scripts/commit_resolved.sh: a conflict resolution is committed only after it is verified (the owner, 2026-11-15).

The trigger was #393: a resolution step failed and `git commit` ran anyway, with conflict markers left in
allowed-deletions.json. The script's exit codes are documented in docs/ops/conflict-commit.md.

Real path: the script itself, run by bash on a temporary git repository with a real merge conflict in two files (a JSON
file and a markdown file whose content has a `=======` rule of its own).
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'commit_resolved.sh'
RULE = 'Title\n=======\n'            # a markdown heading rule: a line of ======= that is NOT a conflict marker


def git(repo, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args], cwd=repo,
                          capture_output=True, text=True)


@unittest.skipUnless(shutil.which('bash') and shutil.which('git'), 'bash and git run the script')
class CommitResolved(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix='commit-resolved-'))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        git(self.repo, 'init', '-q', '-b', 'main')
        (self.repo / 'x.json').write_text('{"a": 1}\n', encoding='utf-8')
        (self.repo / 'r.md').write_text(RULE + 'base\n', encoding='utf-8')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-q', '-m', 'base')
        git(self.repo, 'checkout', '-q', '-b', 'other')
        (self.repo / 'x.json').write_text('{"a": 2}\n', encoding='utf-8')
        (self.repo / 'r.md').write_text(RULE + 'theirs\n', encoding='utf-8')
        git(self.repo, 'commit', '-q', '-am', 'other')
        git(self.repo, 'checkout', '-q', 'main')
        (self.repo / 'x.json').write_text('{"a": 3}\n', encoding='utf-8')
        (self.repo / 'r.md').write_text(RULE + 'ours\n', encoding='utf-8')
        git(self.repo, 'commit', '-q', '-am', 'ours')
        merge = git(self.repo, 'merge', '--no-edit', 'other')
        self.assertNotEqual(merge.returncode, 0)                       # a real conflict, in both files
        self.head = git(self.repo, 'rev-parse', 'HEAD').stdout.strip()

    def run_script(self, *args):
        return subprocess.run(['bash', str(SCRIPT), *args], capture_output=True, text=True,
                              env={'PATH': '/usr/bin:/bin:/usr/local/bin', 'HOME': str(self.repo),
                                   'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
                                   'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'})

    def committed(self):
        return git(self.repo, 'rev-parse', 'HEAD').stdout.strip() != self.head

    def test_no_worktree_is_a_usage_error(self):
        self.assertEqual(self.run_script().returncode, 2)

    def test_markers_left_refuse_the_commit_and_name_each_file(self):
        out = self.run_script(str(self.repo))
        self.assertEqual(out.returncode, 3)
        self.assertIn('::error title=conflict marker::r.md', out.stdout)
        self.assertIn('::error title=conflict marker::x.json', out.stdout)
        self.assertFalse(self.committed())

    def test_a_resolved_markdown_rule_is_not_a_marker_and_the_other_file_still_refuses(self):
        (self.repo / 'r.md').write_text(RULE + 'both\n', encoding='utf-8')
        out = self.run_script(str(self.repo))
        self.assertEqual(out.returncode, 3)
        self.assertNotIn('r.md', out.stdout)                          # its own ======= rule is not a marker
        self.assertIn('x.json', out.stdout)
        self.assertFalse(self.committed())

    def test_broken_json_refuses_the_commit(self):
        (self.repo / 'r.md').write_text(RULE + 'both\n', encoding='utf-8')
        (self.repo / 'x.json').write_text('{"a": 2,}\n', encoding='utf-8')
        out = self.run_script(str(self.repo))
        self.assertEqual(out.returncode, 4)
        self.assertIn('::error title=invalid json::x.json', out.stdout)
        self.assertFalse(self.committed())

    def test_a_verified_resolution_is_committed(self):
        (self.repo / 'r.md').write_text(RULE + 'both\n', encoding='utf-8')
        (self.repo / 'x.json').write_text('{"a": 5}\n', encoding='utf-8')
        out = self.run_script(str(self.repo))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('committed ', out.stdout)
        self.assertTrue(self.committed())
        self.assertEqual(json.loads((self.repo / 'x.json').read_text(encoding='utf-8')), {'a': 5})
        self.assertEqual(git(self.repo, 'status', '--porcelain').stdout.strip(), '')

    def test_a_json_file_the_resolution_deletes_is_committed_deleted(self):
        # 2026-11-26: main deleted SYSTEM_MAP.json (#536) while the sites bundle changed it; the resolution deletes it,
        # and the JSON check read the missing file and refused the commit as "invalid json" (exit 4)
        (self.repo / 'r.md').write_text(RULE + 'both\n', encoding='utf-8')
        git(self.repo, 'rm', '-q', 'x.json')
        out = self.run_script(str(self.repo))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn('invalid json', out.stdout)
        self.assertTrue(self.committed())
        self.assertFalse((self.repo / 'x.json').exists())
        self.assertNotIn('x.json', git(self.repo, 'ls-files').stdout.split())
        self.assertEqual(git(self.repo, 'status', '--porcelain').stdout.strip(), '')

    def test_the_exit_codes_are_the_documented_ones(self):
        doc = (SCRIPT.parents[1] / 'docs' / 'ops' / 'conflict-commit.md').read_text(encoding='utf-8')
        for code in ('| 0 |', '| 2 |', '| 3 |', '| 4 |', '| 5 |'):
            self.assertIn(code, doc)


if __name__ == '__main__':
    unittest.main()
