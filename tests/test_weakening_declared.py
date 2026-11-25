"""Law 5, no test is weakened to get green (audit 2026-11-25). scripts/deletions_declared.py binds every DELETED line;
a weakening that only adds lines passed. Real path: a real git repository in a temp dir (main, a branch, GitHub's merge
commit where it matters) and the real script, scripts/weakening_declared.py, the code the light job of v24-ci.yml runs.

Every fixture line that weakens a test or a workflow is built by concatenation (the WEAK table below) and each kind is
named by its index in the script's own table (KINDS), never by its text, so no line of this file is itself an added
weakening when the script reads the branch that adds it (checked: the script on this branch reports 0)."""
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deletions_declared as DD  # noqa: E402
import weakening_declared as W  # noqa: E402

KINDS = [name for name, _ in W.WEAKENINGS]     # the names the script reports, in the order of its table
(MARK_SKIP, SKIP_CALL, SKIP_TEST, UNITTEST_SKIP, SKIP_IF, SKIP_UNLESS, XFAIL, EXPECTED_FAILURE, CONTINUE_ON_ERROR,
 OR_TRUE, OR_COLON, SET_E) = range(12)
WEAK = [   # one added line per kind, in that order: (file, line); each split so that this source line matches nothing
    ('tests/test_a.py', '@pytest.mark.' + 'skip(reason="flaky on CI")'),
    ('tests/test_a.py', '    pytest.' + 'skip("later")'),
    ('tests/test_a.py', '        self.skip' + 'Test("later")'),
    ('tests/test_a.py', '@unittest.' + 'skip("later")'),
    ('tests/test_a.py', '@skip' + 'If(True, "later")'),
    ('tests/test_a.py', '@skip' + 'Unless(False, "later")'),
    ('tests/test_a.py', '@pytest.mark.' + 'xfail(strict=False)'),
    ('tests/test_a.py', '@unittest.expected' + 'Failure'),
    ('.github/workflows/ci.yml', '        continue-on-' + 'error: true'),
    ('.github/workflows/ci.yml', '        run: python -m pytest -q |' + '| true'),
    ('.github/workflows/ci.yml', '        run: python -m pytest -q |' + '| :'),
    ('.github/workflows/ci.yml', '          set ' + '+e'),
]
TEST = 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n'
WORKFLOW = 'name: ci\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n'


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp()
        git(self.dir, 'init', '-q', '-b', 'main')
        git(self.dir, 'config', 'user.email', 't@example.com')
        git(self.dir, 'config', 'user.name', 't')

    def commit(self, files: dict, remove=()) -> str:
        for name, text in files.items():
            p = Path(self.dir) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        for name in remove:
            git(self.dir, 'rm', '-q', name)
        git(self.dir, 'add', '-A')
        git(self.dir, 'commit', '-q', '-m', 'c')
        return git(self.dir, 'rev-parse', 'HEAD')


def run(repo, anchor, weakening=None, declarations=None):
    decl = declarations or Path(repo.dir) / 'decl.json'
    if declarations is None:
        decl.write_text(json.dumps({'allowed': {}, 'weakening': weakening or {}}))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = W.main([anchor], cwd=repo.dir, declarations=decl)
    return rc, out.getvalue()


def errors(out):
    return [line for line in out.splitlines() if line.startswith('::error')]


SIGNED = {'author': 'claude', 'reviewer': 'shai', 'reviewed_at': '2026-11-25'}


def insert_after_first_line(text: str, line: str) -> str:
    head, rest = text.split('\n', 1)
    return f'{head}\n{line}\n{rest}'


