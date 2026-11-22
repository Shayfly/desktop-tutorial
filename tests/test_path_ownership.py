"""scripts/path_ownership.py: a codex/ or design/ branch changes neither the platform UI shell nor the customers' sites'
engine (the owner, 2026-11-22 evening: the platform UI moves to Claude Code, Codex does not continue it; OWNERS.md)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('path_ownership', ROOT / 'scripts' / 'path_ownership.py')
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

UI = ('omni_prod/assets/app.css', 'omni_prod/assets/index.html', 'omni_prod/assets/app.js',
      'omni_prod/assets/brand/logo.svg', 'ui/old.html', 'omni_prod/assets/sw.js')
ENGINE = ('omni_prod/section_library/library.css', 'omni_prod/site_content/__init__.py',
          'omni_prod/conversation/supervisor.py', 'omni_prod/fact_canon.py', 'omni_prod/typography/x.py')


class TheSplit(unittest.TestCase):
    def test_codex_changes_neither_the_ui_shell_nor_the_site_engine(self):
        for path in UI + ENGINE:
            with self.subTest(path):
                errors, _ = P.judge('codex/new-design', [path])
                self.assertEqual(len(errors), 1)
                self.assertIn('codex/', errors[0])

    def test_a_design_branch_is_judged_as_codex(self):
        # Codex pushed the platform design as design/148ai-full-workspace-133
        for path in ('omni_prod/discovery.py', 'omni_prod/assets/app.css'):
            with self.subTest(path):
                errors, _ = P.judge('design/148ai-full-workspace-133', [path])
                self.assertEqual(len(errors), 1)

    def test_the_error_names_whose_path_it_is(self):
        self.assertIn('platform UI shell', P.judge('codex/x', ['omni_prod/assets/app.css'])[0][0])
        self.assertIn("customers' sites", P.judge('codex/x', ['omni_prod/fact_canon.py'])[0][0])

    def test_claude_owns_both(self):
        self.assertEqual(P.judge('claude/practical-hopper-x', list(UI + ENGINE)), ([], []))

    def test_codex_may_change_the_shared_paths(self):
        self.assertEqual(P.judge('codex/x', ['.github/workflows/v24-ci.yml', 'docs/x.md', 'omni_prod/investor_app.py',
                                             'omni_prod/assets/replicate-test.html']), ([], []))

    def test_other_branches_are_not_judged(self):
        self.assertEqual(P.judge('fix/anything', ['omni_prod/assets/app.css', 'omni_prod/fact_canon.py']), ([], []))

    def test_a_path_is_owned_by_prefix_not_by_substring(self):
        self.assertFalse(P.owned('omni_prod/assets/app.js.map', P.UI_SHELL))
        self.assertFalse(P.owned('omni_prod/intake_extra.py', P.SITE_ENGINE))
        self.assertTrue(P.owned('omni_prod/intake/agent.py', P.SITE_ENGINE))


if __name__ == '__main__':
    unittest.main()
