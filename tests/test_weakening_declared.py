"""Law 5, no test is weakened to get green (audit 2026-11-25; review fixes 2026-11-25). scripts/deletions_declared.py
binds every DELETED line; a weakening that only adds lines passed. Real path: a real git repository in a temp dir (main,
a branch, GitHub's merge commit where it matters) and the real script, scripts/weakening_declared.py, the code the light
job of v24-ci.yml runs.

Every spelling the script reads is its own test (EverySpellingIsRead, one shared repository run once), so narrowing any
one pattern fails exactly that test. Every fixture line is a string literal here, and the script reads a .py file in
code only, so no line of this file is itself an added weakening (checked: the script on this branch reports 0)."""
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

TEST = 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n'
WORKFLOW = 'name: ci\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n'
DECOR = ('import unittest\n\nimport pytest\n\n\n{}\nclass T(unittest.TestCase):\n    def test_x(self):\n'
         '        self.assertTrue(True)\n')
BODY = ('import unittest\n\nimport pytest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n{}\n'
        '        self.assertTrue(True)\n')
SIGNED = {'author': 'claude', 'reviewer': 'shai', 'reviewed_at': '2026-11-25',
          'signature_note': 'the owner instructed this signature on 2026-11-25'}
OR_TRUE = '        run: docker rm -f old || true'
SKIP_UNLESS = '@unittest.skipUnless(False, "needs a real Postgres")'
PIXEL = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\n'
THREE = '      - run: echo two\n      - run: echo three\n      - run: echo four\n'


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp()
        git(self.dir, 'init', '-q', '-b', 'main')
        git(self.dir, 'config', 'user.email', 't@example.com')
        git(self.dir, 'config', 'user.name', 't')
        (Path(self.dir) / '.git' / 'info' / 'exclude').write_text('decl.json\n')   # committed only when asked
        self.decl = Path(self.dir) / 'decl.json'

    def commit(self, files: dict, remove=(), declarations=None) -> str:
        for name, text in files.items():
            p = Path(self.dir) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text) if isinstance(text, bytes) else p.write_text(text)
        for name in remove:
            git(self.dir, 'rm', '-q', name)
        if declarations is not None:
            self.decl.write_text(json.dumps({'allowed': {}, 'weakening': declarations}))
            git(self.dir, 'add', '-f', 'decl.json')
        git(self.dir, 'add', '-A')
        git(self.dir, 'commit', '-q', '-m', 'c')
        return git(self.dir, 'rev-parse', 'HEAD')


def run(repo, anchor, weakening=None):
    """weakening None: the declarations file as it is (written empty when there is none)."""
    if weakening is not None or not repo.decl.exists():
        repo.decl.write_text(json.dumps({'allowed': {}, 'weakening': weakening or {}}))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = W.main([anchor], cwd=repo.dir, declarations=repo.decl)
    return rc, out.getvalue()


def errors(out):
    return [line for line in out.splitlines() if line.startswith('::error')]


_ERROR = re.compile(r'^::error file=([^,]+)(?:,line=\d+)?,title=law 5 \(weakening\)::(.*)$')


def flagged_by_path(out) -> dict:
    """path -> {digest: [kind names]} of every not-declared ::error."""
    found = {}
    for line in errors(out):
        m = _ERROR.match(line)
        digest = re.search(r'"line_sha256": "([0-9a-f]{64})"', m.group(2))
        names = re.search(r' adds (.+?) \(\d+ net new\)', m.group(2))
        found.setdefault(m.group(1), {})[digest.group(1)] = names.group(1).split(', ')
    return found


def insert_after_first_line(text: str, line: str) -> str:
    head, rest = text.split('\n', 1)
    return f'{head}\n{line}\n{rest}'


# ---- the spelling matrix: one repository, one run --------------------------------------------------------------------
ALIAS_BASE = ('import shutil\nimport unittest\n\nneeds_node = unittest.skipUnless(shutil.which("node"), "node")\n\n\n'
              'class T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n')
