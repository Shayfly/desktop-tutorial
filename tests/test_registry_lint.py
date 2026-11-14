"""C31: registry_lint can FAIL (its own canary), and it is red when a canary row is removed (founder 2026-10-21).

Boundary (CONTROLS.json c31_boundary): the lint proves a canary row exists and names an existing test; it does not prove
the canary fails when the control breaks.
"""
import copy
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import registry_lint as RL  # noqa: E402

REAL = json.loads((ROOT / 'CONTROLS.json').read_text(encoding='utf-8'))
TODAY = date(2026, 10, 21)


def run_cli(registry: dict, *extra) -> subprocess.CompletedProcess:
    path = ROOT / '.registry_lint_case.json'          # next to CONTROLS.json: test ids resolve from the repo root
    path.write_text(json.dumps(registry, ensure_ascii=False), encoding='utf-8')
    try:
        return subprocess.run([sys.executable, str(ROOT / 'tools' / 'registry_lint.py'), str(path), '--today', '2026-10-21',
                               *extra], capture_output=True, text=True, timeout=60)
    finally:
        path.unlink()


def control(reg, cid):
    return next(c for c in reg['controls'] if c['id'] == cid)


class TheRealRegistry(unittest.TestCase):
    def test_is_clean_today(self):
        self.assertEqual(RL.lint(REAL, root=ROOT, today=TODAY), [])

    def test_removing_a_canary_row_is_red_and_restoring_it_is_green(self):
        removed = copy.deepcopy(REAL)
        del control(removed, 'C02')['canary']
        red = run_cli(removed)
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn('R1 C02: must declare exactly one of canary / canary_pending (neither present)', red.stdout)
        green = run_cli(copy.deepcopy(REAL))
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

    def test_swapping_a_canary_for_pending_is_red_against_main(self):
        swapped = copy.deepcopy(REAL)
        c = control(swapped, 'C02')
        del c['canary']
        c['canary_pending'] = 'later'
        self.assertEqual(RL.lint(swapped, root=ROOT, today=TODAY), [])            # R1 alone cannot see it
        errors = RL.lint(swapped, root=ROOT, base=REAL, today=TODAY)                 # R4 against main does
        self.assertEqual(errors, ['R4 C02: has a canary on main and none here (canary row removed)'])


