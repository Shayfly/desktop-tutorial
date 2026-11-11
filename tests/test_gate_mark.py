"""2026-10-30: the evidence panel showed a check mark for a gate whose value was missing, null or had no verdict
(`v && v.passed === false ? '✗' : '✓'`). A check mark now means an explicit pass only. Executes the real gateMark
from omni_prod/assets/app.js under node."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js gateMark()')
class TheGateMark(unittest.TestCase):
    def marks(self, values):
        src = APP_JS.read_text(encoding='utf-8')
        m = re.search(r'^function gateMark\(v\) \{.*?^\}', src, re.S | re.M)
        self.assertIsNotNone(m, 'gateMark not found in app.js')
        harness = f"{m.group(0)}\nprocess.stdout.write(JSON.stringify({json.dumps(values)}.map(gateMark)));"
        out = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_missing_null_or_verdictless_values_never_get_a_check_mark(self):
        for v in (None, {}, {'passed': None}, {'passed': 'yes'}, {'score': 90}, {'status': 'CLEAR'}):
            with self.subTest(v=v):
                self.assertEqual(self.marks([v]), ['—'])

    def test_an_explicit_pass_is_a_check_and_an_explicit_fail_a_cross(self):
        self.assertEqual(self.marks([{'passed': True}, {'passed': False}]), ['✓', '✗'])

    def test_the_rights_gate_uses_publish_allowed(self):
        self.assertEqual(self.marks([{'status': 'CLEAR', 'publish_allowed': True},
                                     {'status': 'BLOCKED', 'publish_allowed': False}]), ['✓', '✗'])

    def test_the_evidence_panel_uses_gate_mark(self):
        src = APP_JS.read_text(encoding='utf-8')
        self.assertIn('${gateLabel(k)}: ${gateMark(v)}', src)
        self.assertNotIn("v.passed === false ? '✗' : '✓'", src)


if __name__ == '__main__':
    unittest.main()