ANCHOR_FILES = {
    'tests/test_a.py': TEST,
    'tests/test_alias.py': ALIAS_BASE,
    '.github/workflows/ci.yml': WORKFLOW,
    'tests/conftest.py': '"""conftest."""\n\n\ndef pytest_configure(config):\n    pass\n',
    'pytest.ini': '[pytest]\nmarkers =\n    slow: slow\n',
    'pyproject.toml': '[project]\nname = "x"\n',
    'scripts/test_fast.sh': '#!/bin/bash\nset -euo pipefail\npython3 -m pytest -q tests\n',
    'tests/needs_env.txt': '# measured\ntests/test_x.py\n',
}
# id -> (path, file text in HEAD, the lines that must be flagged, the kind each is reported as)
SPELLINGS = {}


def _py(sid, template, line, kind):
    SPELLINGS[sid] = (f'tests/test_s_{sid}.py', template.format(line), [line], kind)


def _wf(sid, line, kind):
    SPELLINGS[sid] = (f'.github/workflows/s_{sid}.yml', WORKFLOW + line + '\n', [line], kind)


def _js(sid, line, kind):
    SPELLINGS[sid] = (f'tests/s_{sid}.cjs', "const test = require('node:test');\n" + line + '\n', [line], kind)


_py('mark_skip', DECOR, '@pytest.mark.skip(reason="later")', 'pytest.mark.skip')
_py('mark_skipif', DECOR, '@pytest.mark.skipif(True, reason="later")', 'pytest.mark.skip')
_py('mark_skip_from_import', DECOR, '@mark.skip', 'pytest.mark.skip')
_py('pytest_skip_call', BODY, '        pytest.skip("later")', 'pytest.skip(')
_py('skip_test_call', BODY, '        self.skipTest("later")', 'skipTest(')
_py('unittest_skip', DECOR, '@unittest.skip("later")', 'unittest.skip')
_py('unittest_skip_if', DECOR, '@unittest.skipIf(True, "later")', 'unittest.skip')
_py('skip_if', DECOR, '@skipIf(True, "later")', 'skipIf(')
_py('skip_unless', DECOR, '@skipUnless(False, "later")', 'skipUnless(')
_py('mark_xfail', DECOR, '@pytest.mark.xfail(strict=False)', 'pytest.mark.xfail')
_py('pytest_xfail_call', BODY, '        pytest.xfail("later")', 'pytest.mark.xfail')
_py('expected_failure', DECOR, '@unittest.expectedFailure', 'expectedFailure')
_py('raise_unittest_skiptest', BODY, '        raise unittest.SkipTest("later")', 'SkipTest')
_py('raise_bare_skiptest', BODY, '        raise SkipTest("later")', 'SkipTest')
_py('raise_skiptest_class', BODY, '        raise unittest.SkipTest', 'SkipTest')
_py('skiptest_built_not_raised', BODY, '        error = SkipTest("later")', 'SkipTest')
_py('importorskip', 'import pytest\n\n{}\n', 'fastapi = pytest.importorskip("fastapi")', 'importorskip(')
_py('bare_skip_decorator', 'from unittest import TestCase\n\n\n{}\nclass T(TestCase):\n    pass\n', '@skip', 'bare skip')
_py('bare_skip_call', BODY, '        skip("later")', 'bare skip')
SPELLINGS['alias_assigned'] = ('tests/test_alias.py', ALIAS_BASE + '\n    @needs_node\n    def test_y(self):\n'
                               '        self.assertTrue(True)\n', ['    @needs_node'], W.ALIAS)
_py('alias_imported', 'from unittest import skipUnless as when\n\n\n{}\nclass T:\n    pass\n', '@when(False, "later")',
    W.ALIAS)
