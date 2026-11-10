"""Gate freeze (Michael 2026-11-10): while docs/gate-freeze.json is active, no PR may change a gate file.

The diff check itself runs in .github/workflows/gate-freeze.yml (a job with the full git history; a unit test inside
the suite has no reliable access to the base branch). This file checks the freeze definition and the script.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

FREEZE = json.load(open('docs/gate-freeze.json', encoding='utf-8'))


class GateFreeze(unittest.TestCase):
    def test_gate_files_exist(self):
        missing = [p for p in FREEZE['gate_files'] if not os.path.exists(p)]
        self.assertEqual(missing, [])

    def run_check(self, changed: list[str], active: bool = True) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('\n'.join(changed))
        freeze = dict(FREEZE, active=active)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as g:
            json.dump(freeze, g)
        return subprocess.run([sys.executable, 'infra/gate_freeze_check.py', f.name, g.name],
                              capture_output=True, text=True)

    def test_script_blocks_a_gate_change_while_active(self):
        r = self.run_check(['omni_prod/skills_runtime.py', 'README.md'])
        self.assertEqual(r.returncode, 1)
        self.assertIn('::error title=gate freeze::', r.stdout)

    def test_script_allows_product_changes_and_an_inactive_freeze(self):
        self.assertEqual(self.run_check(['omni_prod/assets/app.js']).returncode, 0)
        self.assertEqual(self.run_check(['omni_prod/skills_runtime.py'], active=False).returncode, 0)

    def test_changing_the_freeze_itself_is_its_own_reviewed_decision(self):
        self.assertEqual(self.run_check(['docs/gate-freeze.json', 'omni_prod/skills_runtime.py']).returncode, 0)


if __name__ == '__main__':
    unittest.main()
