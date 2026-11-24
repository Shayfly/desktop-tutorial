"""needs_env is enforced, not decorative (the owner, 2026-11-15 22:50): under -m "not needs_env" no listed module or
test is collected, and the fast suite never lists one. Without the expression (CI) the list changes nothing."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_LINES = [l.strip() for l in (ROOT / 'tests' / 'needs_env.txt').read_text(encoding='utf-8').splitlines()
          if l.strip() and not l.lstrip().startswith('#')]
MODULES = {l for l in _LINES if '::' not in l}       # read here, not imported from conftest (pytest owns that module)
NODE_IDS = {l for l in _LINES if '::' in l}


def collected(*args: str) -> tuple[list[str], str]:
    out = subprocess.run([sys.executable, '-m', 'pytest', '--co', '-q', '-p', 'no:cacheprovider', *args, 'tests'],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
    return [l.strip() for l in out.stdout.splitlines() if '::' in l], out.stdout


class NeedsEnv(unittest.TestCase):
    def test_the_list_is_the_measured_73(self):
        self.assertEqual((len(MODULES), len(NODE_IDS)), (37, 36))
        for m in MODULES:
            self.assertTrue((ROOT / m).is_file(), m)

    def test_nothing_listed_is_collected_under_not_needs_env(self):
        ids, text = collected('-m', 'not needs_env')
        self.assertGreater(len(ids), 1000)
        self.assertNotIn('ERROR collecting', text)                      # a listed module is not even imported
        leaked = [i for i in ids if i in NODE_IDS or i.split('::')[0] in MODULES]
        self.assertEqual(leaked, [])

    def test_the_fast_suite_lists_no_needs_env_module(self):
        fast = ROOT / 'tests' / 'fast_suite.txt'
        if not fast.is_file():
            self.skipTest('tests/fast_suite.txt is not on this tree yet (#402)')
        listed = {l.strip() for l in fast.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')}
        self.assertEqual(listed & (MODULES | {n.split('::')[0] for n in NODE_IDS}), set())


if __name__ == '__main__':
    unittest.main()