_wf('continue_on_error', '        continue-on-error: true', 'continue-on-error')
_wf('continue_on_error_single_quoted_key', "        'continue-on-error': true", 'continue-on-error')
_wf('continue_on_error_double_quoted_key', '        "continue-on-error": true', 'continue-on-error')
_wf('continue_on_error_expression', '        continue-on-error: ${{ matrix.experimental }}', 'continue-on-error')
_wf('or_true', '        run: python -m pytest -q || true', '|| true')
_wf('or_true_in_a_subshell', '        run: n=$(grep -c error log.txt || true)', '|| true')
_wf('or_bin_true', '        run: python -m pytest -q || /bin/true', '|| true')
_wf('or_colon', '        run: python -m pytest -q || :', '|| :')
_wf('set_e', '          set +e', 'set +e')
_wf('set_eux', '          set +eux', 'set +e')
_wf('set_o_errexit', '          set +o errexit', 'set +e')
_wf('or_echo', '        run: python -m pytest -q || echo "::notice::measured"', '|| echo')
_wf('or_exit_0', '        run: python -m pytest -q || exit 0', '|| exit 0')
_wf('if_false', '        if: false', 'if: false')
_wf('if_false_expression', '        if: ${{ false }}', 'if: false')
_wf('python_kind_in_a_workflow', "        run: python -c 'import pytest; pytest.skip(\"x\")'", 'pytest.skip(')
_js('js_skip', "test.skip('later', () => {});", '.skip(')
_js('js_xit', "xit('later', () => {});", 'xit(')
_js('js_xdescribe', "xdescribe('later', () => {});", 'xdescribe(')
# the files that decide what runs: every added line that holds something is a weakening of its own kind
SPELLINGS['conftest_in_tests'] = ('tests/conftest.py', ANCHOR_FILES['tests/conftest.py']
                                  + '\n# a comment\n"""a string only."""\ncollect_ignore = ["test_a.py"]\n',
                                  ['collect_ignore = ["test_a.py"]'], W.CONFTEST)
SPELLINGS['conftest_at_the_root'] = ('conftest.py', 'def pytest_ignore_collect(collection_path, config):\n'
                                     '    return True\n', ['def pytest_ignore_collect(collection_path, config):',
                                                           '    return True'], W.CONFTEST)
SPELLINGS['pytest_ini'] = ('pytest.ini', ANCHOR_FILES['pytest.ini'] + 'addopts = --deselect tests/test_a.py::T::test_x\n',
                           ['addopts = --deselect tests/test_a.py::T::test_x'], W.PYTEST_SETTING)
SPELLINGS['pyproject_toml'] = ('pyproject.toml', '[project]\nname = "x"\nversion = "1"\n\n[tool.pytest.ini_options]\n'
                               'addopts = "-k not_slow"\n', ['[tool.pytest.ini_options]', 'addopts = "-k not_slow"'],
                               W.PYTEST_SETTING)
SPELLINGS['setup_cfg'] = ('setup.cfg', '[metadata]\nname = x\n\n[tool:pytest]\naddopts = -p no:cacheprovider\n',
                          ['[tool:pytest]', 'addopts = -p no:cacheprovider'], W.PYTEST_SETTING)
SPELLINGS['tox_ini'] = ('tox.ini', '[tox]\nenvlist = py312\n\n[pytest]\n; a comment\naddopts = --ignore=tests/test_a.py\n',
                        ['[pytest]', 'addopts = --ignore=tests/test_a.py'], W.PYTEST_SETTING)
SPELLINGS['fast_suite_script'] = ('scripts/test_fast.sh', ANCHOR_FILES['scripts/test_fast.sh'] + '# a comment\nexit 0\n',
                                  ['exit 0'], W.RUNS['scripts/test_fast.sh'])
SPELLINGS['needs_env_entry'] = ('tests/needs_env.txt', ANCHOR_FILES['tests/needs_env.txt']
                                + '# another comment\ntests/test_a.py::T::test_x\n', ['tests/test_a.py::T::test_x'],
                                W.RUNS['tests/needs_env.txt'])
# lines that only name a pattern, or are no weakening: never flagged
QUIET = {
    'tests/test_mentions.py': ('"""pytest.mark.skip and self.skipTest() are named here, never used."""\nimport unittest\n\n'
                               'FORBIDDEN = (\'@unittest.skip("x")\', "pytest.skip(", \'raise unittest.SkipTest(\')\n\n\n'
                               'class T(unittest.TestCase):\n    def test_x(self):\n'
                               '        # self.skipTest("never") is not called\n        text = """\n@pytest.mark.xfail\n'
                               '"""\n        self.assertNotIn(f"{text}skipTest(", text)\n'),
    '.github/workflows/s_comment.yml': WORKFLOW + '          # a failure is never swallowed with || true or set +e here\n',
    '.github/workflows/s_false.yml': WORKFLOW + '        continue-on-error: false\n'
                                     '      - {name: t, run: echo, continue-on-error: false}\n',
    'tests/negative_controls/s_spec.json': '{"new": "        run: pytest || true"}\n',
}
BROKEN = ('tests/test_s_broken.py', 'x = """never closed\n@unittest.skip("x")\n', '@unittest.skip("x")')
BESIDE_SPECS = ('tests/negative_controls/test_s_beside.py', DECOR.format('@unittest.skip("later")'),
                '@unittest.skip("later")')