class EachAddedWeakeningFails(unittest.TestCase):
    """One ::error per added line that weakens, with its file, line and the digest that would declare it."""
    def setUp(self):
        self.repo = Repo()
        self.anchor = self.repo.commit({'tests/test_a.py': TEST, '.github/workflows/ci.yml': WORKFLOW})

    def assert_caught(self, *kinds):
        self.assertEqual(len(WEAK), len(KINDS))                                  # one fixture per kind of the table
        for kind in kinds:
            with self.subTest(kind=KINDS[kind]):
                path, line = WEAK[kind]
                git(self.repo.dir, 'checkout', '-q', '-B', f'pr-{kind}', self.anchor)    # each kind on its own branch
                text = TEST if path.startswith('tests/') else WORKFLOW
                self.repo.commit({path: insert_after_first_line(text, line)})
                rc, out = run(self.repo, self.anchor)
                self.assertEqual(rc, 1, out)
                [error] = errors(out)
                self.assertIn(f'::error file={path},line=2,title=law 5 (weakening)::', error)
                self.assertIn(f'adds {KINDS[kind]}', error)
                self.assertIn(W.line_digest(path, line), error)

    def test_an_added_skip_marker_or_skip_call_fails(self):
        self.assert_caught(MARK_SKIP, SKIP_CALL, SKIP_TEST, UNITTEST_SKIP, SKIP_IF, SKIP_UNLESS)

    def test_an_added_xfail_or_expected_failure_fails(self):
        self.assert_caught(XFAIL, EXPECTED_FAILURE)

    def test_an_added_continue_on_error_fails(self):
        self.assert_caught(CONTINUE_ON_ERROR)

    def test_an_added_swallowed_exit_code_fails(self):
        self.assert_caught(OR_TRUE, OR_COLON, SET_E)

    def test_continue_on_error_false_and_a_plain_line_pass(self):
        self.repo.commit({'.github/workflows/ci.yml': WORKFLOW + '    continue-on-' + 'error: false\n',
                          'tests/test_a.py': TEST + '        self.assertEqual(1, 1)\n'})
        rc, out = run(self.repo, self.anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('2 line(s) added', out)
        self.assertIn('0 weakening(s)', out)

    def test_every_added_weakening_is_its_own_error(self):
        test_lines = [line for path, line in WEAK if path.startswith('tests/')]
        wf_lines = [line for path, line in WEAK if not path.startswith('tests/')]
        self.repo.commit({'tests/test_a.py': TEST + '\n'.join(test_lines) + '\n',
                          '.github/workflows/ci.yml': WORKFLOW + '\n'.join(wf_lines) + '\n'})
        rc, out = run(self.repo, self.anchor)
        self.assertEqual(rc, 1, out)
        self.assertEqual(len(errors(out)), len(WEAK), out)


class OnlyTheChangeIsRead(unittest.TestCase):
    def test_existing_weakenings_that_this_change_does_not_add_are_ignored(self):
        repo = Repo()
        skip_path, skip_line = WEAK[MARK_SKIP]
        wf_path, or_true = WEAK[OR_TRUE]
        anchor = repo.commit({skip_path: insert_after_first_line(TEST, skip_line),
                              wf_path: WORKFLOW + or_true + '\n'})
        repo.commit({skip_path: insert_after_first_line(TEST, skip_line) + '# a comment\n',
                     wf_path: '# ci\n' + WORKFLOW + or_true + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('2 line(s) added', out)

    def test_lines_outside_tests_and_workflows_are_not_read(self):
        repo = Repo()
        anchor = repo.commit({'scripts/run.sh': 'echo\n'})
        repo.commit({'scripts/run.sh': 'echo\n' + WEAK[OR_TRUE][1] + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('0 line(s) added', out)

    def test_measured_from_the_merge_base_when_main_moved_on(self):
        """main removes an old skip after the branch was cut. Diffed against main's tip the branch would 'add' it back;
        measured from the merge base (and from GitHub's merge commit) it adds only its own line."""
        repo = Repo()
        path, skip = WEAK[MARK_SKIP]
        repo.commit({path: insert_after_first_line(TEST, skip)})
        git(repo.dir, 'checkout', '-q', '-b', 'pr')
        repo.commit({'tests/test_b.py': TEST})                                      # the PR adds a plain test
        git(repo.dir, 'checkout', '-q', 'main')
        main_tip = repo.commit({path: TEST})                                        # main drops the old skip
        git(repo.dir, 'checkout', '-q', 'pr')
        rc, out = run(repo, main_tip)
        self.assertEqual(rc, 0, out)
        self.assertIn('6 line(s) added', out)
        git(repo.dir, 'checkout', '-q', '--detach', main_tip)
        git(repo.dir, 'merge', '-q', '--no-ff', '--no-edit', 'pr')                   # what refs/pull/N/merge is
        anchor = DD.rolling_anchor('', cwd=repo.dir)
        self.assertEqual(anchor, main_tip)
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('6 line(s) added', out)

    def test_a_content_line_that_looks_like_a_file_header_stays_in_its_file(self):
        repo = Repo()
        anchor = repo.commit({'tests/data.txt': 'a\n', '.github/workflows/ci.yml': WORKFLOW})
        or_true = WEAK[OR_TRUE][1]
        repo.commit({'tests/data.txt': 'a\n++ b/.github/workflows/ci.yml\n' + or_true + '\n'})   # '+++ b/...' in the diff
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('::error file=tests/data.txt,line=3,', error)
        self.assertIn(W.line_digest('tests/data.txt', or_true), error)


class DeclaredAndSigned(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.anchor = self.repo.commit({'tests/test_a.py': TEST, 'tests/test_b.py': TEST})
        self.path, self.line = WEAK[SKIP_UNLESS]
        self.repo.commit({self.path: insert_after_first_line(TEST, self.line)})
        self.digest = W.line_digest(self.path, self.line)

    def test_the_exact_line_declared_and_signed_passes(self):
        rc, out = run(self.repo, self.anchor, {self.path: [
            {'reason': 'needs a real Postgres', 'line_sha256': self.digest, 'pr': 'x', **SIGNED}]})
        self.assertEqual(rc, 0, out)
        self.assertIn(f'::notice title=weakening declared::tests/test_a.py:2 adds {KINDS[SKIP_UNLESS]}', out)
        self.assertIn('1 weakening(s), each declared and signed', out)

    def test_an_author_signed_or_unsigned_declaration_fails(self):
        for who in ({'author': 'codex', 'reviewer': 'codex'}, {'author': 'codex', 'reviewer': 'claude'},
                    {'author': 'claude', 'reviewer': 'pending'}, {'author': 'claude', 'reviewer': ''}):
            with self.subTest(**who):
                rc, out = run(self.repo, self.anchor, {self.path: {
                    'reason': 'needs a real Postgres', 'line_sha256': self.digest, **who}})
                self.assertEqual(rc, 1, out)
                self.assertIn('declared but not signed by a reviewer other than the author', out)

    def test_a_declaration_binds_its_path_and_its_exact_line(self):
        other = W.line_digest('tests/test_b.py', self.line)                         # the same line, another file
        near = W.line_digest(self.path, self.line + ' ')                            # another line, this file
        for path, digest in (('tests/test_b.py', other), (self.path, other), (self.path, near)):
            with self.subTest(path=path, digest=digest[:8]):
                rc, out = run(self.repo, self.anchor, {path: {'reason': 'r', 'line_sha256': digest, **SIGNED}})
                self.assertEqual(rc, 1, out)
                self.assertIn('-- not declared', out)

    def test_a_declaration_without_a_reason_covers_nothing(self):
        rc, out = run(self.repo, self.anchor, {self.path: {'line_sha256': self.digest, **SIGNED}})
        self.assertEqual(rc, 1, out)


class NeverAPassUnmeasured(unittest.TestCase):
    def test_an_unknown_anchor_or_no_repository_is_an_error(self):
        repo = Repo()
        repo.commit({'tests/test_a.py': TEST})
        rc, out = run(repo, 'no-such-commit')
        self.assertEqual(rc, 2, out)
        self.assertIn('::error title=law 5 (weakening)::nothing measured, which is never a pass', out)
        empty = tempfile.mkdtemp()
        decl = Path(empty) / 'decl.json'
        decl.write_text('{"weakening": {}}')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(W.main(['HEAD'], cwd=empty, declarations=decl), 2)

    def test_two_readings_of_git_that_disagree_are_an_error(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        repo.commit({'tests/test_a.py': TEST + 'x = 1\n'})
        base = W.merge_base(anchor, cwd=repo.dir)
        self.assertEqual(W.measured(base, cwd=repo.dir), [('tests/test_a.py', 7, 'x = 1')])
        with mock.patch.object(W, 'added_counts', return_value={'tests/test_a.py': 2}):
            with self.assertRaisesRegex(W.Unreadable, 'disagree'):
                W.measured(base, cwd=repo.dir)

    def test_an_unreadable_declarations_file_is_an_error(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        decl = Path(repo.dir) / 'decl.json'
        for text in ('{"weakening": [1]}', '{not json'):
            with self.subTest(text=text):
                decl.write_text(text)
                rc, out = run(repo, anchor, declarations=decl)
                self.assertEqual(rc, 2, out)


class TheRealFileAndTheLightJob(unittest.TestCase):
    def test_the_declarations_file_holds_a_weakening_map_and_each_entry_is_signed(self):
        data = json.loads((ROOT / 'docs' / 'identity' / 'allowed-deletions.json').read_text(encoding='utf-8'))
        self.assertIsInstance(data['weakening'], dict)
        self.assertIn('weakening', data['rule_weakening'])
        for path, value in data['weakening'].items():
            for entry in DD.entries_for(data['weakening'], path):
                with self.subTest(path=path):
                    self.assertRegex(entry.get('line_sha256', ''), r'^[0-9a-f]{64}$')
                    self.assertTrue(entry.get('reason'))
                    who = str(entry.get('reviewer') or '').strip()
                    self.assertNotIn(who.lower(), DD._NOT_A_REVIEWER)
                    self.assertNotEqual(who, entry.get('author'))

    def test_the_light_job_runs_both_scripts_and_their_exit_codes_decide(self):
        wf = yaml.safe_load((ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8'))
        steps = wf['jobs']['light']['steps']
        runs = [s.get('run', '') for s in steps]
        [deletions] = [i for i, r in enumerate(runs) if 'deletions_declared.py "$anchor"' in r]
        [weakening] = [i for i, r in enumerate(runs) if 'weakening_declared.py' in r]
        self.assertEqual(weakening, deletions + 1)                                    # next to the deletion step
        self.assertTrue(runs[deletions].rstrip().endswith('python3 scripts/deletions_declared.py "$anchor"'))
        step = steps[weakening]
        self.assertTrue(step['run'].rstrip().endswith('python3 scripts/weakening_declared.py "$anchor"'))
        self.assertIn('set -euo pipefail', step['run'])
        self.assertIn('anchor="$(python3 scripts/deletions_declared.py --anchor "${PR_BASE:-}")"', step['run'])
        self.assertEqual(step['env']['PR_BASE'], '${{ github.event.pull_request.base.sha }}')
        for s in (steps[deletions], step):
            self.assertNotIn('if', s)
            self.assertNotIn('continue-on-error', s)
        self.assertEqual([n for n, rx in W.WEAKENINGS if any(rx.search(line) for line in step['run'].splitlines())], [])

    def test_the_checkout_of_the_light_job_has_the_history_the_merge_base_needs(self):
        [checkout] = [s for s in yaml.safe_load((ROOT / '.github/workflows/v24-ci.yml').read_text())['jobs']['light']
                      ['steps'] if str(s.get('uses', '')).startswith('actions/checkout')]
        self.assertEqual(checkout['with']['fetch-depth'], 0)
        self.assertNotIn('ref', checkout['with'])                    # GitHub's merge commit: the rolling anchor


if __name__ == '__main__':
    unittest.main()
