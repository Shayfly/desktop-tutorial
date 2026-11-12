"""2026-10-30: pollBuild re-armed setTimeout without clearTimeout, so a second call (a new build, a project switch,
a cancel) stacked a second poll loop. Executes the real pollBuild from app.js under node with fake timers."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js pollBuild()')
class OnePollLoop(unittest.TestCase):
    def pending_after(self, calls):
        src = APP_JS.read_text(encoding='utf-8')
        fn = re.search(r'^async function pollBuild\(\) \{.*?^\}', src, re.S | re.M).group(0)
        harness = f"""
let next = 1; const pending = new Map();
const setTimeout = (f, ms) => {{ const id = next++; pending.set(id, f); return id; }};
const clearTimeout = id => {{ pending.delete(id); }};
const S = {{ build: {{ id: 'b1' }}, timers: {{}} }};
const pid = () => 'p'; const isTerminal = s => false; const $ = () => ({{}}); const explain = e => '';
async function api() {{ return {{ status: 'running' }}; }}
async function pollEvents() {{}} async function loadTasks() {{}}
const renderTrack = () => {{}}, renderEvidence = () => {{}}, renderTasks = () => {{}}, renderChat = () => {{}};
{fn}
(async () => {{
  await Promise.all(Array.from({{ length: {calls} }}, () => pollBuild()));   // overlapping calls
  await pollBuild();                                                          // one more, sequentially
  process.stdout.write(JSON.stringify(pending.size));
}})();
"""
        out = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_repeated_and_overlapping_calls_leave_exactly_one_timer(self):
        for calls in (1, 2, 5):
            with self.subTest(calls=calls):
                self.assertEqual(self.pending_after(calls), 1)


if __name__ == '__main__':
    unittest.main()
