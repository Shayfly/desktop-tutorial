"""skills/REGISTRY.md (the owner, 2026-11-17): three columns, and the built table is derived from the code."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = (ROOT / 'skills' / 'REGISTRY.md').read_text(encoding='utf-8')
ROW = re.compile(r'^\| ([^|]+) \| ([^|]+) \| ([^|]+) \|$', re.M)


def rows(section: str):
    return [tuple(c.strip() for c in m) for m in ROW.findall(section) if m[0].strip() not in ('id', '---')]


class TheRegistry(unittest.TestCase):
    def test_the_built_table_is_what_the_generator_produces_from_the_code(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import skills_registry as S
        self.assertIn(S.block(), TEXT, 'run: python scripts/skills_registry.py --write')
        built = S.built_rows()
        self.assertGreater(len(built), 60)
        self.assertEqual(len(built), len(set(built)))

    def test_every_row_has_exactly_three_columns_and_a_failure_code(self):
        for line in TEXT.splitlines():
            if line.startswith('| ') and not line.startswith('| מה'):
                self.assertEqual(line.count('|'), 4, line)
        for skill, gate, code in rows(TEXT):
            self.assertTrue(skill and gate and code, (skill, gate, code))
            self.assertRegex(code, r'^[A-Za-z0-9_]+$', (skill, code))

    def test_a_built_gate_is_a_gate_the_code_knows_and_a_target_gate_is_one_or_a_dash(self):
        from omni_prod.skill_units import gate as G
        known = set(G.DEFAULT_MODE)
        built, target = TEXT.split('## יעד, עוד לא בנוי')
        self.assertTrue({g for _, g, _ in rows(built)} <= known, {g for _, g, _ in rows(built)} - known)
        self.assertTrue({g for _, g, _ in rows(target.split('## מה כבר מכוסה')[0])} <= known | {'—'})

    def test_one_failure_code_belongs_to_one_skill(self):
        seen = {}
        for skill, gate, code in rows(TEXT):
            self.assertIn(seen.setdefault(code, skill), (skill,), f'{code} is claimed by {seen[code]} and {skill}')

    def test_a_target_skill_is_not_already_built(self):
        built, target = TEXT.split('## יעד, עוד לא בנוי')
        self.assertEqual({c for _, _, c in rows(built)} & {c for _, _, c in rows(target)}, set())

    def test_what_fell_is_recorded_with_its_reason(self):
        parked = (ROOT / 'parked' / 'INDEX.md').read_text(encoding='utf-8')
        fallen = [line for line in parked.splitlines() if line.startswith('| ') and not line.startswith(('| מה', '|---'))]
        self.assertEqual(len(fallen), 17)
        for line in fallen:
            cells = [c.strip() for c in line.strip('|').split('|')]
            self.assertEqual(len(cells), 3, line)
            self.assertTrue(cells[0] and cells[1], line)


if __name__ == '__main__':
    unittest.main()