_SHARED = {}


def shared_run():
    if not _SHARED:
        repo = Repo()
        anchor = repo.commit(ANCHOR_FILES)
        head = {path: text for path, text, _, _ in SPELLINGS.values()}
        head.update(QUIET)
        head.update({BROKEN[0]: BROKEN[1], BESIDE_SPECS[0]: BESIDE_SPECS[1]})
        repo.commit(head)
        rc, out = run(repo, anchor)
        _SHARED.update(rc=rc, out=out, flagged=flagged_by_path(out))
    return _SHARED


class EverySpellingIsRead(unittest.TestCase):
    """One test per spelling (generated below): its file holds exactly the expected flagged lines, each reported with
    its kind and the digest that would declare it."""
    def assert_flagged(self, path, lines, kind):
        found = shared_run()['flagged'].get(path, {})
        self.assertEqual(sorted(found), sorted(W.line_digest(path, line) for line in lines), shared_run()['out'])
        for names in found.values():
            self.assertIn(kind, names)

    def test_the_run_fails_and_reads_every_file(self):
        shared = shared_run()
        self.assertEqual(shared['rc'], 1, shared['out'])
        self.assertEqual(len(SPELLINGS), 48)

    def test_python_mentions_in_strings_comments_and_docstrings_are_not_read(self):
        self.assertNotIn('tests/test_mentions.py', shared_run()['flagged'])

    def test_a_workflow_comment_only_line_is_not_read(self):
        self.assertNotIn('.github/workflows/s_comment.yml', shared_run()['flagged'])

    def test_continue_on_error_false_is_no_weakening_in_block_or_flow_style(self):
        self.assertNotIn('.github/workflows/s_false.yml', shared_run()['flagged'])

    def test_a_python_file_that_does_not_tokenize_is_read_as_raw_text(self):
        path, _, line = BROKEN
        self.assert_flagged(path, [line], 'unittest.skip')
        self.assertIn(f'::notice title=law 5 (weakening)::{path} at ', shared_run()['out'])
        self.assertIn('does not tokenize: read as raw text', shared_run()['out'])

    def test_negative_control_specs_are_not_read_but_a_test_beside_them_is(self):
        self.assertNotIn('tests/negative_controls/s_spec.json', shared_run()['flagged'])
        path, _, line = BESIDE_SPECS
        self.assert_flagged(path, [line], 'unittest.skip')


def _spelling_test(path, lines, kind):
    def test(self):
        self.assert_flagged(path, lines, kind)
    return test


for _sid, (_path, _text, _lines, _kind) in SPELLINGS.items():
    setattr(EverySpellingIsRead, f'test_spelling_{_sid}', _spelling_test(_path, _lines, _kind))


