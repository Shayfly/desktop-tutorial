"""C10 (CEO 2026-10-27): no successful agent-loop run in the last 45 minutes fails the run."""
import datetime
import importlib.util
import pathlib
import unittest

_P = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'check_agent_loop_stall.py'
_spec = importlib.util.spec_from_file_location('check_agent_loop_stall', _P)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)
NOW = datetime.datetime(2026, 10, 27, 18, 0, tzinfo=datetime.timezone.utc)
WF = pathlib.Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'agent-loop.yml'


class StallGate(unittest.TestCase):
    def test_recent_success_passes(self):
        self.assertTrue(gate.verdict('2026-10-27T17:46:00Z', NOW)[0])

    def test_exactly_45_minutes_passes(self):
        self.assertTrue(gate.verdict('2026-10-27T17:15:00Z', NOW)[0])

    def test_older_than_45_minutes_fails(self):
        ok, why = gate.verdict('2026-10-27T17:14:59Z', NOW)
        self.assertFalse(ok)
        self.assertIn('minutes ago', why)

    def test_the_observed_five_hour_gap_fails(self):            # 10:36 -> 16:01 on 2026-10-27
        self.assertFalse(gate.verdict('2026-10-27T10:36:46Z', datetime.datetime(2026, 10, 27, 16, 1, tzinfo=datetime.timezone.utc))[0])

    def test_no_success_on_record_fails(self):
        for missing in (None, '', 'null'):
            self.assertFalse(gate.verdict(missing, NOW)[0])

    def test_unreadable_timestamp_fails(self):
        self.assertFalse(gate.verdict('yesterday', NOW)[0])

    def test_exit_codes(self):
        self.assertEqual(gate.main(['x', datetime.datetime.now(datetime.timezone.utc).isoformat()]), 0)
        self.assertEqual(gate.main(['x', '']), 1)

    def test_the_workflow_fails_the_run_through_the_gate_after_the_work(self):
        text = WF.read_text(encoding='utf-8')
        self.assertIn('python scripts/check_agent_loop_stall.py', text)
        self.assertNotIn('::warning title=agent-loop STALLED', text)    # a warning is silent green
        self.assertLess(text.index('sweep clean ready'), text.index('stall gate'))   # the work still runs first
        self.assertIn('if: always()', text[text.index('stall gate') - 200:text.index('stall gate') + 200])


if __name__ == '__main__':
    unittest.main()
