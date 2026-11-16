"""2026-11-16: the v24-ci test job ran the whole suite twice (its pytest step, then again inside
run_international_gate.py), and #418's job was cancelled at its 20-minute bound. The gate now reads the junit report
the first run wrote. Real path: scripts/junit_report.verdict on real junit files written by pytest itself, and the
workflow and the gate as committed. Runs in ci-fast (test_ci_*)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('junit_report', ROOT / 'scripts' / 'junit_report.py')
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def junit_of(test_source: str) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / 'test_x.py').write_text(test_source)
    subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', f'--junitxml={d / "r.xml"}',
                    str(d / 'test_x.py')], capture_output=True, cwd=d)
    return d / 'r.xml'


class TheVerdict(unittest.TestCase):
    def test_a_green_report_passes_and_says_its_counts(self):
        ok, detail = J.verdict(junit_of('def test_a():\n    pass\ndef test_b():\n    pass\n'))
        self.assertTrue(ok, detail)
        self.assertIn('2 tests, 0 failures, 0 errors', detail)

    def test_a_failure_or_an_error_fails(self):
        for src in ('def test_a():\n    assert False\n', 'import pytest\n@pytest.fixture\ndef f():\n    raise RuntimeError\n'
                    'def test_a(f):\n    pass\n'):
            with self.subTest(src[:20]):
                self.assertFalse(J.verdict(junit_of(src))[0])

    def test_missing_unreadable_or_empty_is_not_a_pass(self):
        d = Path(tempfile.mkdtemp())
        self.assertFalse(J.verdict(d / 'none.xml')[0])
        (d / 'bad.xml').write_text('<testsuites><testsuite')
        self.assertFalse(J.verdict(d / 'bad.xml')[0])
        (d / 'empty.xml').write_text('<testsuites><testsuite name="pytest" tests="0" failures="0" errors="0"/></testsuites>')
        ok, detail = J.verdict(d / 'empty.xml')
        self.assertFalse(ok)
        self.assertIn('empty report is not a pass', detail)

    def test_skips_are_counted_and_said(self):
        ok, detail = J.verdict(junit_of('import pytest\ndef test_a():\n    pass\n@pytest.mark.skip\ndef test_b():\n    pass\n'))
        self.assertTrue(ok)
        self.assertIn('1 skipped', detail)


class TheJob(unittest.TestCase):
    def test_the_gate_reads_the_report_in_ci_and_runs_pytest_without_it(self):
        gate = (ROOT / 'scripts' / 'run_international_gate.py').read_text(encoding='utf-8')
        self.assertIn("_report=os.environ.get('OMNI_PYTEST_REPORT')", gate)
        self.assertIn('_ok,_detail=verdict(ROOT/_report)', gate)
        self.assertIn("ok &= run('pytest',[sys.executable,'-m','pytest','-q'])", gate)    # a local run is unchanged

    def test_v24_ci_hands_the_gate_its_own_report(self):
        steps = yaml.safe_load((ROOT / '.github/workflows/v24-ci.yml').read_text(encoding='utf-8'))['jobs']['test']['steps']
        runs = [s.get('run', '') for s in steps]
        first = runs.index('python -m pytest -q --junitxml=pytest-report.xml')
        [gate] = [s for s in steps if s.get('run') == 'python scripts/run_international_gate.py']
        self.assertEqual(gate['env']['OMNI_PYTEST_REPORT'], 'pytest-report.xml')
        self.assertLess(first, steps.index(gate))


if __name__ == '__main__':
    unittest.main()
