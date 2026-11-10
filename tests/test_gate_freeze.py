"""Gate freeze (Michael 2026-11-10): while docs/gate-freeze.json is active, no PR may change a gate file.

CI runs this on pull requests with GITHUB_BASE_REF set; it diffs the PR against its base. Ending the freeze is itself
a change to docs/gate-freeze.json ("active": false), reviewed like any other.
"""
import json
import os
import subprocess
import unittest

FREEZE = json.load(open('docs/gate-freeze.json', encoding='utf-8'))


class GateFreeze(unittest.TestCase):
    def test_gate_files_exist(self):
        missing = [p for p in FREEZE['gate_files'] if not os.path.exists(p)]
        self.assertEqual(missing, [])

    @unittest.skipUnless(os.getenv('GITHUB_BASE_REF'), 'only on pull requests')
    def test_no_gate_file_changes_while_frozen(self):
        base = os.environ['GITHUB_BASE_REF']
        # an explicit refspec: a bare 'git fetch origin main' writes only FETCH_HEAD, not origin/main
        subprocess.run(['git', 'fetch', '--depth=1', 'origin', f'+refs/heads/{base}:refs/remotes/origin/{base}'],
                       check=False, capture_output=True)
        # CI checks out the PR merge commit, so a two-dot diff against the base is exactly the PR's change.
        diff = subprocess.run(['git', 'diff', '--name-only', f'origin/{base}', 'HEAD'], capture_output=True, text=True)
        self.assertEqual(diff.returncode, 0, f'cannot diff against {base}: {diff.stderr}')   # never pass silently
        changed = set(diff.stdout.split())
        if 'docs/gate-freeze.json' in changed:
            return                                      # ending/changing the freeze is a reviewed decision of its own
        touched = sorted(changed & set(FREEZE['gate_files']))
        if FREEZE['active'] and touched:
            print(f"::error title=gate freeze::{', '.join(touched)} changed during the 72h gate freeze")
        self.assertFalse(FREEZE['active'] and touched, f'gate files changed during the freeze: {touched}')


if __name__ == '__main__':
    unittest.main()
