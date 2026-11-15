"""Michael 2026-11-15: "C17 -- read from GitHub". R3 counts C17's drill from backup-restore.yml's green runs on main,
read from GitHub (tools/drill_runs_from_github.py), not only from hand-copied CONTROLS.json entries.

Real path: the real CONTROLS.json and the real run history of backup-restore.yml (30 runs, 2026-10-17..11-14, with the
red runs of 10-17..10-19, 10-25 and 11-01; tests/fixtures/backup_restore_runs_2026_11_15.json). The GitHub call itself
is replaced by an answer carrying that history."""
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import drill_runs_from_github as DR  # noqa: E402
import registry_lint as RL  # noqa: E402

REAL = json.loads((ROOT / 'CONTROLS.json').read_text(encoding='utf-8'))
RUNS = json.loads((ROOT / 'tests' / 'fixtures' / 'backup_restore_runs_2026_11_15.json').read_text())['workflow_runs']


def without_hand_records(control_id='C17'):
    reg = copy.deepcopy(REAL)
    reg['drills_run'] = [r for r in reg.get('drills_run') or [] if r.get('control') != control_id]
    return reg


def r3(reg, today, github_runs=None):
    return [e for e in RL.lint(reg, root=ROOT, today=today, github_runs=github_runs) if e.startswith('R3 C17')]


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TheGitHubRecord(unittest.TestCase):
    def test_c17_opts_in(self):
        self.assertEqual(RL_control(REAL, 'C17')['drill_workflow'], 'backup-restore.yml')

    def test_only_green_runs_on_main_from_schedule_or_dispatch_count(self):
        got = DR.drill_entries('C17', 'backup-restore.yml', RUNS)
        reds = [r for r in RUNS if r['conclusion'] != 'success']
        self.assertEqual(len(got), len(RUNS) - len(reds))
        self.assertTrue(reds)                                      # the history has red runs, and none counts
        self.assertNotIn('2026-10-17', {e['date'] for e in got})
        branch = [dict(RUNS[0], head_branch='fix/x'), dict(RUNS[0], event='push'), dict(RUNS[0], status='in_progress')]
        self.assertEqual(DR.drill_entries('C17', 'backup-restore.yml', branch), [])

    def test_without_hand_records_c17_is_overdue_and_the_github_record_clears_it(self):
        reg = without_hand_records()
        today = date(2026, 11, 15)
        self.assertTrue(r3(reg, today))                             # adopted 10-20 + 7 days: overdue
        self.assertEqual(r3(reg, today, DR.drill_entries('C17', 'backup-restore.yml', RUNS)), [])

    def test_the_github_record_does_not_extend_past_its_last_green_run(self):
        entries = DR.drill_entries('C17', 'backup-restore.yml', RUNS)  # latest green 2026-11-14 -> due 11-21
        self.assertEqual(r3(without_hand_records(), date(2026, 11, 21), entries), [])
        self.assertTrue(r3(without_hand_records(), date(2026, 11, 22), entries))

    def test_only_red_runs_leave_the_drill_overdue(self):
        reds = [r for r in RUNS if r['conclusion'] != 'success']
        # 11-03: two days after the red run of 11-01 -- counted, it would clear the drill
        self.assertTrue(r3(without_hand_records(), date(2026, 11, 3), DR.drill_entries('C17', 'backup-restore.yml', reds)))


class TheTool(unittest.TestCase):
    def run_tool(self, opener, token='t'):
        import os
        out = Path(tempfile.mkdtemp()) / 'runs.json'
        old = os.environ.get('GH_TOKEN')
        os.environ['GH_TOKEN'] = token
        try:
            rc = DR.main([str(ROOT / 'CONTROLS.json'), '--repo', 'Shayfly/desktop-tutorial', '--out', str(out)], urlopen=opener)
        finally:
            if old is None:
                os.environ.pop('GH_TOKEN', None)
            else:
                os.environ['GH_TOKEN'] = old
        return rc, out

    def test_it_writes_the_entries_and_asks_for_main_only(self):
        asked = []

        def opener(req, timeout):
            asked.append(req.full_url)
            return Answer(json.dumps({'workflow_runs': RUNS}).encode())
        rc, out = self.run_tool(opener)
        self.assertEqual(rc, 0)
        self.assertIn('backup-restore.yml/runs?branch=main', asked[0])
        entries = json.loads(out.read_text())
        self.assertEqual(max(e['date'] for e in entries), '2026-11-14')
        self.assertTrue(all(e['source'] == 'github' for e in entries))

    def test_github_unreadable_is_exit_2_and_no_file(self):
        def opener(req, timeout):
            raise OSError('HTTP 503')
        rc, out = self.run_tool(opener)
        self.assertEqual(rc, 2)
        self.assertFalse(out.exists())

    def test_no_token_is_exit_2(self):
        rc, out = self.run_tool(lambda *a, **k: None, token='')
        self.assertEqual(rc, 2)
        self.assertFalse(out.exists())

    def test_the_lint_refuses_an_unreadable_drill_runs_file(self):
        p = subprocess.run([sys.executable, str(ROOT / 'tools' / 'registry_lint.py'), str(ROOT / 'CONTROLS.json'),
                            '--today', '2026-11-15', '--drill-runs', '/nonexistent/runs.json'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn('cannot read the drill runs from GitHub', p.stdout)


def RL_control(reg, cid):
    return next(c for c in reg['controls'] if c['id'] == cid)


if __name__ == '__main__':
    unittest.main()