# ---- behaviour, each on its own small repository ---------------------------------------------------------------------
class OnlyTheChangeIsRead(unittest.TestCase):
    def test_existing_weakenings_that_this_change_does_not_add_are_ignored(self):
        repo = Repo()
        skip_line = '@pytest.mark.skip(reason="flaky on CI")'
        anchor = repo.commit({'tests/test_a.py': insert_after_first_line(TEST, skip_line),
                              '.github/workflows/ci.yml': WORKFLOW + OR_TRUE + '\n'})
        repo.commit({'tests/test_a.py': insert_after_first_line(TEST, skip_line) + '# a comment\n',
                     '.github/workflows/ci.yml': '# ci\n' + WORKFLOW + OR_TRUE + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('2 line(s) added', out)

    def test_lines_outside_the_files_law_5_reads_are_not_read(self):
        repo = Repo()
        anchor = repo.commit({'scripts/run.sh': 'echo\n'})
        repo.commit({'scripts/run.sh': 'echo\n' + OR_TRUE + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('0 line(s) added', out)

    def test_measured_from_the_merge_base_when_main_moved_on(self):
        """main removes an old skip after the branch was cut. Diffed against main's tip the branch would 'add' it back;
        measured from the merge base (and from GitHub's merge commit) it adds only its own line."""
        repo = Repo()
        path, skip_line = 'tests/test_a.py', '@pytest.mark.skip(reason="flaky on CI")'
        repo.commit({path: insert_after_first_line(TEST, skip_line)})
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
        repo.commit({'tests/data.txt': 'a\n++ b/.github/workflows/ci.yml\n' + OR_TRUE + '\n'})   # '+++ b/...' in the diff
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('::error file=tests/data.txt,line=3,', error)
        self.assertIn(W.line_digest('tests/data.txt', OR_TRUE), error)


class NetNewOnly(unittest.TestCase):
    """Item 2: per (path, text), the flagged occurrences added minus those deleted from the same file."""
    def test_a_flagged_line_moved_within_its_file_adds_nothing(self):
        repo = Repo()
        anchor = repo.commit({'.github/workflows/ci.yml': WORKFLOW + OR_TRUE + '\n' + THREE})
        repo.commit({'.github/workflows/ci.yml': WORKFLOW + THREE + OR_TRUE + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('1 line(s) added', out)                   # git moves the flagged line itself: -1 +1
        self.assertIn('0 weakening(s)', out)

    def test_one_deleted_and_two_added_is_one_net_new(self):
        repo = Repo()
        anchor = repo.commit({'.github/workflows/ci.yml': WORKFLOW + OR_TRUE + '\n' + THREE})
        repo.commit({'.github/workflows/ci.yml': WORKFLOW + THREE + OR_TRUE + '\n' + OR_TRUE + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('(1 net new)', error)
        self.assertIn('"count": 1', error)
        digest = W.line_digest('.github/workflows/ci.yml', OR_TRUE)
        rc, out = run(repo, anchor, {'.github/workflows/ci.yml': [{'line_sha256': digest, 'reason': 'r', **SIGNED}]})
        self.assertEqual(rc, 0, out)

    def test_an_edited_flagged_line_is_a_new_text_and_counts(self):
        repo = Repo()
        anchor = repo.commit({'.github/workflows/ci.yml': WORKFLOW + OR_TRUE + '\n'})
        repo.commit({'.github/workflows/ci.yml': WORKFLOW + OR_TRUE.replace('old', 'new') + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        self.assertEqual(len(errors(out)), 1, out)

    def test_a_flagged_line_moved_to_another_file_is_new_there(self):
        repo = Repo()
        anchor = repo.commit({'.github/workflows/ci.yml': WORKFLOW + OR_TRUE + '\n', '.github/workflows/b.yml': WORKFLOW})
        repo.commit({'.github/workflows/ci.yml': WORKFLOW, '.github/workflows/b.yml': WORKFLOW + OR_TRUE + '\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('::error file=.github/workflows/b.yml,', error)

    def test_a_renamed_file_keeps_its_lines(self):
        repo = Repo()
        text = insert_after_first_line(TEST * 3, SKIP_UNLESS)
        anchor = repo.commit({'tests/test_a.py': text})
        repo.commit({'tests/test_b.py': text + 'x = 1\n'}, remove=['tests/test_a.py'])
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 0, out)
        self.assertIn('1 line(s) added', out)


class OneChangeOnly(unittest.TestCase):
    """Item 1: a record covers one change. Only records absent at the merge base count, and their counts add up to
    exactly the net-new occurrences."""
    def setUp(self):
        self.repo = Repo()
        self.anchor = self.repo.commit({'tests/test_a.py': TEST, 'tests/test_b.py': TEST})
        self.path, self.digest = 'tests/test_a.py', W.line_digest('tests/test_a.py', SKIP_UNLESS)

    def record(self, **extra):
        return {'reason': 'needs a real Postgres', 'line_sha256': self.digest, 'pr': 'x', **SIGNED, **extra}

    def test_the_exact_line_declared_and_signed_passes(self):
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS)})
        rc, out = run(self.repo, self.anchor, {self.path: [self.record()]})
        self.assertEqual(rc, 0, out)
        self.assertIn('::notice title=weakening declared::tests/test_a.py:2 adds unittest.skip, skipUnless(', out)
        self.assertIn('1 weakening(s) (1 occurrence(s)), each declared for this change and signed', out)

    def test_a_record_kept_from_an_earlier_change_covers_nothing(self):
        first = self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS)},
                                 declarations={self.path: [self.record()]})
        rc, out = run(self.repo, self.anchor)                            # the first change: its record is new
        self.assertEqual(rc, 0, out)
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS) + SKIP_UNLESS + '\nclass U:\n    pass\n'})
        rc, out = run(self.repo, first)                                  # a later change, the record unchanged
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('-- not declared for this change', error)
        rc, out = run(self.repo, first, {self.path: [self.record(), self.record(pr='y')]})   # its own new record
        self.assertEqual(rc, 0, out)
        rc, out = run(self.repo, first, {self.path: [self.record(), self.record()]})   # an exact copy is a new record too
        self.assertEqual(rc, 0, out)

    def test_identical_lines_need_their_exact_count(self):
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS) + SKIP_UNLESS + '\nclass U:\n    pass\n'})
        for records, rc_expected in (([self.record()], 1), ([self.record(count=3)], 1), ([self.record(count=2)], 0),
                                     ([self.record(), self.record(pr='y')], 0)):
            with self.subTest(counts=[r.get('count', 1) for r in records]):
                rc, out = run(self.repo, self.anchor, {self.path: records})
                self.assertEqual(rc, rc_expected, out)
                if rc_expected:
                    self.assertIn('-- the new record(s) declare count', out)

    def test_the_error_says_how_to_declare(self):
        """Item 10: the key, the path, the digest and the count."""
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS) + SKIP_UNLESS + '\nclass U:\n    pass\n'})
        rc, out = run(self.repo, self.anchor)
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn(f'::error file={self.path},line=2,title=law 5 (weakening)::', error)
        self.assertIn(f'under "weakening" -> "{self.path}": {{"line_sha256": "{self.digest}", "count": 2,', error)
        self.assertIn('"signature_note"', error)

    def test_a_new_record_that_covers_nothing_is_an_error(self):
        self.repo.commit({self.path: TEST + 'x = 1\n'})
        rc, out = run(self.repo, self.anchor, {self.path: [self.record()]})
        self.assertEqual(rc, 1, out)
        [error] = errors(out)
        self.assertIn('::error file=docs/identity/allowed-deletions.json,title=law 5 (weakening)::', error)
        self.assertIn('covers no weakening this change adds', error)

    def test_a_count_that_is_not_a_whole_number_fails(self):
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS)})
        for count in (0, -1, '1', True, 1.0):
            with self.subTest(count=count):
                rc, out = run(self.repo, self.anchor, {self.path: [self.record(count=count)]})
                self.assertEqual(rc, 1, out)
                self.assertIn('is not a whole number of at least 1', out)

    def test_a_declaration_binds_its_path_and_its_exact_line(self):
        self.repo.commit({self.path: insert_after_first_line(TEST, SKIP_UNLESS)})
        other = W.line_digest('tests/test_b.py', SKIP_UNLESS)                       # the same line, another file
        near = W.line_digest(self.path, SKIP_UNLESS + ' ')                          # another line, this file
        for path, digest in (('tests/test_b.py', other), (self.path, other), (self.path, near)):
            with self.subTest(path=path, digest=digest[:8]):
                rc, out = run(self.repo, self.anchor, {path: [self.record(line_sha256=digest)]})
                self.assertEqual(rc, 1, out)
                self.assertIn('-- not declared for this change', out)


