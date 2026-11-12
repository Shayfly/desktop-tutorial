"""2026-10-30: the evidence panel printed raw gate keys (verification, quality, security, rights). They are labels
now, in Hebrew and English like every other one; an unknown key keeps its name. Executes the real gateLabel from
app.js under node with the real T table."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js gateLabel()')
class TheGateLabels(unittest.TestCase):
    def labels(self, lang, keys):
        src = APP_JS.read_text(encoding='utf-8')
        table = src[src.index('const T ='):src.index('const S =')]
        fn = re.search(r'^function gateLabel\(k\) \{.*?\}$', src, re.M).group(0)
        harness = (f"{table}\nconst S = {{ lang: {json.dumps(lang)} }};\nfunction t(k) {{ return T[S.lang][k]; }}\n{fn}\n"
                   f"process.stdout.write(JSON.stringify({json.dumps(keys)}.map(gateLabel)));")
        out = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_four_gates_are_translated(self):
        keys = ['verification', 'quality', 'security', 'rights']
        self.assertEqual(self.labels('he', keys), ['אימות', 'איכות', 'אבטחה', 'זכויות'])
        self.assertEqual(self.labels('en', keys), ['Verification', 'Quality', 'Security', 'Rights'])

    def test_an_unknown_gate_keeps_its_name(self):
        self.assertEqual(self.labels('he', ['new_gate']), ['new_gate'])

    def test_the_panel_uses_the_label(self):
        self.assertIn('${gateLabel(k)}: ${gateMark(v)}', APP_JS.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
