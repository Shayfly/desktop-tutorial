"""Warehouse 127, acceptance 5: a reference site that stopped loading is flagged by name, never left silently."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('domain_references', ROOT / 'tools' / 'domain_references.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

REG = {'domains': {'hair-salon': {'references': [f'https://salon{i}.example' for i in range(6)]},
                   'lawyer': {'references': [f'https://law{i}.example' for i in range(5)]}}}


def fetcher(dead: dict):
    def f(url):
        return dead.get(url, (200, 40_000, ''))
    return f


class TheReferenceCheck(unittest.TestCase):
    def test_all_alive(self):
        out = R.check(REG, fetcher({}))
        self.assertEqual((out['dead'], out['short']), ([], []))

    def test_each_kind_of_dead_is_named(self):
        dead = {'https://salon0.example': (None, 0, 'URLError'), 'https://salon1.example': (404, 40_000, 'HTTP 404'),
                'https://salon2.example': (200, 120, '')}
        out = R.check(REG, fetcher(dead))
        whys = {u: w for _, u, w in out['dead']}
        self.assertEqual(whys['https://salon0.example'], 'no answer (URLError)')
        self.assertEqual(whys['https://salon1.example'], 'HTTP 404')
        self.assertIn('empty or blocked', whys['https://salon2.example'])
        self.assertEqual(out['short'], ['hair-salon'])            # 3 live of 6: below 5

    def test_one_dead_of_five_leaves_a_domain_short(self):
        out = R.check(REG, fetcher({'https://law0.example': (503, 40_000, 'HTTP 503')}))
        self.assertEqual(out['short'], ['lawyer'])

    def test_the_tool_exits_red_on_a_dead_reference_and_green_otherwise(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'r.json').write_text(json.dumps(REG), encoding='utf-8')
            self.assertEqual(R.main(['--out', f'{tmp}/o.json', '--registry', f'{tmp}/r.json'], fetcher({})), 0)
            self.assertEqual(R.main(['--out', f'{tmp}/o.json', '--registry', f'{tmp}/r.json'],
                                    fetcher({'https://law1.example': (None, 0, 'Timeout')})), 1)
            self.assertEqual(R.main(['--out', f'{tmp}/o.json', '--registry', f'{tmp}/missing.json'], fetcher({})), 2)

    def test_a_domain_below_five_live_references_fails_even_with_nothing_dead(self):
        short = {'domains': {'lawyer': {'references': [f'https://law{i}.example' for i in range(4)]}}}
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'r.json').write_text(json.dumps(short), encoding='utf-8')
            self.assertEqual(R.main(['--out', f'{tmp}/o.json', '--registry', f'{tmp}/r.json'], fetcher({})), 1)

    def test_no_network_is_not_207_dead_sites(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'r.json').write_text(json.dumps(REG), encoding='utf-8')
            self.assertEqual(R.main(['--out', f'{tmp}/o.json', '--registry', f'{tmp}/r.json'],
                                    lambda url: (None, 0, 'URLError')), 2)
            self.assertFalse(Path(tmp, 'o.json').exists())

    def test_the_real_registry_has_every_reference_listed(self):
        reg = json.loads((ROOT / 'omni_prod' / 'domain_registry.json').read_text(encoding='utf-8'))
        out = R.check(reg, fetcher({}))
        self.assertEqual(len(out['domains']), 30)


if __name__ == '__main__':
    unittest.main()