class SignedByAnotherHand(unittest.TestCase):
    """Item 7: author required; the reviewer's identity is not the author's (case-insensitive); an agent writing a
    person's name records the instruction in signature_note (CLAUDE.md section 8)."""
    def setUp(self):
        self.repo = Repo()
        self.anchor = self.repo.commit({'tests/test_a.py': TEST})
        self.repo.commit({'tests/test_a.py': insert_after_first_line(TEST, SKIP_UNLESS)})
        self.digest = W.line_digest('tests/test_a.py', SKIP_UNLESS)

    def judge(self, **who):
        return run(self.repo, self.anchor, {'tests/test_a.py': [{'line_sha256': self.digest, **who}]})

    def assert_refused(self, problem, **who):
        rc, out = self.judge(**who)
        self.assertEqual(rc, 1, out)
        self.assertIn('-- declared but not signed: ', out)
        self.assertIn(problem, out)

    def test_signed_records_pass(self):
        for who in ({'author': 'claude', 'reviewer': 'shai', 'signature_note': 'instructed 2026-11-25'},
                    {'author': 'claude', 'reviewer': 'codex'}, {'author': 'shai', 'reviewer': 'michael'}):
            with self.subTest(**who):
                rc, out = self.judge(reason='r', **who)
                self.assertEqual(rc, 0, out)

    def test_a_record_without_an_author_fails(self):
        self.assert_refused('no author', reason='r', reviewer='x')

    def test_a_record_without_a_reason_fails(self):
        self.assert_refused('no reason', author='codex', reviewer='shai', signature_note='n')

    def test_the_author_signing_under_another_case_fails(self):
        self.assert_refused('reviewer codex is the author Codex', reason='r', author='Codex', reviewer='codex')

    def test_the_author_signing_under_another_spelling_fails(self):
        self.assert_refused('reviewer Codex Review is the author codex', reason='r', author='codex',
                            reviewer='Codex Review')

    def test_no_reviewer_or_a_placeholder_fails(self):
        for reviewer in ('', 'pending', 'Claude Code', 'AUTHOR'):
            with self.subTest(reviewer=reviewer):
                self.assert_refused('is not a reviewer', reason='r', author='codex', reviewer=reviewer)

    def test_an_agent_writing_a_persons_name_needs_a_signature_note(self):
        for reviewer in ('shai', 'Shai Nissim Ohana', 'michael'):
            with self.subTest(reviewer=reviewer):
                self.assert_refused('with no signature_note', reason='r', author='claude', reviewer=reviewer,
                                    signature_note=' ')


