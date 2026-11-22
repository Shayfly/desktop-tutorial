"""scripts/path_ownership.py: a claude/ branch does not change the platform UI shell, a codex/ branch does not change
the customers' sites' engine (the owner, 2026-11-22; OWNERS.md)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('path_ownership', ROOT / 'scripts' / 'path_ownership.py')
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


class TheSplit(unittest.TestCase):
    def test_claude_does_not_change_the_ui_shell(self):
        for path in ('omni_prod/assets/app.css', 'omni_prod/assets/index.html', 'omni_prod/assets/brand/logo.svg',
                     'ui/old.html', 'omni_prod/assets/sw.js'):
            with self.subTest(path):
                errors, _ = P.judge('claude/practical-hopper-x', [path])
                self.assertEqual(len(errors), 1)
                self.assertIn('platform UI shell', errors[0])

    def test_claude_app_js_is_the_text_only_exception_said_to_the_reviewer(self):
        errors, notices = P.judge('claude/practical-hopper-x', ['omni_prod/assets/app.js'])
        self.assertEqual(errors, [])
        self.assertEqual(len(notices), 1)

    def test_codex_does_not_change_the_site_engine(self):
        for path in ('omni_prod/section_library/library.css', 'omni_prod/site_content/__init__.py',
                     'omni_prod/conversation/supervisor.py', 'omni_prod/fact_canon.py', 'omni_prod/typography/x.py'):
            with self.subTest(path):
                errors, _ = P.judge('codex/new-design', [path])
                self.assertEqual(len(errors), 1)
                self.assertIn("customers' sites", errors[0])

    def test_a_design_branch_is_the_ui_side(self):
        # Codex pushed the platform design as design/148ai-full-workspace-133
        errors, _ = P.judge('design/148ai-full-workspace-133', ['omni_prod/discovery.py'])
        self.assertEqual(len(errors), 1)
        self.assertIn("customers' sites", errors[0])
        self.assertEqual(P.judge('design/148ai-full-workspace-133', ['omni_prod/assets/app.css']), ([], []))

    def test_each_agent_may_change_its_own_and_the_shared_paths(self):
        self.assertEqual(P.judge('codex/new-design', ['omni_prod/assets/app.css', 'omni_prod/assets/app.js',
                                                      '.github/workflows/v24-ci.yml']), ([], []))
        self.assertEqual(P.judge('claude/x', ['omni_prod/site_content/__init__.py', 'omni_prod/investor_app.py',
                                              'omni_prod/assets/replicate-test.html']), ([], []))

    def test_other_branches_are_not_judged(self):
        self.assertEqual(P.judge('fix/anything', ['omni_prod/assets/app.css', 'omni_prod/fact_canon.py']), ([], []))

    def test_a_path_is_owned_by_prefix_not_by_substring(self):
        self.assertFalse(P.owned('omni_prod/assets/app.js.map', P.UI_SHELL))
        self.assertFalse(P.owned('omni_prod/intake_extra.py', P.SITE_ENGINE))
        self.assertTrue(P.owned('omni_prod/intake/agent.py', P.SITE_ENGINE))


if __name__ == '__main__':
    unittest.main()
