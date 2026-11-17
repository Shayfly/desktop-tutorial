"""Every negative control can still be applied (2026-11-17).

#425's first CI run failed in pg-tests: two controls mutated a line of gate.py that the same PR had rewritten, so the
mutation matched nothing and the control did not run. A control that cannot be applied proves nothing. This reads
every spec and checks, without running anything, that each mutation's text occurs exactly once in its file -- the
same rule scripts/run_negative_controls.py enforces when it runs."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = sorted((ROOT / 'tests' / 'negative_controls').glob('*.json'))


class EveryControlApplies(unittest.TestCase):
    def test_each_mutation_text_occurs_exactly_once_in_its_file(self):
        self.assertGreater(len(SPECS), 40)
        problems, checked = [], 0
        for spec in SPECS:
            for control in json.loads(spec.read_text(encoding='utf-8'))['controls']:
                texts: dict[str, str] = {}
                for m in control['mutations']:              # mutations of one control are applied in order
                    path = ROOT / m['file']
                    if not path.is_file():
                        problems.append(f"{spec.name} {control['id']}: no file {m['file']}")
                        continue
                    text = texts.get(m['file'], path.read_text(encoding='utf-8'))
                    checked += 1
                    if text.count(m['old']) != 1:
                        problems.append(f"{spec.name} {control['id']}: text found {text.count(m['old'])} times in "
                                        f"{m['file']}: {m['old'][:70]!r}")
                    else:
                        texts[m['file']] = text.replace(m['old'], m['new'])
        self.assertEqual(problems, [])
        self.assertGreater(checked, 200)

    def test_every_control_names_what_it_expects_to_fail(self):
        for spec in SPECS:
            for control in json.loads(spec.read_text(encoding='utf-8'))['controls']:
                self.assertTrue(control.get('expect_failed') or control.get('expect_failed_by_env'),
                                f"{spec.name} {control['id']} expects nothing to fail")


if __name__ == '__main__':
    unittest.main()