class NothingUnmeasuredPasses(unittest.TestCase):
    """Item 6, and every other way nothing is measured: exit 2, or the lines are read after all."""
    def test_a_gitattributes_binary_or_minus_diff_hides_nothing(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        coe = '        continue-on-error: true'
        repo.commit({'.gitattributes': 'tests/test_a.py -diff\ntests/test_b.py -diff\n.github/workflows/new.yml binary\n',
                     'tests/test_a.py': insert_after_first_line(TEST, SKIP_UNLESS),
                     'tests/test_b.py': DECOR.format('@unittest.skip("later")'),
                     '.github/workflows/new.yml': WORKFLOW + coe + '\n',
                     'tests/fixtures/pixel.png': PIXEL})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        self.assertEqual(sorted(flagged_by_path(out)), ['.github/workflows/new.yml', 'tests/test_a.py', 'tests/test_b.py'])

    def test_a_binary_file_with_a_nul_byte_is_read_and_checked_against_its_blobs(self):
        repo = Repo()
        anchor = repo.commit({'tests/fixtures/pixel.png': PIXEL, 'tests/fixtures/old.png': PIXEL + b'x\n'})
        repo.commit({'tests/fixtures/pixel.png': PIXEL + b'@unittest.skip("x")\n', 'tests/fixtures/new.png': PIXEL + b'x\n'},
                    remove=['tests/fixtures/old.png'])                            # a binary edited, a binary renamed
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        self.assertEqual(list(flagged_by_path(out)), ['tests/fixtures/pixel.png'])

    def test_a_text_file_in_another_encoding_is_read_never_unmeasured(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        hebrew = 'שלום עולם'.encode('cp1255')
        repo.commit({'tests/fixtures/page.html': b'<html><body>' + hebrew + b'</body></html>\n',
                     'tests/test_c.py': b'# ' + hebrew + b'\n@unittest.skip("later")\nclass T:\n    pass\n'})
        rc, out = run(repo, anchor)
        self.assertEqual(rc, 1, out)
        self.assertEqual(flagged_by_path(out), {'tests/test_c.py': {
            W.line_digest('tests/test_c.py', '@unittest.skip("later")'): ['unittest.skip']}})

    def test_a_binary_file_whose_parsed_lines_disagree_with_its_blobs_is_an_error(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        repo.commit({'.gitattributes': 'tests/test_b.py -diff\n', 'tests/test_b.py': TEST})
        base = W.merge_base(anchor, cwd=repo.dir)
        self.assertEqual(W.numstat(base, cwd=repo.dir)['tests/test_b.py'], None)    # git counts it as binary
        real = W.changes(base, cwd=repo.dir)
        lost = [dict(p, added=p['added'][1:]) if p['new'] == 'tests/test_b.py' else p for p in real]
        with mock.patch.object(W, 'changes', return_value=lost):
            with self.assertRaisesRegex(W.Unreadable, 'disagrees with its blobs'):
                W.measure(base, cwd=repo.dir)

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
        found, read, _ = W.measure(base, cwd=repo.dir)
        self.assertEqual((found, read), ({}, 1))
        with mock.patch.object(W, 'numstat', return_value={'tests/test_a.py': (2, 0)}):
            with self.assertRaisesRegex(W.Unreadable, 'disagree'):
                W.measure(base, cwd=repo.dir)

    def test_a_diff_line_the_blob_does_not_hold_is_an_error(self):
        repo = Repo()
        repo.commit({'tests/test_a.py': TEST})
        with self.assertRaisesRegex(W.Unreadable, 'the diff and the blob of tests/test_a.py'):
            W.flagged('python', 'HEAD', 'tests/test_a.py', [(1, 'not the line')], repo.dir, [])

    def test_an_unreadable_declarations_file_is_an_error(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        for text in ('{"weakening": [1]}', '{"weakening": {"tests/a.py": [1]}}', '{not json'):
            with self.subTest(text=text):
                repo.decl.write_text(text)
                rc, out = run(repo, anchor)
                self.assertEqual(rc, 2, out)

    def test_an_unreadable_declarations_file_at_the_merge_base_is_an_error(self):
        repo = Repo()
        repo.decl.write_text('{not json')
        git(repo.dir, 'add', '-f', 'decl.json')
        anchor = repo.commit({'tests/test_a.py': TEST})
        rc, out = run(repo, anchor, {})
        self.assertEqual(rc, 2, out)

    def test_a_declarations_file_outside_the_repository_is_an_error(self):
        repo = Repo()
        anchor = repo.commit({'tests/test_a.py': TEST})
        outside = Path(tempfile.mkdtemp()) / 'decl.json'
        outside.write_text('{"weakening": {}}')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(W.main([anchor], cwd=repo.dir, declarations=outside), 2)
        self.assertIn('is not in the repository', out.getvalue())


class TheRealFileAndTheLightJob(unittest.TestCase):
    def test_the_declarations_file_holds_a_weakening_map_and_each_entry_is_signed(self):
        data = json.loads((ROOT / 'docs' / 'identity' / 'allowed-deletions.json').read_text(encoding='utf-8'))
        self.assertIn('weakening', data['rule_weakening'])
        for path, entries in W.records(data['weakening'], 'the real file').items():
            for entry in entries:
                with self.subTest(path=path):
                    self.assertRegex(entry.get('line_sha256', ''), r'^[0-9a-f]{64}$')
                    self.assertEqual(W.unsigned(entry), [])

    def test_the_first_weakening_declaration_is_a_pure_addition(self):
        """Item 8: the map opens on its own line, so a record is added by inserting lines, never by rewriting one."""
        text = (ROOT / 'docs' / 'identity' / 'allowed-deletions.json').read_text(encoding='utf-8')
        lines = text.split('\n')
        at = lines.index(' "weakening": {')
        comma = ',' if json.loads(text)['weakening'] else ''
        lines.insert(at + 1, '  "tests/test_x.py": [{"line_sha256": "0", "reason": "r"}]' + comma)
        self.assertEqual(json.loads('\n'.join(lines))['weakening']['tests/test_x.py'][0]['reason'], 'r')

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
        self.assertNotIn('if', steps[deletions])
        self.assertEqual(step.get('if'), '${{ !cancelled() }}')     # item 9: it runs when an earlier step failed
        for s in (steps[deletions], step):
            self.assertNotIn('continue-on-error', s)
        self.assertEqual([n for n, rx in W.PYTHON + W.SHELL if any(rx.search(line) for line in step['run'].splitlines())],
                         [])

    def test_the_checkout_of_the_light_job_has_the_history_the_merge_base_needs(self):
        [checkout] = [s for s in yaml.safe_load((ROOT / '.github/workflows/v24-ci.yml').read_text())['jobs']['light']
                      ['steps'] if str(s.get('uses', '')).startswith('actions/checkout')]
        self.assertEqual(checkout['with']['fetch-depth'], 0)
        self.assertNotIn('ref', checkout['with'])                    # GitHub's merge commit: the rolling anchor


if __name__ == '__main__':
    unittest.main()