class TheLintCanFail(unittest.TestCase):
    """The lint's own canary: every rule turns red on a registry that breaks it."""

    def errors(self, mutate, **kw):
        reg = copy.deepcopy(REAL)
        mutate(reg)
        return RL.lint(reg, root=ROOT, today=kw.get('today', TODAY), base=kw.get('base'))

    def test_R1_neither_or_both(self):
        self.assertTrue(any(e.startswith('R1 C01') for e in self.errors(lambda r: control(r, 'C01').pop('canary'))))
        self.assertTrue(any(e.startswith('R1 C03') for e in self.errors(
            lambda r: control(r, 'C03').update(canary=['tests/test_qa_budget.py::AuthorizeTests::test_total_cap']))))
        self.assertTrue(any(e.startswith('R1 C03') for e in self.errors(lambda r: control(r, 'C03').update(canary_pending=' '))))

    def test_R2_a_canary_that_names_a_missing_test(self):
        errs = self.errors(lambda r: control(r, 'C12').update(canary=['tests/test_qa_budget.py::AuthorizeTests::test_gone']))
        self.assertIn('R2 C12: canary tests/test_qa_budget.py::AuthorizeTests::test_gone: '
                      'tests/test_qa_budget.py::AuthorizeTests has no test test_gone', errs)
        errs = self.errors(lambda r: control(r, 'C12').update(canary=['tests/no_such_file.py::X::y']))
        self.assertIn('R2 C12: canary tests/no_such_file.py::X::y: tests/no_such_file.py does not exist', errs)

    def test_R3_an_overdue_drill(self):
        def never_ran_c17(r):                                                        # C17 weekly, adopted 10-20
            r['drills_run'] = [d for d in r['drills_run'] if d.get('control') != 'C17']
        errs = self.errors(never_ran_c17, today=date(2026, 10, 28))
        self.assertIn('R3 C17: drill overdue since 2026-10-27 (weekly; last adopted 2026-10-20)', errs)
        self.assertFalse(any(e.startswith('R3 C10') for e in errs))                  # C10 ran 10-20, quarterly

    def test_R3_a_recorded_drill_moves_the_due_date(self):
        def only_the_10_28_run(r):                                                   # the registry as it was on 10-28
            r['drills_run'] = [d for d in r['drills_run'] if d.get('control') != 'C17' or d.get('date') == '2026-10-28']
        self.assertFalse(any(e.startswith('R3 C17') for e in self.errors(only_the_10_28_run, today=date(2026, 11, 4))))
        self.assertIn('R3 C17: drill overdue since 2026-11-04 (weekly; last run 2026-10-28)',
                      self.errors(only_the_10_28_run, today=date(2026, 11, 5)))

    def test_R3_the_latest_recorded_run_wins(self):                                  # 11-14 run 43578100405 recorded 11-14
        self.assertFalse(any(e.startswith('R3 C17') for e in self.errors(lambda r: None, today=date(2026, 11, 21))))
        self.assertIn('R3 C17: drill overdue since 2026-11-21 (weekly; last run 2026-11-14)',
                      self.errors(lambda r: None, today=date(2026, 11, 22)))
        # the older record alone (11-06) is overdue on 11-14: the newest entry is the one that counts
        self.assertIn('R3 C17: drill overdue since 2026-11-13 (weekly; last run 2026-11-06)',
                      self.errors(lambda r: r.__setitem__('drills_run', [x for x in r['drills_run']
                                                                         if x.get('date') != '2026-11-14']),
                                  today=date(2026, 11, 14)))

    def test_R3_a_live_control_with_its_own_drill(self):
        errs = self.errors(lambda r: None, today=date(2026, 11, 21))
        self.assertIn('R3 C16: drill overdue since 2026-11-20 (monthly; last adopted 2026-10-20)', errs)

    def test_R5_duplicate_ids(self):
        self.assertIn('R5 C01: control id is not unique', self.errors(lambda r: r['controls'].append(copy.deepcopy(control(r, 'C01')))))

    def test_the_cli_exit_codes(self):
        self.assertEqual(run_cli({'controls': [{'id': 'X'}]}).returncode, 1)
        bad = subprocess.run([sys.executable, str(ROOT / 'tools' / 'registry_lint.py'), str(ROOT / 'no-such.json')],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(bad.returncode, 2)


if __name__ == '__main__':
    unittest.main()


class R3ReadsTheDrillRecordFromMain(unittest.TestCase):
    """Michael 2026-11-14: "R3 ייקרא את רישום התרגיל מ-main, לא מראש ה-PR" -- and the #322 lesson: data every branch
    shares is read from where it is shared. Real rows: CONTROLS.json on main (with the C17 run of 2026-11-14) and the
    same file as #352-#355 carried it, branched before that run was recorded (main minus that entry)."""
    TODAY = date(2026, 11, 15)
    RECORD = next(r for r in REAL['drills_run'] if r.get('control') == 'C17' and r.get('date') == '2026-11-14')

    def stale_branch(self):
        reg = copy.deepcopy(REAL)
        reg['drills_run'] = [r for r in reg['drills_run'] if r != self.RECORD]
        return reg

    def r3(self, head, base):
        return [e for e in RL.lint(head, root=ROOT, today=self.TODAY, base=base) if e.startswith('R3 C17')]

    def test_a_branch_made_before_the_record_passes_because_main_has_it(self):       # #353 on 2026-11-14
        self.assertEqual(self.r3(self.stale_branch(), base=REAL), [])

    def test_a_pr_that_records_the_drill_passes_although_main_lacks_it(self):        # #357 on 2026-11-14
        self.assertEqual(self.r3(REAL, base=self.stale_branch()), [])

    def test_overdue_on_main_and_on_the_branch_still_fails(self):
        self.assertEqual(self.r3(self.stale_branch(), base=self.stale_branch()),
                         ['R3 C17: drill overdue since 2026-11-13 (weekly; last run 2026-11-06)'])

    def test_a_branch_cannot_remove_a_record_main_has(self):
        head = self.stale_branch()
        head['drills_run'] = []                                       # even every record gone from the branch copy
        self.assertEqual(self.r3(head, base=REAL), [])

    def test_an_unreadable_main_registry_fails_loudly_and_never_falls_back(self):
        p = run_cli(self.stale_branch(), '--base', str(ROOT / 'no-such-main.json'), '--today', '2026-11-15')
        self.assertEqual(p.returncode, 2)
        self.assertIn('cannot read the registry on main', p.stdout)
        self.assertIn('R3 reads the drill record from main', p.stdout)
