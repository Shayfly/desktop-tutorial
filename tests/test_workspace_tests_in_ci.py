"""The platform design's own tests run on every pull request (review items T1-T3 of #503, 2026-11-22; the owner, the
same evening: the platform UI is Claude Code's to continue).

T1  tests/workspace_sidebar_local.cjs (Codex's) needs a development server, and nothing started one, so CI ran neither
    it nor its mutations. The browser job now starts it (in-memory accounts) and runs the test, then each mutation,
    and an uncaught mutation -- or one whose anchor is gone from the code -- fails the job.
T2  the three guards the design added against late answers (a stale quote, a late plan, a restore after moving to
    another project) had no test: tests/workspace_guards_browser.cjs, each scenario also run without its guard.
T3  the sidebar test's status filter passed only on the in-memory server's 503: the latest-build answers now come from
    the test, and production's {build: null} is checked as "no build yet"."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
SIDEBAR = (ROOT / 'tests' / 'workspace_sidebar_local.cjs').read_text(encoding='utf-8')
GUARDS = (ROOT / 'tests' / 'workspace_guards_browser.cjs').read_text(encoding='utf-8')


def browser_job() -> str:
    match = re.search(r'\n  browser-tests:\n(.*?)\n  [a-z][a-z0-9-]*:\n', CI, re.S)
    assert match, 'v24-ci.yml has a browser-tests job'
    return match.group(1)


class SidebarRunsOnADevelopmentServer(unittest.TestCase):
    def test_the_browser_job_starts_the_server_with_memory_accounts(self):
        job = browser_job()
        self.assertRegex(job, r'OMNI_CREATOR_PERSISTENCE=memory[^\n]*uvicorn omni_prod\.investor_app:app[^\n]*--port 18749')
        self.assertIn("const baseURL = 'http://127.0.0.1:18749';", SIDEBAR)        # the port the test expects
        self.assertIn('pip install -r requirements-production.txt', job)
        self.assertIn('the development server did not start', job)              # a server that never came up fails loudly

    def test_the_test_and_every_mutation_run(self):
        job = browser_job()
        self.assertIn('node --check tests/workspace_sidebar_local.cjs', job)
        self.assertRegex(job, r'\n\s+node tests/workspace_sidebar_local\.cjs\n')
        self.assertIn('for m in $(WORKSPACE_LIST_MUTATIONS=1 node tests/workspace_sidebar_local.cjs)', job)
        self.assertIn('WORKSPACE_MUTATION=$m node tests/workspace_sidebar_local.cjs', job)
        self.assertIn('was NOT caught', job)
        self.assertIn('mutation anchor missing', job)                            # a vanished anchor is not a catch
        self.assertIn("elif ! grep -q AssertionError mutation.log; then", job)   # nor is a crash or a dead server
        self.assertIn('failed without an assertion, so it was not caught', job)
        self.assertIn('exit $missed', job)

    def test_nothing_lets_a_failure_through(self):
        # read as YAML, not as text: a step-level continue-on-error, an if: that skips it, or set +e in its script
        # would let every failure through while every string above is still present (#508 review, 2026-11-23)
        job = yaml.safe_load(CI)['jobs']['browser-tests']
        self.assertNotIn('continue-on-error', job)
        steps = [s for s in job['steps'] if re.search(r'workspace_(sidebar_local|guards_browser)\.cjs', s.get('run', ''))]
        self.assertEqual(len(steps), 3)                                           # parse-check, guards, sidebar
        for step in steps:
            with self.subTest(step=step.get('name') or step['run'][:40]):
                self.assertNotIn('continue-on-error', step)
                self.assertNotIn('if', step)
                self.assertNotRegex(step['run'], r'set \+e|\|\|\s*true|\|\|\s*:')

    def test_the_test_lists_its_mutations(self):
        self.assertIn('if (process.env.WORKSPACE_LIST_MUTATIONS) {', SIDEBAR)
        self.assertIn('...Object.keys(mutations), ...Object.keys(scriptMutations)', SIDEBAR)
        self.assertGreaterEqual(len(re.findall(r'^  [a-z_]+: ', SIDEBAR, re.M)), 9)


class StatusIsNotReadFromA503(unittest.TestCase):
    def test_the_latest_build_is_answered_by_the_test(self):
        self.assertIn("await page.route('**/api/v28/projects/*/builds/latest'", SIDEBAR)
        self.assertIn("JSON.stringify({ build: null })", SIDEBAR)

    def test_both_states_are_checked(self):
        self.assertIn("selectOption('none');\n      assert.deepEqual(await listed(), ['אוורסט']", SIDEBAR)
        self.assertIn("selectOption('unknown');\n      assert.deepEqual(await listed(), [second]", SIDEBAR)
        self.assertIn('guessed_status:', SIDEBAR)


class TheGuardsAreTested(unittest.TestCase):
    def test_the_browser_job_runs_the_guards(self):
        job = browser_job()
        self.assertIn('node --check tests/workspace_guards_browser.cjs', job)
        self.assertIn('node tests/workspace_guards_browser.cjs', job)

    def test_every_guard_is_taken_out_once(self):
        old = re.search(r'const OLD = \{\n(.*?)\n\};', GUARDS, re.S).group(1)
        self.assertEqual(sorted(re.findall(r'^  ([A-Z]\d): ', old, re.M)), ['P1', 'P2', 'Q1', 'R1', 'R2', 'R3', 'R4'])
        self.assertIn('also passes WITHOUT its guard', GUARDS)
        self.assertIn('the guard is in app.js exactly once', GUARDS)


if __name__ == '__main__':
    unittest.main()
