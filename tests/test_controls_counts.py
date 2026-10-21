"""#92 COUNT_NOTE_CONTRACT_MISMATCH: the registry's counts reconcile with its own controls.

count_note is the founder's literal contract for v3 ("8 of 30"); count_now is what the registry holds today. Both are
recomputed from `controls`, so neither can drift silently.
"""
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = json.loads((ROOT / 'CONTROLS.json').read_text(encoding='utf-8'))
ADDED_AFTER_V3 = {'C32'}          # founder 2026-10-20, after the v3 count


def problems(d: dict) -> list[str]:
    out = []
    controls = d.get('controls') or []
    ids = [c.get('id') for c in controls]
    auto = [c['id'] for c in controls if c.get('enforcement') == 'automatic']
    review = [c['id'] for c in controls if c.get('enforcement') == 'review']
    if d.get('count_note') != '8 of 30':
        out.append(f'count_note is {d.get("count_note")!r}, the contract is the literal "8 of 30"')
    if 'frozen' not in str(d.get('count_note_frozen', '')) or 'count_now' not in str(d.get('count_note_frozen', '')):
        out.append('count_note_frozen must say the v3 contract is frozen and count_now is the live state')
    v3 = [c for c in controls if c.get('id') not in ADDED_AFTER_V3]
    v3_auto = sum(1 for c in v3 if c.get('enforcement') == 'automatic')
    if (v3_auto, len(v3)) != (8, 30):
        out.append(f'v3 controls compute to {v3_auto} of {len(v3)}, count_note says 8 of 30')
    if 'C30' in ids or 'S01' in ids:
        out.append('C30/S01 is a step, not a control')
    now = d.get('count_now') or {}
    actual = {'controls': len(controls), 'automatic': len(auto), 'review': len(review)}
    for k, v in actual.items():
        if now.get(k) != v:
            out.append(f'count_now.{k} is {now.get(k)!r}, the registry has {v}')
    if len(auto) + len(review) != len(controls):
        out.append('a control is neither automatic nor review')
    return out


class CountsReconcile(unittest.TestCase):
    def test_the_real_registry_reconciles(self):
        self.assertEqual(problems(REAL), [])

    def test_the_old_note_is_red(self):
        d = copy.deepcopy(REAL)
        d['count_note'] = ('8 of 31 -> 8 of 30, C30->S01, 20/10. (v3 counted C30; S01 is a step, not a control.) '
                           'Since then C32 was added (founder 2026-10-20): 31 controls, 8 automatic, 23 review.')
        self.assertIn('count_note is', problems(d)[0])

    def test_dropping_the_frozen_line_is_red(self):
        d = copy.deepcopy(REAL)
        d.pop('count_note_frozen')
        self.assertIn('count_note_frozen must say the v3 contract is frozen and count_now is the live state', problems(d))

    def test_adding_a_control_without_updating_count_now_is_red(self):
        d = copy.deepcopy(REAL)
        d['controls'].append({'id': 'C33', 'enforcement': 'review'})
        self.assertIn('count_now.controls is 31, the registry has 32', problems(d))

    def test_flipping_a_control_to_automatic_is_red(self):
        d = copy.deepcopy(REAL)
        next(c for c in d['controls'] if c['id'] == 'C09')['enforcement'] = 'automatic'
        p = problems(d)
        self.assertIn('v3 controls compute to 9 of 30, count_note says 8 of 30', p)
        self.assertIn('count_now.automatic is 8, the registry has 9', p)


if __name__ == '__main__':
    unittest.main()
