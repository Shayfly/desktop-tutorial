"""Dependency gate (founder 2026-11-01 23:33), from bld_96ab03c880f24b3a98065bf29eed11c3: the generated tests were in
`tests.py`; the gate read it as application code, blocked its `import pytest`, and all four rounds failed the same way
with a message that named the file but no line and no way out.

1. `tests.py` is a test module: `import pytest` there is allowed. Negative control: `app.py` with `import pytest` is
   still blocked.
2. Every import finding carries its line; the message says file:line and what to do.
The real gate runs (scan / unsupported_report / DependencyGateExecutor); nothing is mocked but the inner executor.
"""
import json
import unittest

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.dependency_policy import DependencyGateExecutor, scan, unsupported_report
from omni_prod.failure_taxonomy import failure_type

APP = 'import json\n\n\ndef add(a, b):\n    return a + b\n'
TESTS = 'import json\nimport pytest\n\nfrom app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n'


class Inner:
    def __init__(self):
        self.called = 0

    def execute(self, *, repository, spec):
        self.called += 1
        return ExecutionReport(True)


class TestsPyIsATestModule(unittest.TestCase):
    def test_tests_py_may_import_pytest(self):
        repo = {'app.py': APP, 'tests.py': TESTS}
        self.assertEqual(scan(repo), ())
        inner = Inner()
        self.assertTrue(DependencyGateExecutor(inner).execute(repository=repo, spec=None).passed)
        self.assertEqual(inner.called, 1)                                  # the sandbox runs

    def test_nested_tests_py_too(self):
        self.assertEqual(scan({'app.py': APP, 'pkg/tests.py': TESTS}), ())

    def test_negative_control_app_py_importing_pytest_is_still_blocked(self):
        repo = {'app.py': 'import json\nimport pytest\n\n\ndef add(a, b):\n    return a + b\n', 'tests.py': TESTS}
        findings = scan(repo)
        self.assertEqual([(f.name, f.source, f.line) for f in findings], [('pytest', 'app.py', 2)])
        inner = Inner()
        report = DependencyGateExecutor(inner).execute(repository=repo, spec=None)
        self.assertFalse(report.passed)
        self.assertEqual(inner.called, 0)                                  # the sandbox never starts

    def test_other_names_are_still_application_code(self):
        for name in ('testing.py', 'mytests.py', 'tests_helper.py'):
            findings = scan({'app.py': APP, name: 'import pytest\n'})
            self.assertEqual([f.source for f in findings], [name], name)


class FindingSaysWhereAndWhatToDo(unittest.TestCase):
    def test_message_has_file_line_and_the_fix(self):
        repo = {'app.py': 'import os\n\nimport pytest\n'}
        report = unsupported_report(scan(repo))
        msg = report.failures[0].message
        print('\n[gate] ' + msg)
        self.assertIn('pytest (app.py:3): test-only package imported by application code', msg)
        self.assertIn('fix: move the tests into tests/ (or a test_*.py file), or import pytest only there', msg)
        self.assertEqual(json.loads(report.failures[0].evidence)['findings'][0]['line'], 3)

    def test_taxonomy_key_unchanged(self):
        msg = unsupported_report(scan({'app.py': 'import pytest\n'})).failures[0].message
        self.assertEqual(failure_type(msg), 'unsupported_dependency')

    def test_non_test_package_gets_a_line_but_no_pytest_hint(self):
        msg = unsupported_report(scan({'app.py': '\n\nimport requests\n'})).failures[0].message
        self.assertIn('requests (app.py:3): not in the standard library', msg)
        self.assertNotIn('fix: move the tests', msg)

    def test_requirement_file_findings_keep_their_source_without_a_line(self):
        findings = scan({'app.py': APP, 'requirements.txt': 'requests==2.0\n'})
        self.assertTrue(findings)
        self.assertTrue(all(f.line is None and f.where() == f.source for f in findings if f.source == 'requirements.txt'))


if __name__ == '__main__':
    unittest.main()
